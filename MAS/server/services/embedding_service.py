import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import os

logger = logging.getLogger(__name__)

from server.services.embedding_manager import BaseEmbeddingService

class EmbeddingService(BaseEmbeddingService):
    """文本嵌入服务"""
    
    def __init__(self, model_name: str = None):
        """
        初始化嵌入模型
        model_name: 使用的嵌入模型名称
        """
        # 可选的模型列表（按优先级排序）
        model_options = [
            "all-MiniLM-L6-v2",  # 轻量级，适合英文
            "paraphrase-multilingual-MiniLM-L12-v2",  # 多语言支持
            "distiluse-base-multilingual-cased-v1",  # 多语言，更大
            "all-mpnet-base-v2"  # 更准确，但更大
        ]
        
        # 如果指定了模型但格式不对，尝试修正
        if model_name and ":" in model_name:
            logger.warning(f"Invalid model name format: {model_name}. Using default model.")
            model_name = None
        
        # 选择模型
        selected_model = model_name if model_name else model_options[0]
        
        logger.info(f"Initializing embedding model: {selected_model}")
        try:
            # 设置缓存目录
            cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models", "embeddings")
            os.makedirs(cache_dir, exist_ok=True)
            
            # 加载模型
            self.model = SentenceTransformer(
                selected_model,
                cache_folder=cache_dir,
                device='cpu'  # 强制使用 CPU，避免 CUDA 问题
            )
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            self.model_name = selected_model
            logger.info(f"Embedding model loaded successfully: {selected_model}")
            logger.info(f"Embedding dimension: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"Failed to load model {selected_model}: {e}")
            # 尝试备选模型
            for backup_model in model_options[1:]:
                if backup_model == selected_model:
                    continue
                try:
                    logger.info(f"Trying backup model: {backup_model}")
                    self.model = SentenceTransformer(
                        backup_model,
                        cache_folder=cache_dir,
                        device='cpu'
                    )
                    self.embedding_dim = self.model.get_sentence_embedding_dimension()
                    self.model_name = backup_model
                    logger.info(f"Successfully loaded backup model: {backup_model}")
                    break
                except:
                    continue
            else:
                logger.error("Failed to load any embedding model")
                raise RuntimeError("No embedding model could be loaded")
    
    def embed_text(self, text: str) -> List[float]:
        """
        将单个文本转换为向量
        """
        try:
            # 限制文本长度，避免超出模型限制
            if len(text) > 5000:
                text = text[:5000]
                logger.warning("Text truncated to 5000 characters")
            
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        批量将文本转换为向量
        """
        try:
            # 限制每个文本的长度
            processed_texts = []
            for text in texts:
                if len(text) > 5000:
                    processed_texts.append(text[:5000])
                else:
                    processed_texts.append(text)
            
            embeddings = self.model.encode(
                processed_texts, 
                convert_to_numpy=True,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to embed texts: {e}")
            raise
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        """
        try:
            # 转换为 numpy 数组
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "max_sequence_length": getattr(self.model, 'max_seq_length', 512)
        }