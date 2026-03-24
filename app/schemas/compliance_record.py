"""合规记录相关 Schema"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
import enum


class RecordStatusEnum(str, enum.Enum):
    """合规记录状态"""
    DRAFT = "draft"
    PENDING_SECURITY = "pending_security"
    PENDING_LEGAL = "pending_legal"
    APPROVED = "approved"
    REJECTED = "rejected"


class ComplianceRecordBase(BaseModel):
    """合规记录基础 Schema"""
    system_name: str
    comments: Optional[str] = None


class ComplianceRecordCreate(ComplianceRecordBase):
    """创建合规记录请求"""
    component_id: int


class ComplianceRecordUpdate(BaseModel):
    """更新合规记录请求"""
    comments: Optional[str] = None


class ComplianceRecordSubmit(BaseModel):
    """提交审批请求"""
    pass


class ComplianceRecordApprove(BaseModel):
    """审批通过请求"""
    comments: Optional[str] = None


class ComplianceRecordReject(BaseModel):
    """审批驳回请求"""
    comments: Optional[str] = None  # 驳回原因 (向后兼容)
    rejection_reason: Optional[str] = None  # 要求补充的原因
    required_fields: Optional[list] = None  # 需要补充的字段列表

    def get_rejection_reason(self) -> Optional[str]:
        """获取驳回原因，优先使用 rejection_reason，否则使用 comments"""
        return self.rejection_reason or self.comments


class ComponentRef(BaseModel):
    """组件引用（简化版）"""
    id: int
    name: str
    version: str
    license: Optional[str] = None
    license_risk_level: Optional[str] = None
    is_approved: bool = False

    model_config = ConfigDict(from_attributes=True)


class ComplianceRecordResponse(ComplianceRecordBase):
    """合规记录响应"""
    id: int
    component_id: int
    component: Optional[ComponentRef] = None
    status: RecordStatusEnum
    filled_by: Optional[int] = None
    submitted_at: Optional[datetime] = None
    reviewed_by_security: Optional[int] = None
    security_reviewed_at: Optional[datetime] = None
    approved_by_legal: Optional[int] = None
    legal_approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    declaration: Optional["DeclarationRef"] = Field(None, alias="legal_declaration")
    rejection_reason: Optional[str] = None
    required_fields: Optional[list] = None  # JSON array of field names

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DeclarationRef(BaseModel):
    """法务声明引用"""
    id: int
    compliance_record_id: int
    purpose_of_use: Optional[str] = None
    url_to_source: Optional[str] = None
    license_info_url: Optional[str] = None
    license_text_url: Optional[str] = None
    license_name: Optional[str] = None
    is_modified: Optional[str] = None
    usage_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# 解决循环引用
ComplianceRecordResponse.model_rebuild()
