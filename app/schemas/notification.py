"""通知相关 Schema"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
import enum

from app.models.notification import NotificationType


class NotificationTypeSchema(str, enum.Enum):
    """通知类型"""
    SECURITY_REJECTED = "security_rejected"
    LEGAL_REJECTED = "legal_rejected"
    LEGAL_DENIED = "legal_denied"
    URGENCY_ADDED = "urgency_added"


class NotificationBase(BaseModel):
    """通知基础 Schema"""
    title: str
    message: str
    type: NotificationTypeSchema


class NotificationCreate(NotificationBase):
    """创建通知请求"""
    user_id: int
    related_record_id: Optional[int] = None


class NotificationResponse(NotificationBase):
    """通知响应"""
    id: int
    user_id: int
    type: NotificationTypeSchema
    related_record_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    items: list[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """未读通知数响应"""
    unread_count: int


class MarkAsReadResponse(BaseModel):
    """标记已读响应"""
    success: bool
