"""合规记录模型"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship

from app.database import Base
import enum


class RecordStatus(str, enum.Enum):
    """合规记录状态枚举"""
    DRAFT = "draft"  # 草稿/待填写
    PENDING_SECURITY = "pending_security"  # 待安全校验
    PENDING_LEGAL = "pending_legal"  # 待法务审批
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已驳回


class ComplianceRecord(Base):
    """合规记录模型"""

    __tablename__ = "compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    system_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(RecordStatus), nullable=False, default=RecordStatus.DRAFT)

    # 审批相关人员
    filled_by = Column(Integer, ForeignKey("users.id"))
    submitted_at = Column(DateTime, nullable=True)
    reviewed_by_security = Column(Integer, ForeignKey("users.id"), nullable=True)
    security_reviewed_at = Column(DateTime, nullable=True)
    approved_by_legal = Column(Integer, ForeignKey("users.id"), nullable=True)
    legal_approved_at = Column(DateTime, nullable=True)

    comments = Column(Text)

    # 驳回/要求补充信息字段
    rejection_reason = Column(Text, nullable=True, comment="驳回/要求补充的原因")
    required_fields = Column(JSON, nullable=True, comment="审批人要求补充的字段列表")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    component = relationship("Component", back_populates="compliance_records")
    filler = relationship("User", foreign_keys=[filled_by], back_populates="filled_records")
    security_reviewer = relationship("User", foreign_keys=[reviewed_by_security], back_populates="reviewed_records")
    legal_approver = relationship("User", foreign_keys=[approved_by_legal], back_populates="approved_records")
    approval_history = relationship("ApprovalHistory", back_populates="record", cascade="all, delete-orphan")
    legal_declaration = relationship(
        "LegalDeclaration",
        back_populates="compliance_record",
        uselist=False,
        cascade="all, delete-orphan"
    )
    urgencies = relationship("Urgency", back_populates="record")
    notifications = relationship("Notification", back_populates="record")

    def __repr__(self) -> str:
        return f"<ComplianceRecord(id={self.id}, component_id={self.component_id}, status={self.status})>"
