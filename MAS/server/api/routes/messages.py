"""
消息路由 API
处理客户端之间的消息传递
"""
from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict
import logging
import uuid
from datetime import datetime

from server.models.message import (
    Message, MessageStatus, MessageType,
    SendMessageRequest, MessageListRequest, 
    UpdateMessageStatusRequest, ChatSession
)
from server.services.message_storage_service import message_storage
from server.services.websocket_manager import connection_manager
from server.services.device_discovery_service import discovery_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== WebSocket 端点 ==========

@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """WebSocket连接端点"""
    # 允许任何设备ID连接（设备会在连接时自动注册）
    logger.info(f"WebSocket connection request from device: {device_id}")
    
    # 处理WebSocket连接
    await connection_manager.handle_websocket(websocket, device_id)


# ========== 消息发送 API ==========

@router.post("/send")
async def send_message(
    request: Request,
    message_request: SendMessageRequest
):
    """发送消息到指定设备"""
    try:
        # 获取发送者信息
        sender_id = request.headers.get('X-Device-ID', discovery_service.device_id)
        sender_device = discovery_service.get_device_by_id(sender_id)
        if not sender_device and sender_id != discovery_service.device_id:
            # 如果是服务器自己发送
            sender_device = discovery_service.device_info
        
        # 验证接收者（如果设备未注册，使用默认值）
        recipient_device = discovery_service.get_device_by_id(message_request.recipient_id)
        recipient_name = recipient_device.name if recipient_device else message_request.recipient_id
        
        # 创建消息
        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_name=sender_device.name if sender_device else "Unknown",
            recipient_id=message_request.recipient_id,
            recipient_name=recipient_name,
            content=message_request.content,
            type=message_request.type,
            status=MessageStatus.SENT,
            metadata=message_request.metadata
        )
        
        # 保存消息
        if not message_storage.save_message(message):
            raise HTTPException(status_code=500, detail="Failed to save message")
        
        # 尝试通过WebSocket实时发送
        ws_sent = await connection_manager.send_message(message)
        
        if ws_sent:
            # 更新消息状态
            message_storage.update_message_status(
                [message.id], 
                MessageStatus.DELIVERED
            )
        
        logger.info(f"Message {message.id} sent from {sender_id} to {message_request.recipient_id}")
        
        return {
            "message_id": message.id,
            "status": message.status.value,
            "delivered": ws_sent,
            "created_at": message.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 消息查询 API ==========

@router.post("/list")
async def list_messages(
    request: Request,
    list_request: MessageListRequest
):
    """获取消息列表"""
    try:
        # 获取请求设备ID
        device_id = request.headers.get('X-Device-ID', discovery_service.device_id)
        
        # 如果指定了对方设备ID，创建或获取会话
        if list_request.device_id:
            # 获取会话ID
            device1_name = discovery_service.device_info.name if device_id == discovery_service.device_id else "Device"
            device2 = discovery_service.get_device_by_id(list_request.device_id)
            if not device2:
                raise HTTPException(status_code=404, detail="Device not found")
            
            session_id = message_storage.create_or_get_session(
                device_id, device1_name,
                list_request.device_id, device2.name
            )
        else:
            session_id = list_request.session_id
        
        # 获取消息
        messages = message_storage.get_messages(
            session_id=session_id,
            limit=list_request.limit,
            before_id=list_request.before_id,
            after_id=list_request.after_id
        )
        
        # 标记发给当前设备的消息为已读
        unread_message_ids = [
            msg.id for msg in messages 
            if msg.recipient_id == device_id and msg.status != MessageStatus.READ
        ]
        
        if unread_message_ids:
            message_storage.update_message_status(
                unread_message_ids,
                MessageStatus.READ
            )
            
            # 发送已读回执
            for msg in messages:
                if msg.id in unread_message_ids:
                    await connection_manager.send_delivery_receipt(
                        msg.sender_id,
                        msg.id,
                        MessageStatus.READ
                    )
        
        return {
            "messages": [msg.dict() for msg in messages],
            "count": len(messages),
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 会话管理 API ==========

@router.get("/sessions")
async def list_sessions(request: Request):
    """获取设备的所有会话"""
    try:
        # 获取请求设备ID
        device_id = request.headers.get('X-Device-ID', discovery_service.device_id)
        
        # 获取会话列表
        sessions = message_storage.get_sessions(device_id)
        
        # 补充在线状态
        for session in sessions:
            for participant_id in session.participant_ids:
                if participant_id != device_id:
                    # 检查对方是否在线
                    is_online = connection_manager.is_device_online(participant_id)
                    session_dict = session.dict()
                    session_dict['online_status'] = {participant_id: is_online}
                    
        return {
            "sessions": [session.dict() for session in sessions],
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    """删除会话及其所有消息"""
    try:
        # 验证权限（确保是会话参与者）
        device_id = request.headers.get('X-Device-ID', discovery_service.device_id)
        
        # 从session_id解析参与者
        parts = session_id.split('_')
        if len(parts) != 2 or device_id not in parts:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # 删除会话
        if message_storage.delete_session(session_id):
            return {"message": "Session deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete session")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 消息状态更新 API ==========

@router.put("/status")
async def update_message_status(
    request: Request,
    status_request: UpdateMessageStatusRequest
):
    """更新消息状态"""
    try:
        # 获取请求设备ID
        device_id = request.headers.get('X-Device-ID', discovery_service.device_id)
        
        # 更新状态
        updated_count = message_storage.update_message_status(
            status_request.message_ids,
            status_request.status
        )
        
        # 如果是已读状态，发送回执给发送者
        if status_request.status == MessageStatus.READ:
            # 获取消息信息以找到发送者
            for message_id in status_request.message_ids:
                messages = message_storage.get_messages(limit=1, after_id=message_id)
                if messages:
                    msg = messages[0]
                    if msg.recipient_id == device_id:
                        await connection_manager.send_delivery_receipt(
                            msg.sender_id,
                            msg.id,
                            MessageStatus.READ
                        )
        
        return {
            "updated_count": updated_count,
            "status": status_request.status.value
        }
        
    except Exception as e:
        logger.error(f"Failed to update message status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 在线状态 API ==========

@router.get("/online")
async def get_online_devices():
    """获取当前在线的设备（WebSocket连接）"""
    try:
        online_device_ids = connection_manager.get_online_devices()
        
        # 获取设备详细信息
        online_devices = []
        for device_id in online_device_ids:
            device = discovery_service.get_device_by_id(device_id)
            if device:
                online_devices.append({
                    "id": device.id,
                    "name": device.name,
                    "type": device.type,
                    "platform": device.platform
                })
            elif device_id == discovery_service.device_id:
                # 服务器自己
                online_devices.append({
                    "id": discovery_service.device_id,
                    "name": discovery_service.device_info.name,
                    "type": discovery_service.device_info.type,
                    "platform": discovery_service.device_info.platform
                })
        
        return {
            "online_devices": online_devices,
            "count": len(online_devices)
        }
        
    except Exception as e:
        logger.error(f"Failed to get online devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 未读消息统计 API ==========

@router.get("/unread")
async def get_unread_count(request: Request):
    """获取未读消息统计"""
    try:
        # 获取请求设备ID
        device_id = request.headers.get('X-Device-ID', discovery_service.device_id)
        
        # 获取未读统计
        unread_counts = message_storage.get_unread_count(device_id)
        
        # 计算总未读数
        total_unread = sum(unread_counts.values())
        
        return {
            "total_unread": total_unread,
            "by_device": unread_counts
        }
        
    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))
