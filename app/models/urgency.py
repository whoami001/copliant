"""催促记录模型"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
import enum


class UrgencyTarget(str, enum.Enum):
    """催促目标"""
    SECURITY = "security"
    LEGAL = "legal"


class Urgency(Base):
    """催促记录模型"""

    __tablename__ = "urgencies"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False)
    urged_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_role = Column(SQLEnum(UrgencyTarget), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    record = relationship("ComplianceRecord", back_populates="urgencies")
    user = relationship("User", back_populates="urgencies")
