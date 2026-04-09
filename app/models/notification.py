"""站内通知模型"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
import enum


class NotificationType(str, enum.Enum):
    """通知类型枚举"""
    SECURITY_REJECTED = "security_rejected"  # 安全驳回
    LEGAL_REJECTED = "legal_rejected"  # 法务驳回（要求修改）
    LEGAL_DENIED = "legal_denied"  # 法务拒绝
    URGENCY_ADDED = "urgency_added"  # 被催促
    LEGAL_APPROVED = "legal_approved"  # 法务审批通过
    SECURITY_APPROVED = "security_approved"  # 安全审批通过


class Notification(Base):
    """站内通知模型"""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, comment="通知标题")
    message = Column(Text, nullable=False, comment="通知内容")
    type = Column(SQLEnum(NotificationType), nullable=False, comment="通知类型")
    related_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=True, comment="关联的合规记录 ID")
    is_read = Column(Boolean, default=False, comment="是否已读")

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    record = relationship("ComplianceRecord", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type})>"
