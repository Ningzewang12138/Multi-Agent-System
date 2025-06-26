"""
P2P聊天消息服务
处理设备间的聊天消息路由和存储
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
import aiofiles
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """聊天消息数据模型"""
    id: str
    from_device_id: str
    to_device_id: str
    content: str
    message_type: str  # 'text', 'image', 'file'
    timestamp: datetime
    status: str  # 'sent', 'delivered', 'read'
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass 
class ChatSession:
    """聊天会话"""
    session_id: str
    device1_id: str
    device2_id: str
    created_at: datetime
    last_message_at: Optional[datetime] = None
    unread_count: Dict[str, int] = None  # {device_id: count}
    
    def __post_init__(self):
        if self.unread_count is None:
            self.unread_count = {
                self.device1_id: 0,
                self.device2_id: 0
            }
    
    def to_dict(self):
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.last_message_at:
            data['last_message_at'] = self.last_message_at.isoformat()
        return data


class P2PChatService:
    """P2P聊天服务"""
    
    def __init__(self, storage_path: str = "data/chat"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 内存中的会话和消息缓存
        self.sessions: Dict[str, ChatSession] = {}
        self.messages: Dict[str, List[ChatMessage]] = {}  # session_id -> messages
        self.online_devices: Set[str] = set()
        
        # WebSocket连接管理
        self.device_connections: Dict[str, Any] = {}  # device_id -> websocket
        
        # 消息队列（用于离线消息）
        self.offline_queue: Dict[str, List[ChatMessage]] = {}  # device_id -> messages
        
        # 标记是否已加载数据
        self._data_loaded = False
    
    async def _ensure_data_loaded(self):
        """确保数据已加载"""
        if not self._data_loaded:
            await self._load_data()
            self._data_loaded = True
    
    async def _load_data(self):
        """从存储加载历史数据"""
        try:
            # 加载会话
            sessions_file = self.storage_path / "sessions.json"
            if sessions_file.exists():
                async with aiofiles.open(sessions_file, 'r') as f:
                    data = json.loads(await f.read())
                    for session_data in data:
                        session = ChatSession(
                            session_id=session_data['session_id'],
                            device1_id=session_data['device1_id'],
                            device2_id=session_data['device2_id'],
                            created_at=datetime.fromisoformat(session_data['created_at']),
                            last_message_at=datetime.fromisoformat(session_data['last_message_at']) 
                                if session_data.get('last_message_at') else None,
                            unread_count=session_data.get('unread_count', {})
                        )
                        self.sessions[session.session_id] = session
            
            # 加载最近的消息（最近100条每个会话）
            for session_id in self.sessions:
                messages_file = self.storage_path / f"messages_{session_id}.json"
                if messages_file.exists():
                    async with aiofiles.open(messages_file, 'r') as f:
                        data = json.loads(await f.read())
                        messages = [ChatMessage.from_dict(msg) for msg in data[-100:]]
                        self.messages[session_id] = messages
                        
        except Exception as e:
            logger.error(f"Failed to load chat data: {e}")
    
    async def register_device_connection(self, device_id: str, websocket: Any):
        """注册设备WebSocket连接"""
        await self._ensure_data_loaded()
        self.device_connections[device_id] = websocket
        self.online_devices.add(device_id)
        
        # 发送离线消息
        if device_id in self.offline_queue:
            for message in self.offline_queue[device_id]:
                await self._send_to_device(device_id, {
                    'type': 'message',
                    'message': message.to_dict()
                })
            del self.offline_queue[device_id]
        
        logger.info(f"Device {device_id} connected for chat")
    
    async def unregister_device_connection(self, device_id: str):
        """注销设备连接"""
        if device_id in self.device_connections:
            del self.device_connections[device_id]
        self.online_devices.discard(device_id)
        logger.info(f"Device {device_id} disconnected from chat")
    
    async def get_or_create_session(self, device1_id: str, device2_id: str) -> ChatSession:
        """获取或创建会话"""
        await self._ensure_data_loaded()
        # 确保设备ID顺序一致
        if device1_id > device2_id:
            device1_id, device2_id = device2_id, device1_id
        
        # 查找现有会话
        for session in self.sessions.values():
            if (session.device1_id == device1_id and session.device2_id == device2_id):
                return session
        
        # 创建新会话
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            device1_id=device1_id,
            device2_id=device2_id,
            created_at=datetime.now()
        )
        self.sessions[session_id] = session
        self.messages[session_id] = []
        
        # 保存会话
        asyncio.create_task(self._save_sessions())
        
        return session
    
    async def send_message(
        self, 
        from_device_id: str, 
        to_device_id: str,
        content: str,
        message_type: str = 'text',
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """发送消息"""
        # 获取或创建会话
        session = await self.get_or_create_session(from_device_id, to_device_id)
        
        # 创建消息
        message = ChatMessage(
            id=str(uuid.uuid4()),
            from_device_id=from_device_id,
            to_device_id=to_device_id,
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            status='sent',
            metadata=metadata
        )
        
        # 保存消息
        if session.session_id not in self.messages:
            self.messages[session.session_id] = []
        self.messages[session.session_id].append(message)
        
        # 更新会话
        session.last_message_at = message.timestamp
        session.unread_count[to_device_id] = session.unread_count.get(to_device_id, 0) + 1
        
        # 发送给接收方
        if to_device_id in self.online_devices:
            await self._send_to_device(to_device_id, {
                'type': 'message',
                'message': message.to_dict(),
                'session_id': session.session_id
            })
            message.status = 'delivered'
        else:
            # 加入离线队列
            if to_device_id not in self.offline_queue:
                self.offline_queue[to_device_id] = []
            self.offline_queue[to_device_id].append(message)
        
        # 发送确认给发送方
        await self._send_to_device(from_device_id, {
            'type': 'message_sent',
            'message_id': message.id,
            'status': message.status,
            'session_id': session.session_id
        })
        
        # 异步保存
        asyncio.create_task(self._save_messages(session.session_id))
        asyncio.create_task(self._save_sessions())
        
        return message
    
    async def get_messages(
        self, 
        device_id: str, 
        session_id: str,
        limit: int = 50,
        before_id: Optional[str] = None
    ) -> List[ChatMessage]:
        """获取会话消息"""
        await self._ensure_data_loaded()
        # 验证设备权限
        session = self.sessions.get(session_id)
        if not session or device_id not in [session.device1_id, session.device2_id]:
            raise ValueError("Unauthorized access to session")
        
        messages = self.messages.get(session_id, [])
        
        # 如果指定了before_id，找到该消息的位置
        if before_id:
            for i, msg in enumerate(messages):
                if msg.id == before_id:
                    messages = messages[:i]
                    break
        
        # 返回最近的消息
        return messages[-limit:]
    
    async def mark_messages_read(
        self,
        device_id: str,
        session_id: str,
        message_ids: List[str]
    ):
        """标记消息已读"""
        await self._ensure_data_loaded()
        session = self.sessions.get(session_id)
        if not session or device_id not in [session.device1_id, session.device2_id]:
            raise ValueError("Unauthorized access to session")
        
        # 更新消息状态
        messages = self.messages.get(session_id, [])
        other_device_id = session.device1_id if device_id == session.device2_id else session.device2_id
        
        for message in messages:
            if message.id in message_ids and message.to_device_id == device_id:
                message.status = 'read'
                
                # 通知发送方
                await self._send_to_device(message.from_device_id, {
                    'type': 'message_read',
                    'message_id': message.id,
                    'read_by': device_id,
                    'session_id': session_id
                })
        
        # 重置未读计数
        session.unread_count[device_id] = 0
        
        # 异步保存
        asyncio.create_task(self._save_messages(session_id))
        asyncio.create_task(self._save_sessions())
    
    async def get_chat_sessions(self, device_id: str) -> List[Dict[str, Any]]:
        """获取设备的所有聊天会话"""
        await self._ensure_data_loaded()
        result = []
        
        for session in self.sessions.values():
            if device_id in [session.device1_id, session.device2_id]:
                # 获取对方设备ID
                other_device_id = (
                    session.device1_id 
                    if device_id == session.device2_id 
                    else session.device2_id
                )
                
                # 获取最后一条消息
                last_message = None
                messages = self.messages.get(session.session_id, [])
                if messages:
                    last_message = messages[-1].to_dict()
                
                result.append({
                    'session_id': session.session_id,
                    'other_device_id': other_device_id,
                    'created_at': session.created_at.isoformat(),
                    'last_message_at': session.last_message_at.isoformat() 
                        if session.last_message_at else None,
                    'unread_count': session.unread_count.get(device_id, 0),
                    'last_message': last_message,
                    'is_online': other_device_id in self.online_devices
                })
        
        # 按最后消息时间排序
        result.sort(
            key=lambda x: x['last_message_at'] or x['created_at'], 
            reverse=True
        )
        
        return result
    
    async def _send_to_device(self, device_id: str, data: dict):
        """发送数据到设备"""
        if device_id in self.device_connections:
            websocket = self.device_connections[device_id]
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to device {device_id}: {e}")
                await self.unregister_device_connection(device_id)
    
    async def _save_sessions(self):
        """保存会话数据"""
        try:
            sessions_data = [session.to_dict() for session in self.sessions.values()]
            sessions_file = self.storage_path / "sessions.json"
            
            async with aiofiles.open(sessions_file, 'w') as f:
                await f.write(json.dumps(sessions_data, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    async def _save_messages(self, session_id: str):
        """保存消息数据"""
        try:
            messages = self.messages.get(session_id, [])
            if not messages:
                return
            
            messages_data = [msg.to_dict() for msg in messages]
            messages_file = self.storage_path / f"messages_{session_id}.json"
            
            async with aiofiles.open(messages_file, 'w') as f:
                await f.write(json.dumps(messages_data, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save messages for session {session_id}: {e}")
    
    async def broadcast_typing_status(
        self,
        device_id: str,
        session_id: str,
        is_typing: bool
    ):
        """广播输入状态"""
        await self._ensure_data_loaded()
        session = self.sessions.get(session_id)
        if not session or device_id not in [session.device1_id, session.device2_id]:
            return
        
        # 找到对方设备
        other_device_id = (
            session.device1_id 
            if device_id == session.device2_id 
            else session.device2_id
        )
        
        # 发送输入状态
        await self._send_to_device(other_device_id, {
            'type': 'typing_status',
            'session_id': session_id,
            'device_id': device_id,
            'is_typing': is_typing
        })


# 全局实例
p2p_chat_service = P2PChatService()
