from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

try:
    from server.utils.metadata_handler import metadata_handler
    from server.utils.kb_transactions import TransactionalKBOperations
except ImportError:
    try:
        from utils.metadata_handler import metadata_handler
        from utils.kb_transactions import TransactionalKBOperations
    except ImportError:
        # 如果还是找不到，创建一个简单的备用实现
        class MetadataHandler:
            @staticmethod
            def clean_metadata(metadata):
                return metadata
            @staticmethod
            def restore_metadata(metadata):
                return metadata
        metadata_handler = MetadataHandler()
        
        class TransactionalKBOperations:
            def __init__(self, vector_db_service):
                self.vector_db = vector_db_service
            def execute_with_rollback(self, kb_id, operation_func):
                return operation_func()

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 数据模型 ==========

class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    document_count: int = 0
    device_id: Optional[str] = None  # 来源设备ID
    device_name: Optional[str] = None  # 来源设备名称
    is_synced: bool = False  # 是否是同步的知识库

class CreateKnowledgeBaseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    device_id: str = Field(..., description="创建设备ID，必需")
    device_name: str = Field(..., description="创建设备名称，必需")
    is_draft: bool = Field(default=True, description="是否为草稿状态")

class Document(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]

class AddDocumentRequest(BaseModel):
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    filter: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float

class DeleteDocumentsRequest(BaseModel):
    document_ids: Optional[List[str]] = Field(None, description="Specific document IDs to delete")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="Filter conditions for deletion")
    older_than_days: Optional[int] = Field(None, description="Delete documents older than N days")
    source_pattern: Optional[str] = Field(None, description="Delete documents matching source pattern")
    
class CleanupRequest(BaseModel):
    delete_all: bool = Field(False, description="Delete all documents in the knowledge base")
    confirm: str = Field(..., description="Type 'CONFIRM' to proceed with deletion")

# ========== 依赖注入 ==========

def get_services(request: Request):
    """获取所需的服务"""
    services = request.app.state.services
    
    logger.info(f"Vector DB Service: {services.vector_db_service is not None}")
    logger.info(f"Embedding Manager: {services.embedding_manager is not None}")
    
    if not services.vector_db_service:
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Vector database service not available",
                "message": "The vector database service is not initialized. Please check server logs.",
                "suggestion": "Ensure ChromaDB is properly installed and the data directory is accessible."
            }
        )
    
    if not services.embedding_manager:
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Embedding service not available",
                "message": "No embedding service is available for text processing.",
                "suggestion": "Check if sentence-transformers or Ollama embedding service is properly configured."
            }
        )
    
    # 检查嵌入服务健康状态
    health_status = services.embedding_manager.get_health_status()
    if not health_status["has_healthy_service"]:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "All embedding services are unhealthy",
                "health_status": health_status,
                "suggestion": "Please check the embedding service configuration and ensure at least one service is working."
            }
        )
    
    return services

def get_kb_operations(request: Request) -> TransactionalKBOperations:
    """获取知识库事务操作管理器"""
    services = get_services(request)
    
    # 创建或获取事务管理器
    if not hasattr(request.app.state, 'kb_operations'):
        request.app.state.kb_operations = TransactionalKBOperations(services.vector_db_service)
    
    return request.app.state.kb_operations
# ========== API 端点 ==========

