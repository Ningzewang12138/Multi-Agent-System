"""
P2P聊天API路由
提供聊天相关的HTTP和WebSocket端点
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import json

from server.services.p2p.chat_service import p2p_chat_service
from server.services.p2p.websocket_manager import ws_manager
from server.services.device_discovery_service import discovery_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 数据模型 ==========

class SendMessageRequest(BaseModel):
    """发送消息请求"""
    to_device_id: str = Field(..., description="接收方设备ID")
    content: str = Field(..., description="消息内容")
    message_type: str = Field(default="text", description="消息类型")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class MarkReadRequest(BaseModel):
    """标记已读请求"""
    session_id: str = Field(..., description="会话ID")
    message_ids: List[str] = Field(..., description="消息ID列表")


class GetMessagesRequest(BaseModel):
    """获取消息请求"""
    session_id: str = Field(..., description="会话ID")
    limit: int = Field(default=50, ge=1, le=200, description="消息数量限制")
    before_id: Optional[str] = Field(None, description="获取此ID之前的消息")


class TypingStatusRequest(BaseModel):
    """输入状态请求"""
    session_id: str = Field(..., description="会话ID")
    is_typing: bool = Field(..., description="是否正在输入")


# ========== HTTP API端点 ==========

@router.post("/send")
async def send_message(
    request: Request,
    message_request: SendMessageRequest
):
    """发送P2P聊天消息"""
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")
    
    try:
        # 检查接收方是否存在
        target_device = discovery_service.get_device_by_id(message_request.to_device_id)
        if not target_device:
            raise HTTPException(status_code=404, detail="Target device not found")
        
        # 发送消息
        message = await p2p_chat_service.send_message(
            from_device_id=device_id,
            to_device_id=message_request.to_device_id,
            content=message_request.content,
            message_type=message_request.message_type,
            metadata=message_request.metadata
        )
        
        return {
            "success": True,
            "message": message.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_chat_sessions(request: Request):
    """获取聊天会话列表"""
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")
    
    try:
        sessions = await p2p_chat_service.get_chat_sessions(device_id)
        
        # 增强会话信息
        for session in sessions:
            # 获取对方设备信息
            other_device = discovery_service.get_device_by_id(session['other_device_id'])
            if other_device:
                session['other_device'] = {
                    'id': other_device.id,
                    'name': other_device.name,
                    'type': other_device.type,
                    'platform': other_device.platform,
                    'status': other_device.status
                }
            else:
                session['other_device'] = {
                    'id': session['other_device_id'],
                    'name': 'Unknown Device',
                    'type': 'unknown',
                    'platform': 'unknown',
                    'status': 'offline'
                }
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages")
async def get_messages(
    request: Request,
    get_request: GetMessagesRequest
):
    """获取会话消息"""
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")
    
    try:
        messages = await p2p_chat_service.get_messages(
            device_id=device_id,
            session_id=get_request.session_id,
            limit=get_request.limit,
            before_id=get_request.before_id
        )
        
        return {
            "messages": [msg.to_dict() for msg in messages],
            "count": len(messages)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read")
async def mark_messages_read(
    request: Request,
    read_request: MarkReadRequest
):
    """标记消息已读"""
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")
    
    try:
        await p2p_chat_service.mark_messages_read(
            device_id=device_id,
            session_id=read_request.session_id,
            message_ids=read_request.message_ids
        )
        
        return {"success": True}
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to mark messages read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/typing")
async def update_typing_status(
    request: Request,
    typing_request: TypingStatusRequest
):
    """更新输入状态"""
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")
    
    try:
        await p2p_chat_service.broadcast_typing_status(
            device_id=device_id,
            session_id=typing_request.session_id,
            is_typing=typing_request.is_typing
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to update typing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/online")
async def get_online_devices(request: Request):
    """获取在线设备列表"""
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")
    
    try:
        # 获取所有在线设备
        online_devices = []
        all_devices = discovery_service.get_online_devices()
        
        for device in all_devices:
            if device.id != device_id:  # 排除自己
                online_devices.append({
                    'id': device.id,
                    'name': device.name,
                    'type': device.type,
                    'platform': device.platform,
                    'is_chat_online': ws_manager.is_device_online(device.id)
                })
        
        return {
            "devices": online_devices,
            "total": len(online_devices)
        }
        
    except Exception as e:
        logger.error(f"Failed to get online devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== WebSocket端点 ==========

@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """WebSocket连接端点"""
    await ws_manager.connect(websocket, device_id)
    
    # 注册到聊天服务
    await p2p_chat_service.register_device_connection(device_id, websocket)
    
    # 自动订阅设备频道
    await ws_manager.subscribe_to_channel(device_id, f"device:{device_id}")
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理WebSocket管理消息
            handled_message = await ws_manager.handle_message(device_id, message)
            
            if handled_message:
                # 处理聊天相关消息
                message_type = handled_message.get("type")
                
                if message_type == "send_message":
                    # 发送消息
                    await p2p_chat_service.send_message(
                        from_device_id=device_id,
                        to_device_id=handled_message["to_device_id"],
                        content=handled_message["content"],
                        message_type=handled_message.get("message_type", "text"),
                        metadata=handled_message.get("metadata")
                    )
                    
                elif message_type == "typing":
                    # 输入状态
                    await p2p_chat_service.broadcast_typing_status(
                        device_id=device_id,
                        session_id=handled_message["session_id"],
                        is_typing=handled_message.get("is_typing", False)
                    )
                    
                elif message_type == "mark_read":
                    # 标记已读
                    await p2p_chat_service.mark_messages_read(
                        device_id=device_id,
                        session_id=handled_message["session_id"],
                        message_ids=handled_message.get("message_ids", [])
                    )
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {device_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {device_id}: {e}")
    finally:
        await p2p_chat_service.unregister_device_connection(device_id)
        await ws_manager.disconnect(device_id)


@router.get("/ws/status")
async def get_websocket_status():
    """获取WebSocket服务状态"""
    return {
        "online_devices": ws_manager.get_online_devices(),
        "total_connections": len(ws_manager.active_connections),
        "subscriptions": {
            device_id: list(channels) 
            for device_id, channels in ws_manager.subscriptions.items()
        }
    }
