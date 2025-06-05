import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class VectorDBService:
    """向量数据库服务（使用 ChromaDB）"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """初始化 ChromaDB"""
        try:
            # 确保目录存在
            os.makedirs(persist_directory, exist_ok=True)
            
            # 初始化 ChromaDB 客户端
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
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _ensure_default_collection(self):
        """确保默认集合存在"""
        try:
            self.client.get_or_create_collection(
                name="default",
                metadata={"description": "Default knowledge base"}
            )
        except Exception as e:
            logger.error(f"Failed to create default collection: {e}")
    
    def create_collection(self, name: str, description: str = "") -> Dict[str, Any]:
        """创建新的知识库集合"""
        try:
            # 检查集合是否已存在
            existing_collections = [c.name for c in self.client.list_collections()]
            if name in existing_collections:
                raise ValueError(f"Collection '{name}' already exists")
            
            # 创建集合
            collection = self.client.create_collection(
                name=name,
                metadata={
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "document_count": 0
                }
            )
            
            logger.info(f"Created collection: {name}")
            return {
                "id": name,
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "document_count": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """列出所有知识库集合"""
        try:
            collections = []
            for collection in self.client.list_collections():
                metadata = collection.metadata or {}
                collections.append({
                    "id": collection.name,
                    "name": collection.name,
                    "description": metadata.get("description", ""),
                    "created_at": metadata.get("created_at", ""),
                    "document_count": collection.count()
                })
            return collections
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise
    
    def delete_collection(self, name: str):
        """删除知识库集合"""
        try:
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
            collection = self.client.get_collection(name=collection_name)
            
            # 生成 ID
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(len(documents))]
            
            # 准备元数据
            if metadatas is None:
                metadatas = [{} for _ in range(len(documents))]
            
            # 为每个元数据添加时间戳
            for metadata in metadatas:
                metadata["added_at"] = datetime.now().isoformat()
            
            # 添加到集合
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # 更新集合元数据中的文档计数
            collection_metadata = collection.metadata or {}
            collection_metadata["document_count"] = collection.count()
            
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
            collection = self.client.get_collection(name=collection_name)
            
            # 执行搜索
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
            collection = self.client.get_collection(name=collection_name)
            collection.delete(ids=document_ids)
            
            # 更新文档计数
            collection_metadata = collection.metadata or {}
            collection_metadata["document_count"] = collection.count()
            
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