@router.get("/")  # 移除 response_model 以返回完整数据
async def list_knowledge_bases(
    request: Request,
    services = Depends(get_services),
    device_id: Optional[str] = None,  # 设备ID过滤
    show_mode: str = "all"  # "all", "drafts", "published"
):
    """
    列出知识库
    - 如果提供device_id：显示该设备的所有草稿 + 所有公开的知识库
    - 如果不提供device_id：只显示公开的知识库
    """
    try:
        collections = services.vector_db_service.list_collections()
        
        knowledge_bases = []
        for collection in collections:
            # 获取集合的元数据
            collection_obj = services.vector_db_service.client.get_collection(name=collection["id"])
            raw_metadata = collection_obj.metadata or {}
            
            # 使用统一的元数据处理器
            metadata = metadata_handler.restore_metadata(raw_metadata)
            
            is_draft = metadata.get("is_draft", False)
            kb_device_id = metadata.get("device_id")
            
            # 根据规则过滤
            if device_id:
                # 有设备ID：显示该设备的草稿 + 所有公开的
                if is_draft and kb_device_id != device_id:
                    continue  # 草稿只能看到自己的
            else:
                # 没有设备ID：只显示公开的
                if is_draft:
                    continue
            
            # 根据show_mode过滤
            if show_mode == "drafts" and not is_draft:
                continue
            elif show_mode == "published" and is_draft:
                continue
            
            # 使用元数据中的display_name，如果没有则使用collection的name
            display_name = metadata.get("display_name", collection.get("name", collection["id"]))
            
            kb = KnowledgeBase(
                id=collection["id"],
                name=display_name,  # 使用显示名称而不是ID
                description=collection.get("description", ""),
                created_at=collection.get("created_at", ""),
                document_count=collection.get("document_count", 0),
                device_id=kb_device_id,
                device_name=metadata.get("device_name"),
                is_synced=metadata.get("is_synced", False)
            )
            # 添加元数据信息以便客户端使用
            kb_dict = kb.dict()
            kb_dict["metadata"] = metadata
            kb_dict["is_draft"] = is_draft
            
            # 确保 is_draft 始终存在且正确
            if "is_draft" not in kb_dict:
                kb_dict["is_draft"] = is_draft
                
            # 调试输出
            logger.info(f"KB: {kb_dict['name']}, is_draft: {kb_dict.get('is_draft')}, metadata: {kb_dict.get('metadata')}")
            knowledge_bases.append(kb_dict)
        
        logger.info(f"Listed {len(knowledge_bases)} knowledge bases for device: {device_id}")
        return knowledge_bases
        
    except Exception as e:
        logger.error(f"Failed to list knowledge bases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=KnowledgeBase)
async def create_knowledge_base(
    request: Request,
    kb_request: CreateKnowledgeBaseRequest,
    services = Depends(get_services)
):
    """创建新的知识库"""
    try:
        logger.info(f"Creating knowledge base with request: {kb_request.dict()}")
        
        # 验证必需的服务
        if not services.vector_db_service:
            logger.error("Vector DB service is not available")
            raise HTTPException(status_code=503, detail="Vector database service not available")
            
        if not services.embedding_manager:
            logger.warning("Embedding service is not available, but continuing...")
        # 构建完整的知识库名称（添加设备名后缀）
        full_name = f"{kb_request.name} ({kb_request.device_name})"
        
        # 检查是否已存在同名知识库（只检查公开的）
        if not kb_request.is_draft:
            existing_collections = services.vector_db_service.list_collections()
            for collection in existing_collections:
                collection_obj = services.vector_db_service.client.get_collection(name=collection["id"])
                metadata = collection_obj.metadata or {}
                if collection["name"] == full_name and not metadata.get("is_draft", False):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"A published knowledge base with name '{full_name}' already exists"
                    )
        
        # 创建元数据
        raw_metadata = {
            "device_id": kb_request.device_id,
            "device_name": kb_request.device_name,
            "is_synced": False,
            "is_draft": kb_request.is_draft,
            "creator_device_id": kb_request.device_id,  # 记录创建者
            "original_name": kb_request.name,  # 保存原始名称（不带设备名）
            "created_at": datetime.now().isoformat(),
            "display_name": full_name  # 保存显示名称
        }
        
        # 使用元数据处理器清理
        metadata = metadata_handler.clean_metadata(raw_metadata)
        
        # 生成简短的集合ID，确保唯一性
        import uuid
        import time
        # 使用UUID前8位 + 毫秒时间戳后6位，避免重复
        timestamp = str(int(time.time() * 1000))[-8:]  # 使用毫秒时间戳的后8位
        uuid_part = str(uuid.uuid4())[:8]
        collection_id = f"{uuid_part}_{timestamp}"
        
        logger.info(f"Creating collection with metadata: {metadata}")
        logger.info(f"Collection ID: {collection_id}")
        
        try:
            collection_data = services.vector_db_service.create_collection(
                name=full_name,
                description=kb_request.description or "",
                metadata=metadata,
                collection_id=collection_id  # 使用简短ID
            )
        except Exception as e:
            logger.error(f"Failed to create collection in vector DB: {e}")
            logger.error(f"Collection data: name={full_name}, id={collection_id}")
            raise
        
        kb = KnowledgeBase(
            id=collection_data["id"],
            name=collection_data["name"],
            description=collection_data.get("description", ""),
            created_at=collection_data["created_at"],
            document_count=0,
            device_id=kb_request.device_id,
            device_name=kb_request.device_name
        )
        
        logger.info(f"Created {'draft' if kb_request.is_draft else 'public'} knowledge base: {kb.name}")
        return kb
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"ValueError in create_knowledge_base: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create knowledge base: {e}")
        logger.error(f"Request data: name={kb_request.name}, device_id={kb_request.device_id}, is_draft={kb_request.is_draft}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    request: Request,
    services = Depends(get_services)
):
    """获取特定知识库的信息"""
    try:
        collections = services.vector_db_service.list_collections()
        
        for collection in collections:
            if collection["id"] == kb_id:
                # 获取集合的元数据
                collection_obj = services.vector_db_service.client.get_collection(name=collection["id"])
                raw_metadata = collection_obj.metadata or {}
                
                # 使用元数据处理器恢复数据
                restored_metadata = metadata_handler.restore_metadata(raw_metadata)
                is_draft = restored_metadata.get("is_draft", False)
                
                kb = KnowledgeBase(
                    id=collection["id"],
                    name=collection["name"],
                    description=collection.get("description", ""),
                    created_at=collection.get("created_at", ""),
                    document_count=collection.get("document_count", 0),
                    device_id=restored_metadata.get("device_id"),
                    device_name=restored_metadata.get("device_name"),
                    is_synced=restored_metadata.get("is_synced", False)
                )
                
                # 返回完整数据
                kb_dict = kb.dict()
                kb_dict["is_draft"] = is_draft
                kb_dict["metadata"] = restored_metadata
                
                return kb_dict
        
        raise HTTPException(status_code=404, detail="Knowledge base not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    request: Request,
    services = Depends(get_services),
    is_admin: bool = False  # 可以通过header或其他方式传递管理员标识
):
    """删除知识库"""
    try:
        # 获取知识库元数据以检查状态
        try:
            collection = services.vector_db_service.client.get_collection(name=kb_id)
            metadata = collection.metadata or {}
        except Exception:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # 检查是否是草稿
        is_draft_value = metadata.get("is_draft", False)
        is_draft = bool(is_draft_value) if isinstance(is_draft_value, int) else is_draft_value
        
        # 检查是否从管理界面发起的请求
        referer = request.headers.get("referer", "")
        is_from_admin = "/admin/" in referer or is_admin
        
        # 检查特定的管理员header
        admin_key = request.headers.get("x-admin-key", "")
        is_admin_request = admin_key == "mas-server-admin" or is_from_admin
        
        # 如果不是草稿且不是管理员请求
        if not is_draft and not is_admin_request:
            logger.warning(f"Attempt to delete published KB {kb_id} without admin privileges")
            raise HTTPException(
                status_code=403, 
                detail="Published knowledge bases can only be deleted through the server admin interface."
            )
        
        services.vector_db_service.delete_collection(kb_id)
        logger.info(f"Deleted knowledge base: {kb_id}")
        return {"message": f"Knowledge base {kb_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{kb_id}/documents")
