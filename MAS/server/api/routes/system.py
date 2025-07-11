from fastapi import APIRouter, Depends, Request, HTTPException
import platform
import psutil
import sys
import os
import logging
from typing import Optional
from datetime import datetime

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, server_dir)

from server.services.ollama_service import OllamaService
from server.services.device_discovery_service import discovery_service

# 创建 logger 实例
logger = logging.getLogger(__name__)

router = APIRouter()

def get_ollama_service(request: Request) -> OllamaService:
    """从 FastAPI 应用状态获取 OllamaService"""
    return request.app.state.services.ollama_service

@router.get("/health")
async def health_check(
    request: Request,
    ollama: OllamaService = Depends(get_ollama_service)
):
    """健康检查"""
    logger.info("Health check requested")
    
    # 先检查服务是否存在
    if ollama is None:
        logger.error("OllamaService is not initialized")
        return {
            "status": "unhealthy",
            "ollama_connected": False,
            "model_count": 0,
            "error": "OllamaService not initialized"
        }
    
    try:
        models = ollama.list_models()
        is_healthy = len(models) > 0
        
        health_status = {
            "status": "healthy" if is_healthy else "unhealthy",
            "ollama_connected": is_healthy,
            "model_count": len(models)
        }
        
        if is_healthy:
            logger.info(f"Health check passed: {len(models)} models available")
        else:
            logger.warning("Health check failed: No models found")
            
        return health_status
    except Exception as e:
        logger.error(f"Health check failed with error: {e}")
        return {
            "status": "unhealthy",
            "ollama_connected": False,
            "model_count": 0,
            "error": str(e)
        }

@router.get("/info")
async def system_info():
    """获取系统信息"""
    logger.info("System info requested")
    try:
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }
        logger.info("System info retrieved successfully")
        return info
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise

@router.get("/debug/ollama")
async def debug_ollama_connection(request: Request):
    """调试 Ollama 连接"""
    import requests
    from datetime import datetime
    
    logger.info("Starting Ollama connection debug")
    
    results = {
        "ollama_url": "http://localhost:11434",
        "timestamp": datetime.now().isoformat(),
        "service_status": "initialized" if hasattr(request.app.state, 'services') and request.app.state.services.ollama_service else "not initialized",
        "checks": {}
    }
    
    # 检查基础连接
    try:
        logger.debug("Testing base connection to Ollama")
        response = requests.get("http://localhost:11434", timeout=5)
        results["checks"]["base_connection"] = {
            "status": "success",
            "status_code": response.status_code
        }
        logger.info("Base connection successful")
    except Exception as e:
        logger.error(f"Base connection failed: {e}")
        results["checks"]["base_connection"] = {
            "status": "failed",
            "error": str(e)
        }
    
    # 检查 v1 API 端点
    try:
        logger.debug("Testing v1/models endpoint")
        response = requests.get("http://localhost:11434/v1/models", timeout=5)
        data = response.json()
        results["checks"]["v1_models_endpoint"] = {
            "status": "success",
            "status_code": response.status_code,
            "model_count": len(data.get("data", [])),
            "models": [m.get("id", "unknown") for m in data.get("data", [])]
        }
        logger.info(f"v1/models endpoint successful, found {len(data.get('data', []))} models")
    except Exception as e:
        logger.error(f"v1/models endpoint failed: {e}")
        results["checks"]["v1_models_endpoint"] = {
            "status": "failed",
            "error": str(e)
        }
    
    logger.info("Ollama connection debug completed")
    return results

@router.get("/embeddings/status")
async def embedding_status(request: Request):
    """获取嵌入服务状态"""
    embedding_manager = request.app.state.services.embedding_manager
    
    if embedding_manager is None:
        return {
            "status": "disabled",
            "message": "No embedding service available",
            "health": {
                "all_healthy": False,
                "has_healthy_service": False
            }
        }
    
    # 获取健康状态
    health_status = embedding_manager.get_health_status()
    
    return {
        "status": "active" if health_status["has_healthy_service"] else "degraded",
        "health": health_status,
        "default_service": embedding_manager.default_service
    }

@router.post("/embeddings/check")
async def check_embedding_services(request: Request):
    """检查所有嵌入服务的健康状态"""
    embedding_manager = request.app.state.services.embedding_manager
    
    if embedding_manager is None:
        raise HTTPException(status_code=503, detail="Embedding service not available")
    
    try:
        # 执行健康检查
        check_results = embedding_manager.check_all_services()
        
        # 获取更新后的健康状态
        health_status = embedding_manager.get_health_status()
        
        return {
            "message": "Health check completed",
            "check_results": check_results,
            "health_status": health_status
        }
    except Exception as e:
        logger.error(f"Failed to check embedding services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/embeddings/test")
async def test_embeddings(
    request: Request,
    text: str = "Hello, this is a test.",
    service_name: Optional[str] = None
):
    """测试嵌入服务"""
    embedding_manager = request.app.state.services.embedding_manager
    
    if embedding_manager is None:
        raise HTTPException(status_code=503, detail="Embedding service not available")
    
    try:
        if service_name:
            # 测试特定服务
            embedding = embedding_manager.embed_text(text, service_name)
            service, actual_service_name = embedding_manager.get_service(service_name)
            return {
                "requested_service": service_name,
                "actual_service": actual_service_name,
                "text": text,
                "embedding_dimension": len(embedding),
                "embedding_sample": embedding[:10],  # 只返回前10个值
                "model_info": service.get_model_info()
            }
        else:
            # 比较所有服务
            return {
                "text": text,
                "comparisons": embedding_manager.compare_embeddings(text)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/discovery/status")
async def device_discovery_status():
    """获取设备发现服务状态"""
    logger.info("Device discovery status requested")
    
    try:
        # 获取当前设备信息
        current_device = discovery_service.device_info
        
        # 获取所有设备
        all_devices = discovery_service.get_all_devices()
        online_devices = discovery_service.get_online_devices()
        
        status = {
            "service_running": discovery_service.running,
            "discovery_port": discovery_service.discovery_port,
            "broadcast_interval": discovery_service.broadcast_interval,
            "device_timeout": discovery_service.device_timeout,
            "current_device": {
                "id": current_device.id,
                "name": current_device.name,
                "ip_address": current_device.ip_address,
                "port": current_device.port,
                "platform": current_device.platform,
                "type": current_device.type
            },
            "discovered_devices": {
                "total": len(all_devices),
                "online": len(online_devices),
                "offline": len(all_devices) - len(online_devices)
            },
            "devices": [
                {
                    "id": device.id,
                    "name": device.name,
                    "ip_address": device.ip_address,
                    "status": device.status,
                    "last_seen": device.last_seen.isoformat()
                }
                for device in all_devices
            ]
        }
        
        logger.info(f"Discovery status: {len(all_devices)} devices found")
        return status
        
    except Exception as e:
        logger.error(f"Failed to get discovery status: {e}")
        raise HTTPException(status_code=500, detail=str(e))