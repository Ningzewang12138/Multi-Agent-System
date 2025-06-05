import logging
from typing import List, Dict, Any
import requests
import numpy as np

logger = logging.getLogger(__name__)

from server.services.embedding_manager import BaseEmbeddingService

class OllamaEmbeddingService(BaseEmbeddingService):
    """使用 Ollama 的嵌入服务"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "nomic-embed-text:latest"):
        """
        初始化 Ollama 嵌入服务
        """
        self.base_url = base_url
        self.model_name = model_name
        self.embedding_dim = None
        
        # 测试连接并获取嵌入维度
        self._test_embedding()
    
    def _test_embedding(self):
        """测试嵌入功能并获取维度"""
        try:
            test_embedding = self.embed_text("test")
            self.embedding_dim = len(test_embedding)
            logger.info(f"Ollama embedding service initialized with model: {self.model_name}")
            logger.info(f"Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama embedding service: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """使用 Ollama 生成文本嵌入"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama embedding failed: {response.text}")
            
            data = response.json()
            embedding = data.get("embedding", [])
            
            if not embedding:
                raise Exception("No embedding returned from Ollama")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量生成文本嵌入"""
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                embedding = self.embed_text(text)
                embeddings.append(embedding)
        return embeddings
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算余弦相似度"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "provider": "ollama"
        }