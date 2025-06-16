"""
简单的向量数据库实现（ChromaDB替代方案）
使用numpy和文件存储实现基本的向量搜索功能
"""
import json
import os
import numpy as np
from typing import List, Dict, Any, Optional
import pickle
from pathlib import Path

class SimpleVectorDB:
    """简单的向量数据库实现"""
    
    def __init__(self, persist_directory: str = "./simple_vector_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collections = {}
        self._load_collections()
    
    def create_collection(self, name: str, metadata: Dict[str, Any] = None):
        """创建集合"""
        if name not in self.collections:
            self.collections[name] = {
                "vectors": [],
                "documents": [],
                "metadatas": [],
                "ids": [],
                "metadata": metadata or {}
            }
            self._save_collection(name)
        return self.collections[name]
    
    def add_documents(self, collection_name: str, documents: List[str], 
                     embeddings: List[List[float]], metadatas: List[Dict[str, Any]] = None,
                     ids: List[str] = None):
        """添加文档"""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")
        
        collection = self.collections[collection_name]
        n_docs = len(documents)
        
        if ids is None:
            ids = [f"doc_{len(collection['ids']) + i}" for i in range(n_docs)]
        
        if metadatas is None:
            metadatas = [{} for _ in range(n_docs)]
        
        collection["documents"].extend(documents)
        collection["vectors"].extend(embeddings)
        collection["metadatas"].extend(metadatas)
        collection["ids"].extend(ids)
        
        self._save_collection(collection_name)
        return ids
    
    def search(self, collection_name: str, query_embedding: List[float], 
              n_results: int = 10) -> Dict[str, List[Any]]:
        """搜索相似文档"""
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")
        
        collection = self.collections[collection_name]
        if not collection["vectors"]:
            return {"results": []}
        
        # 计算余弦相似度
        query_vec = np.array(query_embedding)
        vectors = np.array(collection["vectors"])
        
        # 归一化
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        vectors_norm = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)
        
        # 计算相似度
        similarities = np.dot(vectors_norm, query_norm)
        
        # 获取top-k结果
        top_indices = np.argsort(similarities)[::-1][:n_results]
        
        results = []
        for idx in top_indices:
            results.append({
                "id": collection["ids"][idx],
                "document": collection["documents"][idx],
                "metadata": collection["metadatas"][idx],
                "distance": float(1 - similarities[idx])  # 转换为距离
            })
        
        return {"results": results}
    
    def delete_collection(self, name: str):
        """删除集合"""
        if name in self.collections:
            del self.collections[name]
            collection_file = self.persist_directory / f"{name}.pkl"
            if collection_file.exists():
                collection_file.unlink()
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return list(self.collections.keys())
    
    def _save_collection(self, name: str):
        """保存集合到文件"""
        collection_file = self.persist_directory / f"{name}.pkl"
        with open(collection_file, "wb") as f:
            pickle.dump(self.collections[name], f)
    
    def _load_collections(self):
        """从文件加载集合"""
        for collection_file in self.persist_directory.glob("*.pkl"):
            name = collection_file.stem
            with open(collection_file, "rb") as f:
                self.collections[name] = pickle.load(f)

# 全局实例
_simple_db = None

def get_simple_vector_db(persist_directory: str = "./simple_vector_db") -> SimpleVectorDB:
    """获取简单向量数据库实例"""
    global _simple_db
    if _simple_db is None:
        _simple_db = SimpleVectorDB(persist_directory)
    return _simple_db