async def add_document(
    kb_id: str,
    request: Request,
    doc_request: AddDocumentRequest,
    services = Depends(get_services)
):
    """向知识库添加文档（文本）"""
    try:
        # 处理文档
        chunks = services.document_processor.split_text(
            doc_request.content,
            doc_request.metadata
        )
        
        if not chunks:
            raise ValueError("No content to add")
        
        # 生成嵌入
        texts = [chunk["text"] for chunk in chunks]
        embeddings = services.embedding_manager.embed_texts(texts)
        
        # 准备元数据
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = chunk["metadata"].copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            # 使用元数据处理器清理元数据
            clean_metadata = metadata_handler.clean_metadata(chunk_metadata)
            metadatas.append(clean_metadata)
        
        # 添加到向量数据库
        doc_ids = services.vector_db_service.add_documents(
            collection_name=kb_id,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Added document with {len(chunks)} chunks to {kb_id}")
        return {
            "message": "Document added successfully",
            "document_ids": doc_ids,
            "chunk_count": len(chunks)
        }
        
    except Exception as e:
        logger.error(f"Failed to add document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{kb_id}/documents/upload")
async def upload_document(
    kb_id: str,
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    services = Depends(get_services)
):
    """上传文件到知识库"""
    temp_file_path = None
    
    try:
        # 验证文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in services.document_processor.supported_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Supported types: {', '.join(services.document_processor.supported_extensions)}"
            )
        
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            temp_file_path = tmp_file.name
            shutil.copyfileobj(file.file, tmp_file)
        
        # 处理文件
        text_content, file_metadata = services.document_processor.process_file(temp_file_path)
        
        # 合并元数据
        if metadata:
            import json
            try:
                custom_metadata = json.loads(metadata)
                file_metadata.update(custom_metadata)
            except json.JSONDecodeError:
                logger.warning("Invalid metadata JSON, ignoring")
        
        file_metadata["original_filename"] = file.filename
        file_metadata["file_size"] = os.path.getsize(temp_file_path)
        file_metadata["extension"] = file_extension[1:] if file_extension else "unknown"
        
        # 分割文本
        chunks = services.document_processor.split_text(text_content, file_metadata)
        
        if not chunks:
            raise ValueError("No content extracted from file")
        
        # 生成嵌入
        texts = [chunk["text"] for chunk in chunks]
        embeddings = services.embedding_manager.embed_texts(texts)
        
        # 准备元数据
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = chunk["metadata"].copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            # 使用元数据处理器清理元数据
            clean_metadata = metadata_handler.clean_metadata(chunk_metadata)
            metadatas.append(clean_metadata)
        
        # 添加到向量数据库
        doc_ids = services.vector_db_service.add_documents(
            collection_name=kb_id,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Uploaded file {file.filename} with {len(chunks)} chunks to {kb_id}")
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "document_ids": doc_ids,
            "chunk_count": len(chunks),
            "total_characters": len(text_content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.post("/{kb_id}/search", response_model=List[SearchResult])
async def search_knowledge_base(
    kb_id: str,
    request: Request,
    search_request: SearchRequest,
    services = Depends(get_services)
):
    """在知识库中搜索"""
    try:
        # 生成查询向量
        query_embedding = services.embedding_manager.embed_text(search_request.query)
        
        # 执行搜索
        results = services.vector_db_service.search(
            collection_name=kb_id,
            query_embedding=query_embedding,
            n_results=search_request.limit,
            filter=search_request.filter
        )
        
        # 格式化结果
        search_results = []
        for result in results["results"]:
            # 计算相似度分数（距离越小，相似度越高）
            similarity_score = 1.0 / (1.0 + result["distance"])
            
            search_results.append(SearchResult(
                id=result["id"],
                content=result["document"],
                metadata=result["metadata"],
                score=similarity_score
            ))
        
        logger.info(f"Search in {kb_id} returned {len(search_results)} results")
        return search_results
        
    except Exception as e:
        logger.error(f"Failed to search knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}/documents/{doc_id}")
async def get_document(
    kb_id: str,
    doc_id: str,
    request: Request,
    services = Depends(get_services)
):
    """获取特定文档"""
    try:
        document = services.vector_db_service.get_document(kb_id, doc_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(
    kb_id: str,
    doc_id: str,
    request: Request,
    services = Depends(get_services)
):
    """删除文档"""
    try:
        services.vector_db_service.delete_documents(kb_id, [doc_id])
        logger.info(f"Deleted document {doc_id} from {kb_id}")
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}/stats")
async def get_knowledge_base_stats(
    kb_id: str,
    request: Request,
    services = Depends(get_services)
):
    """获取知识库统计信息"""
    try:
        collections = services.vector_db_service.list_collections()
        
        for collection in collections:
            if collection["id"] == kb_id:
                # 获取更详细的统计信息
                stats = {
                    "id": kb_id,
                    "name": collection["name"],
                    "document_count": collection["document_count"],
                    "created_at": collection.get("created_at", ""),
                    "embedding_service": services.embedding_manager.default_service,
                    "embedding_dimension": len(services.embedding_manager.embed_text("test"))
                }
                return stats
        
        raise HTTPException(status_code=404, detail="Knowledge base not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    request: Request,
    limit: int = 100,
    offset: int = 0,
    services = Depends(get_services)
):
    """列出知识库中的文档"""
    try:
        # 直接使用ChromaDB的get方法获取所有文档
        collection = services.vector_db_service.client.get_collection(name=kb_id)
        
        # 获取所有文档（ChromaDB支持不指定IDs获取所有）
        results = collection.get(
            include=["documents", "metadatas"],
            limit=limit,
            offset=offset
        )
        
        documents = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                doc_info = {
                    "id": doc_id,
                    "content_preview": results["documents"][i][:200] + "..." if len(results["documents"][i]) > 200 else results["documents"][i],
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    "created_at": results["metadatas"][i].get("added_at", "") if results["metadatas"] else ""
                }
                documents.append(doc_info)
        
        # 获取总数
        total_count = collection.count()
        
        return {
            "documents": documents,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{kb_id}/documents/delete")
async def delete_documents_batch(
    kb_id: str,
    request: Request,
    delete_request: DeleteDocumentsRequest,
    services = Depends(get_services)
):
    """批量删除文档"""
    try:
        documents_to_delete = []
        
        # 1. 如果指定了具体的文档ID
        if delete_request.document_ids:
            documents_to_delete.extend(delete_request.document_ids)
            logger.info(f"Deleting specific documents: {len(delete_request.document_ids)}")
        
        # 2. 如果指定了时间条件
        if delete_request.older_than_days is not None:
            cutoff_date = datetime.now() - timedelta(days=delete_request.older_than_days)
            cutoff_date_str = cutoff_date.isoformat()
            
            # 获取所有文档并筛选
            collection = services.vector_db_service.client.get_collection(name=kb_id)
            results = collection.get(include=["metadatas"])
            
            all_docs = {
                "documents": []
            }
            
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    all_docs["documents"].append({
                        "id": doc_id,
                        "metadata": metadata,
                        "created_at": metadata.get("added_at", "")
                    })
            
            for doc in all_docs["documents"]:
                if doc["created_at"] < cutoff_date_str:
                    documents_to_delete.append(doc["id"])
            
            logger.info(f"Found {len(documents_to_delete)} documents older than {delete_request.older_than_days} days")
        
        # 3. 如果指定了源匹配模式
        if delete_request.source_pattern:
            # 重新获取所有文档（如果之前没有获取过）
            if 'collection' not in locals():
                collection = services.vector_db_service.client.get_collection(name=kb_id)
                results = collection.get(include=["metadatas"])
                
                all_docs = {
                    "documents": []
                }
                
                if results["ids"]:
                    for i, doc_id in enumerate(results["ids"]):
                        metadata = results["metadatas"][i] if results["metadatas"] else {}
                        all_docs["documents"].append({
                            "id": doc_id,
                            "metadata": metadata
                        })
            
            for doc in all_docs["documents"]:
                source = doc["metadata"].get("source", "")
                filename = doc["metadata"].get("filename", "")
                
                if delete_request.source_pattern in source or delete_request.source_pattern in filename:
                    if doc["id"] not in documents_to_delete:
                        documents_to_delete.append(doc["id"])
            
            logger.info(f"Found documents matching pattern '{delete_request.source_pattern}'")
        
        # 4. 如果指定了过滤条件
        if delete_request.filter_conditions:
            # 这需要更复杂的实现，暂时简化处理
            logger.warning("Filter conditions not fully implemented yet")
        
        # 去重
        documents_to_delete = list(set(documents_to_delete))
        
        if not documents_to_delete:
            return {
                "message": "No documents found matching the criteria",
                "deleted_count": 0
            }
        
        # 执行删除
        services.vector_db_service.delete_documents(kb_id, documents_to_delete)
        
        logger.info(f"Deleted {len(documents_to_delete)} documents from {kb_id}")
        return {
            "message": f"Successfully deleted {len(documents_to_delete)} documents",
            "deleted_count": len(documents_to_delete),
            "deleted_ids": documents_to_delete
        }
        
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{kb_id}/cleanup")
async def cleanup_knowledge_base(
    kb_id: str,
    request: Request,
    cleanup_request: CleanupRequest,
    services = Depends(get_services)
):
    """清理知识库（删除所有文档但保留知识库）"""
    try:
        if cleanup_request.confirm != "CONFIRM":
            raise HTTPException(
                status_code=400,
                detail="Please type 'CONFIRM' in the confirm field to proceed"
            )
        
        if not cleanup_request.delete_all:
            raise HTTPException(
                status_code=400,
                detail="Please set delete_all to true to proceed"
            )
        
        # 获取所有文档
        collection = services.vector_db_service.client.get_collection(name=kb_id)
        results = collection.get(include=["metadatas"])  # 只需要IDs
        
        all_docs = {
            "documents": []
        }
        
        if results["ids"]:
            for doc_id in results["ids"]:
                all_docs["documents"].append({"id": doc_id})
        
        if not all_docs["documents"]:
            return {
                "message": "Knowledge base is already empty",
                "deleted_count": 0
            }
        
        # 提取所有文档ID
        all_doc_ids = [doc["id"] for doc in all_docs["documents"]]
        
        # 批量删除
        batch_size = 100
        total_deleted = 0
        
        for i in range(0, len(all_doc_ids), batch_size):
            batch = all_doc_ids[i:i + batch_size]
            services.vector_db_service.delete_documents(kb_id, batch)
            total_deleted += len(batch)
            logger.info(f"Deleted batch {i//batch_size + 1}: {len(batch)} documents")
        
        logger.info(f"Cleaned up knowledge base {kb_id}: deleted {total_deleted} documents")
        return {
            "message": f"Successfully cleaned up knowledge base",
            "deleted_count": total_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}/documents/stats")
async def get_documents_stats(
    kb_id: str,
    request: Request,
    services = Depends(get_services)
):
    """获取文档统计信息"""
    try:
        # 获取所有文档信息
        # 直接使用ChromaDB获取所有文档
        collection = services.vector_db_service.client.get_collection(name=kb_id)
        results = collection.get(include=["metadatas"])
        
        all_docs = {
            "documents": [],
            "total": 0
        }
        
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                all_docs["documents"].append({
                    "id": doc_id,
                    "metadata": metadata
                })
            all_docs["total"] = len(results["ids"])
        
        # 统计信息
        stats = {
            "total_documents": all_docs["total"],
            "total_files": 0,  # 兼容旧版本
            "total_size": 0,
            "by_source": {},
            "by_date": {},
            "by_topic": {},
            "file_types": {},
            "file_types_count": 0  # 兼容旧版本
        }
        
        # 如果没有文档，返回空统计
        if not all_docs["documents"]:
            return stats
        
        # 分析每个文档
        unique_files = set()  # 用于去重计算实际文件数
        
        for doc in all_docs["documents"]:
            metadata = doc["metadata"]
            
            # 统计唯一文件
            filename = metadata.get("filename") or metadata.get("original_filename")
            if filename:
                unique_files.add(filename)
            
            # 按来源统计
            source = metadata.get("source", "unknown")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
            
            # 按日期统计（按天）
            added_at = metadata.get("added_at", "")
            if added_at:
                date_only = added_at.split("T")[0]
                stats["by_date"][date_only] = stats["by_date"].get(date_only, 0) + 1
            
            # 按主题统计
            topic = metadata.get("topic", "uncategorized")
            stats["by_topic"][topic] = stats["by_topic"].get(topic, 0) + 1
            
            # 按文件类型统计
            extension = metadata.get("extension", "text")
            if not extension and filename:
                # 尝试从文件名获取扩展名
                extension = filename.split('.')[-1].lower() if '.' in filename else 'text'
            stats["file_types"][extension] = stats["file_types"].get(extension, 0) + 1
            
            # 统计文件大小
            file_size = metadata.get("file_size", 0)
            if file_size:
                stats["total_size"] += file_size
        
        # 更新统计
        stats["total_files"] = len(unique_files)
        stats["file_types_count"] = len(stats["file_types"])
        
        # 添加时间范围
        if all_docs["documents"]:
            dates = [doc["metadata"].get("added_at", "") for doc in all_docs["documents"] if doc["metadata"].get("added_at")]
            if dates:
                stats["oldest_document"] = min(dates)
                stats["newest_document"] = max(dates)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get document stats: {e}")
        # 返回空统计而不是错误，避免客户端处理错误
        return {
            "total_documents": 0,
            "total_files": 0,
            "total_size": 0,
            "file_types": {},
            "file_types_count": 0
        }

@router.post("/{kb_id}/documents/search-delete")
async def search_and_delete(
    kb_id: str,
    request: Request,
    query: str,
    confirm: bool = False,
    services = Depends(get_services)
):
    """搜索并删除匹配的文档"""
    try:
        # 先搜索
        query_embedding = services.embedding_manager.embed_text(query)
        
        results = services.vector_db_service.search(
            collection_name=kb_id,
            query_embedding=query_embedding,
            n_results=50  # 搜索更多结果
        )
        
        if not results["results"]:
            return {
                "message": "No documents found matching the query",
                "found_count": 0
            }
        
        # 如果只是预览
        if not confirm:
            return {
                "message": "Preview mode - no documents deleted",
                "found_count": len(results["results"]),
                "documents": [
                    {
                        "id": r["id"],
                        "content_preview": r["document"][:200] + "...",
                        "score": 1.0 / (1.0 + r["distance"])
                    }
                    for r in results["results"]
                ],
                "note": "Set confirm=true to delete these documents"
            }
        
        # 执行删除
        doc_ids = [r["id"] for r in results["results"]]
        services.vector_db_service.delete_documents(kb_id, doc_ids)
        
        return {
            "message": f"Deleted {len(doc_ids)} documents matching the query",
            "deleted_count": len(doc_ids),
            "deleted_ids": doc_ids
        }
        
    except Exception as e:
        logger.error(f"Failed to search and delete: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{kb_id}/publish")
async def publish_knowledge_base(
    kb_id: str,
    request: Request,
    device_id: str,  # 必须提供设备ID以验证权限
    services = Depends(get_services),
    kb_ops = Depends(get_kb_operations)
):
    """发布草稿知识库为公开状态"""
    try:
        # 获取知识库元数据
        try:
            collection = services.vector_db_service.client.get_collection(name=kb_id)
            raw_metadata = collection.metadata or {}
            metadata = metadata_handler.restore_metadata(raw_metadata)
        except Exception:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # 验证权限：只有创建者可以发布
        if metadata.get("creator_device_id") != device_id:
            raise HTTPException(status_code=403, detail="Only the creator can publish this knowledge base")
        
        # 检查是否已经是公开状态
        if not metadata.get("is_draft", True):
            raise HTTPException(status_code=400, detail="Knowledge base is already published")
        
        # 获取原始的显示名称
        kb_display_name = metadata.get("display_name", collection.name)
        
        # 检查是否存在同名的公开知识库
        existing_collections = services.vector_db_service.list_collections()
        for existing in existing_collections:
            if existing["id"] == kb_id:
                continue  # 跳过自己
            
            existing_collection = services.vector_db_service.client.get_collection(name=existing["id"])
            existing_raw_metadata = existing_collection.metadata or {}
            existing_metadata = metadata_handler.restore_metadata(existing_raw_metadata)
            
            # 检查名称冲突（只检查公开的）
            existing_display_name = existing_metadata.get("display_name", existing_collection.name)
            if (existing_display_name == kb_display_name and 
                not existing_metadata.get("is_draft", False)):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot publish: A public knowledge base with name '{kb_display_name}' already exists. Please rename before publishing."
                )
        
        # 定义发布操作
        def publish_operation():
            # 更新元数据为公开状态
            new_metadata = metadata.copy()
            new_metadata["is_draft"] = False
            new_metadata["published_at"] = datetime.now().isoformat()
            new_metadata["published_by_device"] = device_id
            
            # 使用元数据处理器清理
            clean_metadata = metadata_handler.clean_metadata(new_metadata)
            
            # 由于ChromaDB不支持直接更新元数据，需要重新创建
            # 获取所有文档
            results = collection.get(include=["embeddings", "documents", "metadatas"])
            
            # 删除旧集合
            services.vector_db_service.delete_collection(kb_id)
            
            # 创建新集合（公开状态），使用原始的显示名称
            services.vector_db_service.create_collection(
                name=kb_display_name,  # 使用显示名称而不是collection.name
                description=metadata.get("description", ""),
                metadata=clean_metadata,
                collection_id=kb_id  # 保持相同ID
            )
            
            # 恢复文档
            if results['ids']:
                services.vector_db_service.add_documents(
                    collection_name=kb_id,
                    documents=results['documents'],
                    embeddings=results['embeddings'],
                    metadatas=results['metadatas'],
                    ids=results['ids']
                )
            
            return {
                "kb_id": kb_id,
                "name": kb_display_name,
                "published_at": new_metadata["published_at"]
            }
        
        # 使用事务性操作执行发布
        result = kb_ops.execute_with_rollback(kb_id, publish_operation)
        
        logger.info(f"Published knowledge base {kb_id} by device {device_id}")
        
        return {
            "message": "Knowledge base published successfully",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{kb_id}/rename")
async def rename_knowledge_base(
    kb_id: str,
    new_name: str,
    device_id: str,
    services = Depends(get_services),
    kb_ops = Depends(get_kb_operations)
):
    """重命名知识库（只能重命名草稿）"""
    try:
        # 获取知识库
        try:
            collection = services.vector_db_service.client.get_collection(name=kb_id)
            raw_metadata = collection.metadata or {}
            metadata = metadata_handler.restore_metadata(raw_metadata)
        except Exception:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # 验证权限
        if metadata.get("creator_device_id") != device_id:
            raise HTTPException(status_code=403, detail="Only the creator can rename this knowledge base")
        
        # 只能重命名草稿
        if not metadata.get("is_draft", True):
            raise HTTPException(status_code=400, detail="Cannot rename published knowledge base")
        
        # 构建新的完整名称
        device_name = metadata.get("device_name", "Unknown")
        full_new_name = f"{new_name} ({device_name})"
        
        # 定义重命名操作
        def rename_operation():
            # 由于ChromaDB不支持重命名，需要重新创建
            # 获取所有数据
            results = collection.get(include=["embeddings", "documents", "metadatas"])
            
            # 更新元数据
            new_metadata = metadata.copy()
            new_metadata["original_name"] = new_name
            new_metadata["display_name"] = full_new_name
            new_metadata["renamed_at"] = datetime.now().isoformat()
            
            # 使用元数据处理器清理
            clean_metadata = metadata_handler.clean_metadata(new_metadata)
            
            # 删除旧集合
            services.vector_db_service.delete_collection(kb_id)
            
            # 创建新集合
            services.vector_db_service.create_collection(
                name=full_new_name,
                description=metadata.get("description", ""),
                metadata=clean_metadata,
                collection_id=kb_id
            )
            
            # 恢复文档
            if results['ids']:
                services.vector_db_service.add_documents(
                    collection_name=kb_id,
                    documents=results['documents'],
                    embeddings=results['embeddings'],
                    metadatas=results['metadatas'],
                    ids=results['ids']
                )
            
            return {
                "kb_id": kb_id,
                "new_name": full_new_name
            }
        
        # 使用事务性操作执行重命名
        result = kb_ops.execute_with_rollback(kb_id, rename_operation)
        
        logger.info(f"Renamed knowledge base {kb_id} to {full_new_name}")
        
        return {
            "message": "Knowledge base renamed successfully",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))