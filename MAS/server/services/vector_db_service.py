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
            # 检查默认集合是否存在
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
            else:
                # 如果存在但没有元数据，我们无法更新它
                # ChromaDB 不支持更新集合元数据
                pass
        except Exception as e:
            logger.error(f"Failed to create default collection: {e}")
    
    def create_collection(self, name: str, description: str = "", metadata: Optional[Dict[str, Any]] = None, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """创建新的知识库集合"""
        try:
            # 使用指定的ID或生成新的
            if collection_id is None:
                collection_id = str(uuid.uuid4())
            
            # 检查集合是否已存在
            existing_collections = [c.name for c in self.client.list_collections()]
            logger.info(f"Existing collections: {existing_collections}")
            logger.info(f"Trying to create collection with id: {collection_id}")
            logger.info(f"Collection display name: {name}")
            
            # 如果集合已存在，生成新的ID
            retry_count = 0
            while collection_id in existing_collections and retry_count < 5:
                logger.warning(f"Collection ID {collection_id} already exists, generating new one...")
                collection_id = str(uuid.uuid4())
                retry_count += 1
                
            if collection_id in existing_collections:
                raise ValueError(f"Failed to generate unique collection ID after {retry_count} attempts")
            
            # 创建集合
            collection_metadata = {
                "description": str(description or ""),  # 确保是字符串
                "created_at": datetime.now().isoformat(),
                "document_count": 0,
                "status": "draft",  # 默认为草稿状态
                "device_id": "",  # 创建设备ID
                "device_name": "",  # 创建设备名称
                "published_at": "",  # 发布时间
                "original_name": name  # 原始名称（不含设备后缀）
            }
            
            # 添加额外的元数据，过滤掉None值并转换为字符串
            if metadata:
                for key, value in metadata.items():
                    if value is not None:  # 只添加非None值
                        # ChromaDB只支持字符串、数字和布尔值
                        if isinstance(value, bool):
                            collection_metadata[key] = value
                        elif isinstance(value, (int, float)):
                            collection_metadata[key] = value
                        else:
                            collection_metadata[key] = str(value)
            
            # 在元数据中保存显示名称
            collection_metadata["display_name"] = name
            
            collection = self.client.create_collection(
                name=collection_id,  # 使用ID作为collection的名称
                metadata=collection_metadata
            )
            
            logger.info(f"Created collection: {name} with id: {collection_id}")
            return {
                "id": collection_id,
                "name": name,  # 返回显示名称
                "description": description,
                "created_at": datetime.now().isoformat(),
                "document_count": 0,
                "status": collection_metadata.get("status", "draft"),
                "device_id": collection_metadata.get("device_id", ""),
                "device_name": collection_metadata.get("device_name", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def list_collections(self, device_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出知识库集合
        
        Args:
            device_id: 如果指定，只返回该设备的知识库
            status: 如果指定，只返回该状态的知识库（draft/published）
        """
        try:
            collections = []
            for collection in self.client.list_collections():
                metadata = collection.metadata or {}
                
                # 过滤条件
                if device_id and metadata.get("device_id") != device_id:
                    continue
                if status and metadata.get("status", "draft") != status:
                    continue
                
                # 如果没有 created_at，使用当前时间
                created_at = metadata.get("created_at")
                if not created_at:
                    created_at = datetime.now().isoformat()
                
                collections.append({
                    "id": collection.name,  # collection的实际ID
                    "name": metadata.get("display_name", collection.name),  # 显示名称
                    "description": metadata.get("description", ""),
                    "created_at": created_at,
                    "document_count": collection.count(),
                    "status": metadata.get("status", "draft"),
                    "device_id": metadata.get("device_id", ""),
                    "device_name": metadata.get("device_name", ""),
                    "published_at": metadata.get("published_at", ""),
                    "original_name": metadata.get("original_name", "")
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
    
    def publish_collection(self, collection_id: str, new_name: Optional[str] = None) -> Dict[str, Any]:
        """发布知识库（从草稿状态改为公开状态）
        
        Args:
            collection_id: 集合ID
            new_name: 新的显示名称（可选）
            
        Returns:
            更新后的集合信息
        """
        try:
            # 获取集合
            collection = self.client.get_collection(name=collection_id)
            metadata = collection.metadata or {}
            
            # 检查是否已经发布
            if metadata.get("status") == "published":
                raise ValueError("Collection is already published")
            
            # 获取所有文档和嵌入
            all_docs = collection.get(include=["documents", "embeddings", "metadatas"])
            
            # 创建新的元数据
            new_metadata = metadata.copy()
            new_metadata["status"] = "published"
            new_metadata["published_at"] = datetime.now().isoformat()
            if new_name:
                new_metadata["display_name"] = new_name
            
            # 由于ChromaDB不支持直接更新元数据，需要重新创建集合
            # 首先删除旧集合
            self.client.delete_collection(name=collection_id)
            
            # 创建新集合
            new_collection = self.client.create_collection(
                name=collection_id,
                metadata=new_metadata
            )
            
            # 重新添加所有文档
            if all_docs['ids']:
                new_collection.add(
                    ids=all_docs['ids'],
                    documents=all_docs['documents'],
                    embeddings=all_docs['embeddings'],
                    metadatas=all_docs['metadatas']
                )
            
            logger.info(f"Published collection: {collection_id}")
            
            return {
                "id": collection_id,
                "name": new_metadata.get("display_name", collection_id),
                "description": new_metadata.get("description", ""),
                "status": "published",
                "published_at": new_metadata["published_at"],
                "document_count": new_collection.count()
            }
            
        except Exception as e:
            logger.error(f"Failed to publish collection: {e}")
            raise
    
    def check_name_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """检查知识库名称是否已存在
        
        Args:
            name: 要检查的名称
            exclude_id: 排除的集合ID（用于更新时排除自己）
            
        Returns:
            True 如果名称已存在，否则 False
        """
        try:
            for collection in self.client.list_collections():
                if collection.name == exclude_id:
                    continue
                    
                metadata = collection.metadata or {}
                display_name = metadata.get("display_name", collection.name)
                
                # 只检查公开的知识库
                if metadata.get("status") == "published" and display_name == name:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to check name existence: {e}")
            raise