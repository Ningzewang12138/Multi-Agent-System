"""
消息存储服务
负责消息的持久化存储和查询
"""
import json
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import logging
import threading
from contextlib import contextmanager

from server.models.message import Message, ChatSession, MessageStatus, MessageType

logger = logging.getLogger(__name__)


class MessageStorageService:
    """消息存储服务"""
    
    def __init__(self, db_path: str = "messages.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with self._get_connection() as conn:
            # 创建消息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender_id TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    recipient_id TEXT NOT NULL,
                    recipient_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT,
                    read_at TEXT,
                    metadata TEXT,
                    FOREIGN KEY (sender_id, recipient_id) REFERENCES sessions(device1_id, device2_id)
                )
            """)
            
            # 创建会话表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    device1_id TEXT NOT NULL,
                    device1_name TEXT NOT NULL,
                    device2_id TEXT NOT NULL,
                    device2_name TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(device1_id, device2_id)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_devices ON sessions(device1_id, device2_id)")
            
            conn.commit()
            
        logger.info(f"Message database initialized at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def create_or_get_session(self, device1_id: str, device1_name: str, 
                            device2_id: str, device2_name: str) -> str:
        """创建或获取会话"""
        # 确保设备ID顺序一致
        if device1_id > device2_id:
            device1_id, device2_id = device2_id, device1_id
            device1_name, device2_name = device2_name, device1_name
        
        session_id = f"{device1_id}_{device2_id}"
        
        with self._lock:
            with self._get_connection() as conn:
                # 尝试获取现有会话
                cursor = conn.execute(
                    "SELECT id FROM sessions WHERE device1_id = ? AND device2_id = ?",
                    (device1_id, device2_id)
                )
                row = cursor.fetchone()
                
                if row:
                    # 更新最后活动时间
                    conn.execute(
                        "UPDATE sessions SET last_activity = ? WHERE id = ?",
                        (datetime.now().isoformat(), row['id'])
                    )
                    conn.commit()
                    return row['id']
                
                # 创建新会话
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO sessions (id, device1_id, device1_name, device2_id, 
                                        device2_name, last_activity, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, device1_id, device1_name, device2_id, 
                     device2_name, now, now))
                conn.commit()
                
                logger.info(f"Created new session: {session_id}")
                return session_id
    
    def save_message(self, message: Message) -> bool:
        """保存消息"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO messages (id, sender_id, sender_name, recipient_id, 
                                            recipient_name, content, type, status, 
                                            created_at, delivered_at, read_at, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        message.id,
                        message.sender_id,
                        message.sender_name,
                        message.recipient_id,
                        message.recipient_name,
                        message.content,
                        message.type.value,
                        message.status.value,
                        message.created_at.isoformat(),
                        message.delivered_at.isoformat() if message.delivered_at else None,
                        message.read_at.isoformat() if message.read_at else None,
                        json.dumps(message.metadata)
                    ))
                    
                    # 更新会话的最后活动时间
                    session_id = self.create_or_get_session(
                        message.sender_id, message.sender_name,
                        message.recipient_id, message.recipient_name
                    )
                    
                    conn.execute(
                        "UPDATE sessions SET last_activity = ? WHERE id = ?",
                        (message.created_at.isoformat(), session_id)
                    )
                    
                    conn.commit()
                    logger.debug(f"Message {message.id} saved successfully")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to save message: {e}")
                return False
    
    def get_messages(self, session_id: Optional[str] = None, 
                    device1_id: Optional[str] = None,
                    device2_id: Optional[str] = None,
                    limit: int = 50,
                    before_id: Optional[str] = None,
                    after_id: Optional[str] = None) -> List[Message]:
        """获取消息列表"""
        with self._get_connection() as conn:
            query = "SELECT * FROM messages WHERE 1=1"
            params = []
            
            # 根据会话ID或设备ID过滤
            if session_id:
                # 从会话ID解析设备ID
                parts = session_id.split('_')
                if len(parts) == 2:
                    query += " AND ((sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?))"
                    params.extend([parts[0], parts[1], parts[1], parts[0]])
            elif device1_id and device2_id:
                query += " AND ((sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?))"
                params.extend([device1_id, device2_id, device2_id, device1_id])
            
            # 分页过滤
            if before_id:
                query += " AND id < ?"
                params.append(before_id)
            elif after_id:
                query += " AND id > ?"
                params.append(after_id)
            
            # 排序和限制
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            messages = []
            
            for row in cursor:
                message = Message(
                    id=row['id'],
                    sender_id=row['sender_id'],
                    sender_name=row['sender_name'],
                    recipient_id=row['recipient_id'],
                    recipient_name=row['recipient_name'],
                    content=row['content'],
                    type=MessageType(row['type']),
                    status=MessageStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    delivered_at=datetime.fromisoformat(row['delivered_at']) if row['delivered_at'] else None,
                    read_at=datetime.fromisoformat(row['read_at']) if row['read_at'] else None,
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                messages.append(message)
            
            # 返回时反转顺序（最新的在后面）
            return list(reversed(messages))
    
    def update_message_status(self, message_ids: List[str], status: MessageStatus) -> int:
        """更新消息状态"""
        with self._lock:
            with self._get_connection() as conn:
                now = datetime.now().isoformat()
                updated_count = 0
                
                for message_id in message_ids:
                    cursor = conn.cursor()
                    
                    # 根据状态更新相应的时间戳
                    if status == MessageStatus.DELIVERED:
                        cursor.execute(
                            "UPDATE messages SET status = ?, delivered_at = ? WHERE id = ?",
                            (status.value, now, message_id)
                        )
                    elif status == MessageStatus.READ:
                        cursor.execute(
                            "UPDATE messages SET status = ?, read_at = ? WHERE id = ?",
                            (status.value, now, message_id)
                        )
                    else:
                        cursor.execute(
                            "UPDATE messages SET status = ? WHERE id = ?",
                            (status.value, message_id)
                        )
                    
                    updated_count += cursor.rowcount
                
                conn.commit()
                logger.debug(f"Updated {updated_count} messages to status {status.value}")
                return updated_count
    
    def get_sessions(self, device_id: str) -> List[ChatSession]:
        """获取设备的所有会话"""
        with self._get_connection() as conn:
            # 查询包含该设备的所有会话
            cursor = conn.execute("""
                SELECT s.*, 
                       (SELECT COUNT(*) FROM messages m 
                        WHERE ((m.sender_id = s.device1_id AND m.recipient_id = s.device2_id) 
                            OR (m.sender_id = s.device2_id AND m.recipient_id = s.device1_id))
                          AND m.recipient_id = ? AND m.status != 'read') as unread_count
                FROM sessions s
                WHERE s.device1_id = ? OR s.device2_id = ?
                ORDER BY s.last_activity DESC
            """, (device_id, device_id, device_id))
            
            sessions = []
            for row in cursor:
                # 确定对方设备
                if row['device1_id'] == device_id:
                    other_device_id = row['device2_id']
                    other_device_name = row['device2_name']
                else:
                    other_device_id = row['device1_id']
                    other_device_name = row['device1_name']
                
                # 获取最后一条消息
                last_msg_cursor = conn.execute("""
                    SELECT * FROM messages 
                    WHERE (sender_id = ? AND recipient_id = ?) 
                       OR (sender_id = ? AND recipient_id = ?)
                    ORDER BY created_at DESC LIMIT 1
                """, (row['device1_id'], row['device2_id'], 
                     row['device2_id'], row['device1_id']))
                
                last_msg_row = last_msg_cursor.fetchone()
                last_message = None
                
                if last_msg_row:
                    last_message = Message(
                        id=last_msg_row['id'],
                        sender_id=last_msg_row['sender_id'],
                        sender_name=last_msg_row['sender_name'],
                        recipient_id=last_msg_row['recipient_id'],
                        recipient_name=last_msg_row['recipient_name'],
                        content=last_msg_row['content'],
                        type=MessageType(last_msg_row['type']),
                        status=MessageStatus(last_msg_row['status']),
                        created_at=datetime.fromisoformat(last_msg_row['created_at']),
                        delivered_at=datetime.fromisoformat(last_msg_row['delivered_at']) if last_msg_row['delivered_at'] else None,
                        read_at=datetime.fromisoformat(last_msg_row['read_at']) if last_msg_row['read_at'] else None,
                        metadata=json.loads(last_msg_row['metadata']) if last_msg_row['metadata'] else {}
                    )
                
                session = ChatSession(
                    id=row['id'],
                    participant_ids=[row['device1_id'], row['device2_id']],
                    participant_names=[row['device1_name'], row['device2_name']],
                    last_message=last_message,
                    last_activity=datetime.fromisoformat(row['last_activity']),
                    unread_count={device_id: row['unread_count']},
                    created_at=datetime.fromisoformat(row['created_at'])
                )
                sessions.append(session)
            
            return sessions
    
    def get_unread_count(self, device_id: str) -> Dict[str, int]:
        """获取设备的未读消息统计"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT sender_id, COUNT(*) as count
                FROM messages
                WHERE recipient_id = ? AND status != 'read'
                GROUP BY sender_id
            """, (device_id,))
            
            unread_counts = {}
            for row in cursor:
                unread_counts[row['sender_id']] = row['count']
            
            return unread_counts
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话及其所有消息"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    # 从会话ID解析设备ID
                    parts = session_id.split('_')
                    if len(parts) != 2:
                        return False
                    
                    # 删除消息
                    conn.execute("""
                        DELETE FROM messages 
                        WHERE (sender_id = ? AND recipient_id = ?) 
                           OR (sender_id = ? AND recipient_id = ?)
                    """, (parts[0], parts[1], parts[1], parts[0]))
                    
                    # 删除会话
                    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                    
                    conn.commit()
                    logger.info(f"Deleted session {session_id}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to delete session: {e}")
                return False


# 全局实例
message_storage = MessageStorageService()
