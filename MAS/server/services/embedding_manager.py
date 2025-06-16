import logging
from typing import List, Dict, Any, Optional, Literal, Tuple
from abc import ABC, abstractmethod
import time
from datetime import datetime, timedelta

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
    
    def is_healthy(self) -> bool:
        """检查服务是否健康"""
        try:
            # 尝试嵌入一个简单文本
            test_embedding = self.embed_text("test")
            return len(test_embedding) > 0
        except:
            return False

class ServiceHealth:
    """服务健康状态"""
    def __init__(self):
        self.is_healthy: bool = True
        self.last_error: Optional[str] = None
        self.last_check: Optional[datetime] = None
        self.failure_count: int = 0
        self.success_count: int = 0

class EmbeddingManager:
    """嵌入服务管理器，支持多种嵌入服务"""
    
    def __init__(self):
        self.services: Dict[str, BaseEmbeddingService] = {}
        self.default_service: Optional[str] = None
        self.service_health: Dict[str, ServiceHealth] = {}
        self.fallback_order: List[str] = []  # 服务降级顺序
        self.max_retries: int = 3
        self.retry_delay: float = 1.0
        
    def register_service(self, name: str, service: BaseEmbeddingService, set_as_default: bool = False):
        """注册嵌入服务"""
        self.services[name] = service
        self.service_health[name] = ServiceHealth()
        
        # 检查服务健康状态
        if service.is_healthy():
            self.service_health[name].is_healthy = True
            self.service_health[name].last_check = datetime.now()
            
            if set_as_default or self.default_service is None:
                self.default_service = name
            
            # 添加到降级顺序列表
            if name not in self.fallback_order:
                self.fallback_order.append(name)
            
            logger.info(f"Registered embedding service: {name} (healthy)")
        else:
            self.service_health[name].is_healthy = False
            self.service_health[name].last_error = "Initial health check failed"
            logger.warning(f"Registered embedding service: {name} (unhealthy)")
        
    def get_service(self, name: Optional[str] = None) -> Tuple[BaseEmbeddingService, str]:
        """获取嵌入服务，支持自动降级"""
        if name is None:
            name = self.default_service
        
        if name not in self.services:
            raise ValueError(f"Embedding service '{name}' not found")
        
        # 检查指定服务的健康状态
        if self.service_health[name].is_healthy:
            return self.services[name], name
        
        # 如果不健康，尝试降级到其他服务
        logger.warning(f"Service '{name}' is unhealthy, attempting fallback")
        
        for fallback_name in self.fallback_order:
            if fallback_name != name and self.service_health[fallback_name].is_healthy:
                logger.info(f"Falling back to service: {fallback_name}")
                return self.services[fallback_name], fallback_name
        
        # 如果所有服务都不健康，返回原始服务（可能会失败）
        logger.error("All embedding services are unhealthy")
        return self.services[name], name
    
    def embed_text(self, text: str, service_name: Optional[str] = None) -> List[float]:
        """使用指定服务嵌入文本，支持重试和降级"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                service, actual_service_name = self.get_service(service_name)
                
                # 执行嵌入
                result = service.embed_text(text)
                
                # 更新健康状态
                health = self.service_health[actual_service_name]
                health.is_healthy = True
                health.success_count += 1
                health.last_check = datetime.now()
                
                return result
                
            except Exception as e:
                last_error = e
                service_name_for_log = service_name or self.default_service
                logger.error(f"Embedding failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                # 更新健康状态
                if service_name_for_log in self.service_health:
                    health = self.service_health[service_name_for_log]
                    health.is_healthy = False
                    health.failure_count += 1
                    health.last_error = str(e)
                    health.last_check = datetime.now()
                
                # 等待后重试
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        # 所有重试都失败
        raise RuntimeError(f"All embedding attempts failed. Last error: {last_error}")
    
    def embed_texts(self, texts: List[str], service_name: Optional[str] = None, batch_size: int = 32) -> List[List[float]]:
        """批量嵌入文本，支持重试和降级"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                service, actual_service_name = self.get_service(service_name)
                
                # 执行批量嵌入
                result = service.embed_texts(texts, batch_size)
                
                # 更新健康状态
                health = self.service_health[actual_service_name]
                health.is_healthy = True
                health.success_count += 1
                health.last_check = datetime.now()
                
                return result
                
            except Exception as e:
                last_error = e
                service_name_for_log = service_name or self.default_service
                logger.error(f"Batch embedding failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                # 更新健康状态
                if service_name_for_log in self.service_health:
                    health = self.service_health[service_name_for_log]
                    health.is_healthy = False
                    health.failure_count += 1
                    health.last_error = str(e)
                    health.last_check = datetime.now()
                
                # 等待后重试
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        # 所有重试都失败
        raise RuntimeError(f"All batch embedding attempts failed. Last error: {last_error}")
    
    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """列出所有可用的嵌入服务及其健康状态"""
        result = {}
        for name, service in self.services.items():
            health = self.service_health.get(name)
            result[name] = {
                "info": service.get_model_info(),
                "is_default": name == self.default_service,
                "health": {
                    "is_healthy": health.is_healthy if health else False,
                    "last_error": health.last_error if health else None,
                    "last_check": health.last_check.isoformat() if health and health.last_check else None,
                    "failure_count": health.failure_count if health else 0,
                    "success_count": health.success_count if health else 0
                }
            }
        return result
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取嵌入服务的整体健康状态"""
        healthy_count = sum(1 for h in self.service_health.values() if h.is_healthy)
        total_count = len(self.services)
        
        return {
            "healthy_services": healthy_count,
            "total_services": total_count,
            "all_healthy": healthy_count == total_count and total_count > 0,
            "has_healthy_service": healthy_count > 0,
            "default_service": self.default_service,
            "default_healthy": self.service_health.get(self.default_service, ServiceHealth()).is_healthy if self.default_service else False,
            "services": self.list_services()
        }
    
    def check_all_services(self) -> Dict[str, bool]:
        """检查所有服务的健康状态"""
        results = {}
        
        for name, service in self.services.items():
            try:
                # 执行健康检查
                is_healthy = service.is_healthy()
                
                # 更新状态
                health = self.service_health[name]
                health.is_healthy = is_healthy
                health.last_check = datetime.now()
                
                if not is_healthy:
                    health.last_error = "Health check failed"
                
                results[name] = is_healthy
                
            except Exception as e:
                results[name] = False
                health = self.service_health[name]
                health.is_healthy = False
                health.last_error = str(e)
                health.last_check = datetime.now()
        
        return results
    
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