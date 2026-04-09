"""审批历史相关 Schema"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
import enum


class ApprovalActionEnum(str, enum.Enum):
    """审批操作类型"""
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class ApprovalHistoryResponse(BaseModel):
    """审批历史响应"""
    id: int
    record_id: int
    action: ApprovalActionEnum
    role: str
    actor_name: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    comments: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
