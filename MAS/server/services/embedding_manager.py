import logging
from typing import List, Dict, Any, Optional, Literal
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseEmbeddingService(ABC):
    """嵌入服务基类"""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        pass

class EmbeddingManager:
    """嵌入服务管理器，支持多种嵌入服务"""
    
    def __init__(self):
        self.services: Dict[str, BaseEmbeddingService] = {}
        self.default_service: Optional[str] = None
        
    def register_service(self, name: str, service: BaseEmbeddingService, set_as_default: bool = False):
        """注册嵌入服务"""
        self.services[name] = service
        if set_as_default or self.default_service is None:
            self.default_service = name
        logger.info(f"Registered embedding service: {name}")
        
    def get_service(self, name: Optional[str] = None) -> BaseEmbeddingService:
        """获取嵌入服务"""
        if name is None:
            name = self.default_service
        
        if name not in self.services:
            raise ValueError(f"Embedding service '{name}' not found")
            
        return self.services[name]
    
    def embed_text(self, text: str, service_name: Optional[str] = None) -> List[float]:
        """使用指定服务嵌入文本"""
        service = self.get_service(service_name)
        return service.embed_text(text)
    
    def embed_texts(self, texts: List[str], service_name: Optional[str] = None, batch_size: int = 32) -> List[List[float]]:
        """批量嵌入文本"""
        service = self.get_service(service_name)
        return service.embed_texts(texts, batch_size)
    
    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """列出所有可用的嵌入服务"""
        result = {}
        for name, service in self.services.items():
            result[name] = {
                "info": service.get_model_info(),
                "is_default": name == self.default_service
            }
        return result
    
    def compare_embeddings(self, text: str) -> Dict[str, List[float]]:
        """使用所有服务生成嵌入并比较"""
        results = {}
        for name, service in self.services.items():
            try:
                embedding = service.embed_text(text)
                results[name] = {
                    "embedding": embedding[:5] + ["..."] if len(embedding) > 5 else embedding,  # 只显示前5个值
                    "dimension": len(embedding)
                }
            except Exception as e:
                results[name] = {"error": str(e)}
        return results