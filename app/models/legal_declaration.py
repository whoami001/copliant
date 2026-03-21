"""法务声明模型"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.compliance_record import ComplianceRecord


class UsageType(str, PyEnum):
    """使用方式枚举"""
    STANDALONE = "standalone"  # 独立可执行程序
    DYNAMICALLY_LINKED = "dynamically_linked"  # 动态链接库（Python/Perl/Ruby/Java 等）
    STATICALLY_LINKED = "statically_linked"  # 静态链接库（C/C++ 等）
    BROWSER_CODE = "browser_code"  # 浏览器代码（HTML/CSS/JS）
    OTHER = "other"  # 其他


class IsModified(str, PyEnum):
    """是否修改枚举"""
    YES = "yes"
    NO = "no"


class LegalDeclaration(Base):
    """法务声明模型 - 1:1 关联 ComplianceRecord"""

    __tablename__ = "legal_declarations"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(
        Integer,
        ForeignKey("compliance_records.id"),
        nullable=False,
        unique=True,
        index=True,
        comment="关联合规记录 ID"
    )

    # 表单字段
    purpose_of_use = Column(String(500), nullable=False, comment="使用目的")
    url_to_source = Column(String(500), nullable=False, comment="源代码下载位置")
    license_info_url = Column(String(500), nullable=False, comment="许可证说明页面")
    license_text_url = Column(String(500), nullable=False, comment="许可证全文 URL")
    license_name = Column(String(100), nullable=False, comment="SPDX 许可证 ID")

    # 枚举字段（使用 String 类型，数据库层面有 ENUM 约束）
    is_modified = Column(
        String(10),
        nullable=False,
        default="no",
        comment="是否修改"
    )
    usage_type = Column(
        String(50),
        nullable=False,
        comment="使用方式"
    )

    # 时间戳
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="提交时间")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )

    # 1:1 关系
    compliance_record = relationship(
        "ComplianceRecord",
        back_populates="legal_declaration",
        uselist=False
    )

    # 数据库约束：确保枚举字段值有效
    __table_args__ = (
        CheckConstraint(
            "is_modified IN ('yes', 'no')",
            name="check_is_modified_valid"
        ),
        CheckConstraint(
            "usage_type IN ('standalone', 'dynamically_linked', 'statically_linked', 'browser_code', 'other')",
            name="check_usage_type_valid"
        ),
    )

    def __repr__(self) -> str:
        return f"<LegalDeclaration(id={self.id}, compliance_record_id={self.compliance_record_id}, license_name={self.license_name})>"
