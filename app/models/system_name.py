"""
系统名称管理 Model
"""

from sqlalchemy import Column, Integer, String, UniqueConstraint

from app.database import Base


class SystemName(Base):
    """系统名称表 - 用于存储可用的系统名称列表"""
    __tablename__ = "system_names"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)

    __table_args__ = (
        UniqueConstraint('name', name='uq_system_name'),
    )
