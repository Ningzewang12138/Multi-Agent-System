"""
P2P API路由
提供P2P连接相关的API端点
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging

from server.services.p2p_coordinator_service import p2p_coordinator
from server.services.device_discovery_service import discovery_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 数据模型 ==========

class P2PRegisterRequest(BaseModel):
    """P2P注册请求"""
    local_ip: str = Field(..., description="本地IP地址")
    local_port: int = Field(..., description="本地监听端口")
    device_name: Optional[str] = Field(None, description="设备名称")


class P2PPeerRequest(BaseModel):
    """获取对等设备信息请求"""
    peer_id: str = Field(..., description="目标设备ID")


class P2PNatPunchRequest(BaseModel):
    """NAT打洞请求"""
    peer_id: str = Field(..., description="目标设备ID")


# ========== API端点 ==========

@router.post("/register")
async def register_p2p_endpoint(
    request: Request,
    register_request: P2PRegisterRequest
):
    """注册P2P端点"""
    try:
        # 获取设备ID
        device_id = request.headers.get('X-Device-ID')
        if not device_id:
            raise HTTPException(status_code=400, detail="Device ID required")
        
        # 获取公网IP（从请求中）
        public_ip = request.client.host
        if request.headers.get('X-Forwarded-For'):
            public_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            public_ip = request.headers['X-Real-IP']
        
        # 获取设备名称
        device_name = register_request.device_name
        if not device_name:
            device = discovery_service.get_device_by_id(device_id)
            device_name = device.name if device else device_id
        
        # 注册端点
        endpoint = await p2p_coordinator.register_endpoint(
            device_id=device_id,
            device_name=device_name,
            local_ip=register_request.local_ip,
            local_port=register_request.local_port,
            public_ip=public_ip
        )
        
        logger.info(f"P2P endpoint registered: {device_id} at {register_request.local_ip}:{register_request.local_port}")
        
        return {
            "success": True,
            "endpoint": endpoint.to_dict(),
            "message": "P2P endpoint registered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register P2P endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peers")
async def list_available_peers(request: Request):
    """列出可用的对等设备"""
    try:
        device_id = request.headers.get('X-Device-ID')
        if not device_id:
            raise HTTPException(status_code=400, detail="Device ID required")
        
        peers = await p2p_coordinator.list_available_peers(device_id)
        
        return {
            "peers": peers,
            "count": len(peers)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list peers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/peer/info")
async def get_peer_connection_info(
    request: Request,
    peer_request: P2PPeerRequest
):
    """获取特定对等设备的连接信息"""
    try:
        device_id = request.headers.get('X-Device-ID')
        if not device_id:
            raise HTTPException(status_code=400, detail="Device ID required")
        
        peer_info = await p2p_coordinator.get_peer_info(device_id, peer_request.peer_id)
        
        if not peer_info:
            raise HTTPException(status_code=404, detail="Peer not found or not available")
        
        return {
            "success": True,
            "peer": peer_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get peer info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/punch")
async def request_nat_punch(
    request: Request,
    punch_request: P2PNatPunchRequest
):
    """请求NAT打洞协助"""
    try:
        device_id = request.headers.get('X-Device-ID')
        if not device_id:
            raise HTTPException(status_code=400, detail="Device ID required")
        
        result = await p2p_coordinator.request_nat_punch(device_id, punch_request.peer_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "NAT punch failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to request NAT punch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stun")
async def get_stun_server_info():
    """获取STUN服务器信息"""
    try:
        # 返回内置STUN服务信息
        return {
            "stun_servers": [
                {
                    "url": "stun:localhost:3478",
                    "type": "internal"
                },
                # 备用公共STUN服务器
                {
                    "url": "stun:stun.l.google.com:19302",
                    "type": "public"
                }
            ],
            "recommended": "internal"
        }
        
    except Exception as e:
        logger.error(f"Failed to get STUN info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class P2PRelayRequest(BaseModel):
    """中继服务请求"""
    peer_id: str = Field(..., description="需要中继的对等设备ID")


@router.post("/relay/request")
async def request_relay_service(
    request: Request,
    relay_request: P2PRelayRequest
):
    """请求中继服务（当P2P连接失败时的备用方案）"""
    try:
        device_id = request.headers.get('X-Device-ID')
        if not device_id:
            raise HTTPException(status_code=400, detail="Device ID required")
        
        # 这里可以实现中继服务的逻辑
        # 目前返回暂不支持
        return {
            "success": False,
            "message": "Relay service not implemented yet",
            "alternative": "Try establishing P2P connection again",
            "peer_id": relay_request.peer_id
        }
        
    except Exception as e:
        logger.error(f"Failed to request relay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_p2p_service_status():
    """获取P2P服务状态"""
    try:
        total_endpoints = len(p2p_coordinator.endpoints)
        
        # 统计NAT类型
        nat_types = {}
        for endpoint in p2p_coordinator.endpoints.values():
            nat_type = endpoint.nat_type
            nat_types[nat_type] = nat_types.get(nat_type, 0) + 1
        
        return {
            "status": "active",
            "total_endpoints": total_endpoints,
            "nat_types": nat_types,
            "features": {
                "nat_punch": True,
                "stun": True,
                "relay": False  # 暂未实现
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get P2P status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
