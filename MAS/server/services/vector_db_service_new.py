"""
向量数据库服务 - 支持ChromaDB和简单实现
"""
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# 尝试导入ChromaDB
CHROMADB_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
    logger.info("ChromaDB is available")
except ImportError:
    logger.warning("ChromaDB not available, will use simple vector DB implementation")

class VectorDBService:
    """向量数据库服务（支持ChromaDB和简单实现）"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """初始化向量数据库"""
        self.persist_directory = persist_directory
        self.use_simple_db = not CHROMADB_AVAILABLE
        
        try:
            # 确保目录存在
            os.makedirs(persist_directory, exist_ok=True)
            
            if CHROMADB_AVAILABLE:
                # 使用ChromaDB
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info(f"ChromaDB initialized with persist directory: {persist_directory}")
                
                # 获取或创建默认集合
                self._ensure_default_collection()
            else:
                # 使用简单实现
                from server.services.simple_vector_db import get_simple_vector_db
                self.client = get_simple_vector_db(persist_directory)
                logger.info(f"Simple Vector DB initialized with persist directory: {persist_directory}")
                
                # 创建默认集合
                if "default" not in self.client.list_collections():
                    self.client.create_collection("default", {
                        "description": "Default knowledge base",
                        "created_at": datetime.now().isoformat(),
                        "document_count": 0
                    })
            
        except ImportError as e:
            logger.error(f"Failed to import simple vector DB: {e}")
            logger.error("Please run install_dependencies.py first")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize vector DB: {e}")
            raise
    
    def _ensure_default_collection(self):
        """确保默认集合存在（仅ChromaDB）"""
        if not self.use_simple_db:
            try:
                existing_collections = [c.name for c in self.client.list_collections()]
                if "default" not in existing_collections:
                    self.client.create_collection(
                        name="default",
                        metadata={
                            "description": "Default knowledge base",
                            "created_at": datetime.now().isoformat(),
                            "document_count": 0
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to create default collection: {e}")
    
    def create_collection(self, name: str, description: str = "", metadata: Optional[Dict[str, Any]] = None, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """创建新的知识库集合"""
        try:
            # 使用指定的ID或生成新的
            if collection_id is None:
                collection_id = str(uuid.uuid4())
            
            # 准备元数据
            collection_metadata = {
                "description": str(description or ""),
                "created_at": datetime.now().isoformat(),
                "document_count": 0,
                "display_name": name  # 保存显示名称
            }
            
            # 添加额外的元数据
            if metadata:
                for key, value in metadata.items():
                    if value is not None:
                        # 确保值类型兼容
                        if isinstance(value, bool):
                            collection_metadata[key] = value
                        elif isinstance(value, (int, float)):
                            collection_metadata[key] = value
                        else:
                            collection_metadata[key] = str(value)
            
            if self.use_simple_db:
                # 简单DB实现
                self.client.create_collection(collection_id, collection_metadata)
            else:
                # ChromaDB实现
                # 检查集合是否已存在
                existing_collections = [c.name for c in self.client.list_collections()]
                
                # 如果集合已存在，生成新的ID
                retry_count = 0
                while collection_id in existing_collections and retry_count < 5:
                    logger.warning(f"Collection ID {collection_id} already exists, generating new one...")
                    collection_id = str(uuid.uuid4())
                    retry_count += 1
                
                if collection_id in existing_collections:
                    raise ValueError(f"Failed to generate unique collection ID after {retry_count} attempts")
                
                collection = self.client.create_collection(
                    name=collection_id,
                    metadata=collection_metadata
                )
            
            logger.info(f"Created collection: {name} with id: {collection_id}")
            return {
                "id": collection_id,
                "name": name,
                "description": description,
                "created_at": collection_metadata["created_at"],
                "document_count": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """列出所有知识库集合"""
        try:
            collections = []
            
            if self.use_simple_db:
                # 简单DB实现
                for coll_id in self.client.list_collections():
                    collection = self.client.collections[coll_id]
                    metadata = collection.get("metadata", {})
                    collections.append({
                        "id": coll_id,
                        "name": metadata.get("display_name", coll_id),
                        "description": metadata.get("description", ""),
                        "created_at": metadata.get("created_at", ""),
                        "document_count": len(collection.get("documents", []))
                    })
            else:
                # ChromaDB实现
                for collection in self.client.list_collections():
                    metadata = collection.metadata or {}
                    created_at = metadata.get("created_at", datetime.now().isoformat())
                    
                    collections.append({
                        "id": collection.name,
                        "name": metadata.get("display_name", collection.name),
                        "description": metadata.get("description", ""),
                        "created_at": created_at,
                        "document_count": collection.count()
                    })
            
            return collections
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise
    
    def delete_collection(self, name: str):
        """删除知识库集合"""
        try:
            if self.use_simple_db:
                self.client.delete_collection(name)
            else:
                self.client.delete_collection(name=name)
            
            logger.info(f"Deleted collection: {name}")
            
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """向集合中添加文档"""
        try:
            # 生成ID
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(len(documents))]
            
            # 准备元数据
            if metadatas is None:
                metadatas = [{} for _ in range(len(documents))]
            
            # 为每个元数据添加时间戳
            for metadata in metadatas:
                metadata["added_at"] = datetime.now().isoformat()
            
            if self.use_simple_db:
                # 简单DB实现
                return self.client.add_documents(
                    collection_name=collection_name,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
            else:
                # ChromaDB实现
                collection = self.client.get_collection(name=collection_name)
                collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"Added {len(documents)} documents to collection: {collection_name}")
                return ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """在集合中搜索相似文档"""
        try:
            if self.use_simple_db:
                # 简单DB实现（不支持filter）
                if filter:
                    logger.warning("Simple DB does not support filters, ignoring filter parameter")
                return self.client.search(
                    collection_name=collection_name,
                    query_embedding=query_embedding,
                    n_results=n_results
                )
            else:
                # ChromaDB实现
                collection = self.client.get_collection(name=collection_name)
                
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=filter
                )
                
                # 格式化结果
                formatted_results = []
                if results['ids'] and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        formatted_results.append({
                            "id": results['ids'][0][i],
                            "document": results['documents'][0][i] if results['documents'] else "",
                            "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                            "distance": results['distances'][0][i] if results['distances'] else 0
                        })
                
                return {
                    "results": formatted_results,
                    "total": len(formatted_results)
                }
            
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            raise
    
    def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """获取特定文档"""
        try:
            if self.use_simple_db:
                # 简单DB实现
                collection = self.client.collections.get(collection_name)
                if collection:
                    for i, doc_id in enumerate(collection["ids"]):
                        if doc_id == document_id:
                            return {
                                "id": doc_id,
                                "document": collection["documents"][i],
                                "metadata": collection["metadatas"][i],
                                "embedding": collection["vectors"][i]
                            }
                return None
            else:
                # ChromaDB实现
                collection = self.client.get_collection(name=collection_name)
                
                results = collection.get(
                    ids=[document_id],
                    include=["embeddings", "documents", "metadatas"]
                )
                
                if results['ids']:
                    return {
                        "id": results['ids'][0],
                        "document": results['documents'][0] if results['documents'] else "",
                        "metadata": results['metadatas'][0] if results['metadatas'] else {},
                        "embedding": results['embeddings'][0] if results['embeddings'] else []
                    }
                
                return None
            
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            raise
    
    def delete_documents(self, collection_name: str, document_ids: List[str]):
        """删除文档"""
        try:
            if self.use_simple_db:
                # 简单DB实现
                collection = self.client.collections.get(collection_name)
                if collection:
                    # 找到要删除的索引
                    indices_to_remove = []
                    for doc_id in document_ids:
                        if doc_id in collection["ids"]:
                            idx = collection["ids"].index(doc_id)
                            indices_to_remove.append(idx)
                    
                    # 从高到低排序，避免索引错位
                    for idx in sorted(indices_to_remove, reverse=True):
                        collection["ids"].pop(idx)
                        collection["documents"].pop(idx)
                        collection["vectors"].pop(idx)
                        collection["metadatas"].pop(idx)
                    
                    # 保存更改
                    self.client._save_collection(collection_name)
            else:
                # ChromaDB实现
                collection = self.client.get_collection(name=collection_name)
                collection.delete(ids=document_ids)
            
            logger.info(f"Deleted {len(document_ids)} documents from collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise
    
    def update_document(
        self,
        collection_name: str,
        document_id: str,
        document: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """更新文档"""
        try:
            if self.use_simple_db:
                # 简单DB实现
                collection = self.client.collections.get(collection_name)
                if collection and document_id in collection["ids"]:
                    idx = collection["ids"].index(document_id)
                    
                    if document is not None:
                        collection["documents"][idx] = document
                    if embedding is not None:
                        collection["vectors"][idx] = embedding
                    if metadata is not None:
                        metadata["updated_at"] = datetime.now().isoformat()
                        collection["metadatas"][idx] = metadata
                    
                    # 保存更改
                    self.client._save_collection(collection_name)
            else:
                # ChromaDB实现
                collection = self.client.get_collection(name=collection_name)
                
                update_params = {"ids": [document_id]}
                if document is not None:
                    update_params["documents"] = [document]
                if embedding is not None:
                    update_params["embeddings"] = [embedding]
                if metadata is not None:
                    metadata["updated_at"] = datetime.now().isoformat()
                    update_params["metadatas"] = [metadata]
                
                collection.update(**update_params)
            
            logger.info(f"Updated document {document_id} in collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            raise
