"""
消息模型定义
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"      # 待发送
    SENT = "sent"           # 已发送
    DELIVERED = "delivered"  # 已送达
    READ = "read"           # 已读
    FAILED = "failed"       # 发送失败


class Message(BaseModel):
    """消息模型"""
    id: str = Field(..., description="消息ID")
    sender_id: str = Field(..., description="发送者设备ID")
    sender_name: str = Field(..., description="发送者设备名称")
    recipient_id: str = Field(..., description="接收者设备ID")
    recipient_name: str = Field(..., description="接收者设备名称")
    content: str = Field(..., description="消息内容")
    type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="消息状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    delivered_at: Optional[datetime] = Field(None, description="送达时间")
    read_at: Optional[datetime] = Field(None, description="已读时间")
    metadata: dict = Field(default_factory=dict, description="额外元数据")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatSession(BaseModel):
    """聊天会话模型"""
    id: str = Field(..., description="会话ID")
    participant_ids: List[str] = Field(..., description="参与者设备ID列表")
    participant_names: List[str] = Field(..., description="参与者设备名称列表")
    last_message: Optional[Message] = Field(None, description="最后一条消息")
    last_activity: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    unread_count: dict = Field(default_factory=dict, description="各设备的未读消息数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    recipient_id: str = Field(..., description="接收者设备ID")
    content: str = Field(..., description="消息内容")
    type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    metadata: dict = Field(default_factory=dict, description="额外元数据")


class MessageListRequest(BaseModel):
    """获取消息列表请求"""
    session_id: Optional[str] = Field(None, description="会话ID")
    device_id: Optional[str] = Field(None, description="对方设备ID")
    limit: int = Field(default=50, ge=1, le=200, description="返回消息数量")
    before_id: Optional[str] = Field(None, description="获取此ID之前的消息")
    after_id: Optional[str] = Field(None, description="获取此ID之后的消息")


class UpdateMessageStatusRequest(BaseModel):
    """更新消息状态请求"""
    message_ids: List[str] = Field(..., description="消息ID列表")
    status: MessageStatus = Field(..., description="新状态")
