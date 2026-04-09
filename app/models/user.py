"""用户模型"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
import enum


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ENGINEER = "engineer"
    SECURITY = "security"
    LEGAL = "legal"
    ADMIN = "admin"


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100))
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.ENGINEER)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    created_components = relationship("Component", foreign_keys="Component.created_by", back_populates="creator")
    updated_components = relationship("Component", foreign_keys="Component.updated_by", back_populates="updater")
    filled_records = relationship("ComplianceRecord", foreign_keys="ComplianceRecord.filled_by", back_populates="filler")
    reviewed_records = relationship("ComplianceRecord", foreign_keys="ComplianceRecord.reviewed_by_security", back_populates="security_reviewer")
    approved_records = relationship("ComplianceRecord", foreign_keys="ComplianceRecord.approved_by_legal", back_populates="legal_approver")
    approval_actions = relationship("ApprovalHistory", foreign_keys="ApprovalHistory.actor", back_populates="actor_rel")
    urgencies = relationship("Urgency", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
