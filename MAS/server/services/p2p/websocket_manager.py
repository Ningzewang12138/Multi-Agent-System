"""
WebSocket连接管理器
处理实时双向通信
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 设备订阅的频道
        self.subscriptions: Dict[str, Set[str]] = {}  # device_id -> set of channels
        # 心跳追踪
        self.last_heartbeat: Dict[str, datetime] = {}
        # 启动心跳检查任务
        self._heartbeat_task = None
        
    async def connect(self, websocket: WebSocket, device_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[device_id] = websocket
        self.last_heartbeat[device_id] = datetime.now()
        
        # 发送连接成功消息
        await self.send_personal_message(device_id, {
            "type": "connected",
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"WebSocket connected: {device_id}")
        
        # 启动心跳检查
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._check_heartbeats())
    
    async def disconnect(self, device_id: str):
        """断开WebSocket连接"""
        if device_id in self.active_connections:
            websocket = self.active_connections[device_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"Error closing websocket for {device_id}: {e}")
            
            del self.active_connections[device_id]
        
        # 清理订阅
        if device_id in self.subscriptions:
            del self.subscriptions[device_id]
        
        # 清理心跳
        if device_id in self.last_heartbeat:
            del self.last_heartbeat[device_id]
        
        logger.info(f"WebSocket disconnected: {device_id}")
    
    async def send_personal_message(self, device_id: str, message: dict):
        """发送消息给特定设备"""
        if device_id in self.active_connections:
            websocket = self.active_connections[device_id]
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    logger.warning(f"WebSocket not connected for device {device_id}")
                    await self.disconnect(device_id)
            except Exception as e:
                logger.error(f"Error sending message to {device_id}: {e}")
                await self.disconnect(device_id)
    
    async def broadcast_to_channel(self, channel: str, message: dict, exclude_device: Optional[str] = None):
        """广播消息到频道的所有订阅者"""
        disconnected = []
        
        for device_id, channels in self.subscriptions.items():
            if channel in channels and device_id != exclude_device:
                if device_id in self.active_connections:
                    try:
                        await self.send_personal_message(device_id, message)
                    except Exception as e:
                        logger.error(f"Failed to send to {device_id}: {e}")
                        disconnected.append(device_id)
        
        # 清理断开的连接
        for device_id in disconnected:
            await self.disconnect(device_id)
    
    async def subscribe_to_channel(self, device_id: str, channel: str):
        """订阅频道"""
        if device_id not in self.subscriptions:
            self.subscriptions[device_id] = set()
        
        self.subscriptions[device_id].add(channel)
        logger.info(f"Device {device_id} subscribed to channel {channel}")
        
        # 通知订阅成功
        await self.send_personal_message(device_id, {
            "type": "subscribed",
            "channel": channel,
            "timestamp": datetime.now().isoformat()
        })
    
    async def unsubscribe_from_channel(self, device_id: str, channel: str):
        """取消订阅频道"""
        if device_id in self.subscriptions:
            self.subscriptions[device_id].discard(channel)
            logger.info(f"Device {device_id} unsubscribed from channel {channel}")
            
            # 通知取消订阅成功
            await self.send_personal_message(device_id, {
                "type": "unsubscribed", 
                "channel": channel,
                "timestamp": datetime.now().isoformat()
            })
    
    async def handle_message(self, device_id: str, message: dict):
        """处理来自客户端的消息"""
        message_type = message.get("type")
        
        if message_type == "ping":
            # 心跳消息
            self.last_heartbeat[device_id] = datetime.now()
            await self.send_personal_message(device_id, {"type": "pong"})
            
        elif message_type == "subscribe":
            # 订阅频道
            channel = message.get("channel")
            if channel:
                await self.subscribe_to_channel(device_id, channel)
                
        elif message_type == "unsubscribe":
            # 取消订阅
            channel = message.get("channel")
            if channel:
                await self.unsubscribe_from_channel(device_id, channel)
        
        else:
            # 其他消息类型交给上层处理
            return message
    
    async def _check_heartbeats(self):
        """检查心跳，清理超时连接"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                now = datetime.now()
                timeout_devices = []
                
                for device_id, last_heartbeat in self.last_heartbeat.items():
                    # 超过60秒没有心跳，认为断开
                    if (now - last_heartbeat).total_seconds() > 60:
                        timeout_devices.append(device_id)
                
                for device_id in timeout_devices:
                    logger.warning(f"Device {device_id} heartbeat timeout")
                    await self.disconnect(device_id)
                    
            except Exception as e:
                logger.error(f"Heartbeat check error: {e}")
    
    def get_online_devices(self) -> List[str]:
        """获取在线设备列表"""
        return list(self.active_connections.keys())
    
    def is_device_online(self, device_id: str) -> bool:
        """检查设备是否在线"""
        return device_id in self.active_connections


# 全局实例
ws_manager = ConnectionManager()
