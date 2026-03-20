"""合规记录相关 Schema"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
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
    comments: str  # 驳回必须填写原因


class ComponentRef(BaseModel):
    """组件引用（简化版）"""
    id: int
    name: str
    version: str

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

    model_config = ConfigDict(from_attributes=True)
