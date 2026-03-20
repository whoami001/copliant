"""审批历史模型"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship

from app.database import Base


class ApprovalHistory(Base):
    """审批历史模型"""

    __tablename__ = "approval_history"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False)

    action = Column(String(30), nullable=False)  # submit/approve/reject/request_changes
    actor = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)  # engineer/security/legal

    previous_status = Column(String(30))
    new_status = Column(String(30))
    comments = Column(Text)

    ip_address = Column(INET)
    user_agent = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关联关系
    record = relationship("ComplianceRecord", back_populates="approval_history")
    actor_rel = relationship("User", foreign_keys=[actor], back_populates="approval_actions")

    def __repr__(self) -> str:
        return f"<ApprovalHistory(record_id={self.record_id}, action={self.action})>"
