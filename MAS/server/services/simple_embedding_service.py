"""
简单的嵌入服务实现
用于测试和备用
"""
import logging
import hashlib
from typing import List, Dict, Any
from server.services.embedding_manager import BaseEmbeddingService

logger = logging.getLogger(__name__)

class SimpleEmbeddingService(BaseEmbeddingService):
    """简单的嵌入服务（用于测试）"""
    
    def __init__(self):
        self.dimension = 384  # 模拟的嵌入维度
        logger.info("Initialized SimpleEmbeddingService")
    
    def embed_text(self, text: str) -> List[float]:
        """生成文本的模拟嵌入向量"""
        # 使用哈希生成伪随机但可重复的向量
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # 将哈希转换为浮点数向量
        embedding = []
        for i in range(0, len(hash_hex), 2):
            # 取两个十六进制字符转换为0-1之间的浮点数
            value = int(hash_hex[i:i+2], 16) / 255.0
            embedding.append(value)
            
        # 确保向量长度为指定维度
        while len(embedding) < self.dimension:
            embedding.append(0.0)
        
        return embedding[:self.dimension]
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量生成文本的模拟嵌入向量"""
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_text(text))
        return embeddings
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": "simple-embedding",
            "dimension": self.dimension,
            "description": "Simple hash-based embedding for testing"
        }
