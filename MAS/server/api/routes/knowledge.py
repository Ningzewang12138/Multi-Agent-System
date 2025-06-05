from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 数据模型 ==========

class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    document_count: int = 0

class CreateKnowledgeBaseRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

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
        raise HTTPException(status_code=503, detail="Vector database service not available")
    
    if not services.embedding_manager:
        raise HTTPException(status_code=503, detail="Embedding service not available")
    
    return services
# ========== API 端点 ==========

@router.get("/", response_model=List[KnowledgeBase])
async def list_knowledge_bases(
    request: Request,
    services = Depends(get_services)
):
    """列出所有知识库"""
    try:
        collections = services.vector_db_service.list_collections()
        
        knowledge_bases = []
        for collection in collections:
            kb = KnowledgeBase(
                id=collection["id"],
                name=collection["name"],
                description=collection.get("description", ""),
                created_at=collection.get("created_at", ""),
                document_count=collection.get("document_count", 0)
            )
            knowledge_bases.append(kb)
        
        logger.info(f"Listed {len(knowledge_bases)} knowledge bases")
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
        # 创建知识库集合
        collection_data = services.vector_db_service.create_collection(
            name=kb_request.name,
            description=kb_request.description or ""
        )
        
        kb = KnowledgeBase(
            id=collection_data["id"],
            name=collection_data["name"],
            description=collection_data.get("description", ""),
            created_at=collection_data["created_at"],
            document_count=0
        )
        
        logger.info(f"Created knowledge base: {kb.name}")
        return kb
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{kb_id}", response_model=KnowledgeBase)
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
                return KnowledgeBase(
                    id=collection["id"],
                    name=collection["name"],
                    description=collection.get("description", ""),
                    created_at=collection.get("created_at", ""),
                    document_count=collection.get("document_count", 0)
                )
        
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
    services = Depends(get_services)
):
    """删除知识库"""
    try:
        services.vector_db_service.delete_collection(kb_id)
        logger.info(f"Deleted knowledge base: {kb_id}")
        return {"message": f"Knowledge base {kb_id} deleted successfully"}
        
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
            metadata = chunk["metadata"].copy()
            metadata["chunk_index"] = i
            metadata["total_chunks"] = len(chunks)
            metadatas.append(metadata)
        
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
            metadata = chunk["metadata"].copy()
            metadata["chunk_index"] = i
            metadata["total_chunks"] = len(chunks)
            metadatas.append(metadata)
        
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
        # 获取集合中的所有文档ID
        # 注意：ChromaDB 的 get() 方法有限制，这里我们使用一个技巧
        # 通过搜索一个不太可能匹配的查询来获取所有文档
        
        # 生成一个随机向量进行搜索
        import random
        random_embedding = [random.random() for _ in range(384)]  # 假设嵌入维度是384
        
        # 搜索大量结果
        results = services.vector_db_service.search(
            collection_name=kb_id,
            query_embedding=random_embedding,
            n_results=limit,
            filter=None
        )
        
        documents = []
        for result in results["results"]:
            doc_info = {
                "id": result["id"],
                "content_preview": result["document"][:200] + "..." if len(result["document"]) > 200 else result["document"],
                "metadata": result["metadata"],
                "created_at": result["metadata"].get("added_at", "")
            }
            documents.append(doc_info)
        
        return {
            "documents": documents,
            "total": len(documents),
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
            all_docs = await list_documents(kb_id, request, limit=10000, offset=0, services=services)
            
            for doc in all_docs["documents"]:
                if doc["created_at"] < cutoff_date_str:
                    documents_to_delete.append(doc["id"])
            
            logger.info(f"Found {len(documents_to_delete)} documents older than {delete_request.older_than_days} days")
        
        # 3. 如果指定了源匹配模式
        if delete_request.source_pattern:
            all_docs = await list_documents(kb_id, request, limit=10000, offset=0, services=services)
            
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
        all_docs = await list_documents(kb_id, request, limit=10000, offset=0, services=services)
        
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
        all_docs = await list_documents(kb_id, request, limit=10000, offset=0, services=services)
        
        # 统计信息
        stats = {
            "total_documents": len(all_docs["documents"]),
            "by_source": {},
            "by_date": {},
            "by_topic": {},
            "file_types": {}
        }
        
        # 分析每个文档
        for doc in all_docs["documents"]:
            metadata = doc["metadata"]
            
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
            stats["file_types"][extension] = stats["file_types"].get(extension, 0) + 1
        
        # 添加时间范围
        if all_docs["documents"]:
            dates = [doc["created_at"] for doc in all_docs["documents"] if doc.get("created_at")]
            if dates:
                stats["oldest_document"] = min(dates)
                stats["newest_document"] = max(dates)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get document stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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