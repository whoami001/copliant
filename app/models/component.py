"""组件模型"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Component(Base):
    """组件模型"""

    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(255), nullable=False)
    license = Column(String(100))
    copyright = Column(Text)
    usage_type = Column(String(50))  # 'direct' or 'transitive'
    license_risk_level = Column(String(20), default="unknown")  # safe/caution/warning/unknown
    black_duck_report_id = Column(String(100))
    is_approved = Column(Boolean, default=False)

    created_by = Column(Integer, ForeignKey("users.id"))
    updated_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 唯一约束：name + version
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_component_name_version"),
    )

    # 关联关系
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_components")
    updater = relationship("User", foreign_keys=[updated_by], back_populates="updated_components")
    compliance_records = relationship("ComplianceRecord", back_populates="component")

    def __repr__(self) -> str:
        return f"<Component(name={self.name}, version={self.version})>"

    @property
    def full_name(self) -> str:
        """返回完整的组件名称"""
        return f"{self.name}@{self.version}"
