"""
WebSocket连接管理器
管理客户端的WebSocket连接，支持实时消息推送
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from uuid import uuid4

from server.models.message import Message, MessageStatus
from server.services.device_discovery_service import discovery_service

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # device_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # WebSocket -> device_id (反向映射)
        self.websocket_to_device: Dict[WebSocket, str] = {}
        # 连接锁
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, device_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        
        # 如果设备不存在，自动注册
        device = discovery_service.get_device_by_id(device_id)
        if not device:
            # 获取客户端IP
            client_ip = "unknown"
            if hasattr(websocket, 'client') and websocket.client:
                client_ip = websocket.client.host
            
            discovery_service.register_device(
                device_id=device_id,
                device_name=f"Device-{device_id[:8]}",
                device_type="client",
                ip_address=client_ip
            )
        
        async with self._lock:
            # 如果设备已有连接，先断开旧连接
            if device_id in self.active_connections:
                old_websocket = self.active_connections[device_id]
                try:
                    await old_websocket.close()
                except Exception:
                    pass
                if old_websocket in self.websocket_to_device:
                    del self.websocket_to_device[old_websocket]
            
            # 保存新连接
            self.active_connections[device_id] = websocket
            self.websocket_to_device[websocket] = device_id
            
        logger.info(f"Device {device_id} connected via WebSocket")
        
        # 发送连接成功消息
        await self.send_personal_message(
            device_id,
            {
                "type": "connection",
                "status": "connected",
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        async with self._lock:
            device_id = self.websocket_to_device.get(websocket)
            
            if device_id:
                if device_id in self.active_connections:
                    del self.active_connections[device_id]
                if websocket in self.websocket_to_device:
                    del self.websocket_to_device[websocket]
                
                logger.info(f"Device {device_id} disconnected from WebSocket")
    
    async def send_personal_message(self, device_id: str, message: dict):
        """发送消息给特定设备"""
        if device_id in self.active_connections:
            websocket = self.active_connections[device_id]
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message to device {device_id}: {e}")
                # 连接可能已断开，清理
                await self.disconnect(websocket)
                return False
        return False
    
    async def broadcast(self, message: dict, exclude_device: Optional[str] = None):
        """广播消息给所有连接的设备"""
        disconnected = []
        
        for device_id, websocket in self.active_connections.items():
            if device_id == exclude_device:
                continue
                
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to device {device_id}: {e}")
                disconnected.append(websocket)
        
        # 清理断开的连接
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def send_message(self, message: Message):
        """发送聊天消息给接收者"""
        # 构建消息数据
        message_data = {
            "type": "message",
            "message": {
                "id": message.id,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "content": message.content,
                "message_type": message.type.value,
                "created_at": message.created_at.isoformat(),
                "metadata": message.metadata
            }
        }
        
        # 发送给接收者
        success = await self.send_personal_message(
            message.recipient_id,
            message_data
        )
        
        if success:
            # 如果接收者在线，更新消息状态为已送达
            message.status = MessageStatus.DELIVERED
            message.delivered_at = datetime.now()
            
            # 发送送达确认给发送者
            await self.send_delivery_receipt(
                message.sender_id,
                message.id,
                MessageStatus.DELIVERED
            )
        
        return success
    
    async def send_delivery_receipt(self, device_id: str, message_id: str, status: MessageStatus):
        """发送消息状态更新"""
        receipt_data = {
            "type": "receipt",
            "message_id": message_id,
            "status": status.value,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_personal_message(device_id, receipt_data)
    
    async def send_typing_indicator(self, sender_id: str, recipient_id: str, is_typing: bool):
        """发送输入状态指示"""
        indicator_data = {
            "type": "typing",
            "sender_id": sender_id,
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_personal_message(recipient_id, indicator_data)
    
    def is_device_online(self, device_id: str) -> bool:
        """检查设备是否在线（WebSocket连接）"""
        return device_id in self.active_connections
    
    def get_online_devices(self) -> Set[str]:
        """获取所有在线设备ID"""
        return set(self.active_connections.keys())
    
    async def handle_websocket(self, websocket: WebSocket, device_id: str):
        """处理WebSocket连接的主循环"""
        await self.connect(websocket, device_id)
        
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_json()
                
                # 处理不同类型的消息
                message_type = data.get("type")
                
                if message_type == "ping":
                    # 心跳响应
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "typing":
                    # 转发输入状态
                    recipient_id = data.get("recipient_id")
                    is_typing = data.get("is_typing", False)
                    if recipient_id:
                        await self.send_typing_indicator(
                            device_id,
                            recipient_id,
                            is_typing
                        )
                
                elif message_type == "read_receipt":
                    # 处理已读回执
                    message_ids = data.get("message_ids", [])
                    if message_ids:
                        # 这里应该更新消息状态并通知发送者
                        # 需要与消息存储服务集成
                        pass
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
        except WebSocketDisconnect:
            logger.info(f"Device {device_id} disconnected normally")
        except Exception as e:
            logger.error(f"WebSocket error for device {device_id}: {e}")
        finally:
            await self.disconnect(websocket)


# 全局连接管理器实例
connection_manager = ConnectionManager()
