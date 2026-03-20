"""
Pydantic Schemas 模块

用于 API 请求/响应验证
"""

from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserInDB
from app.schemas.component import (
    ComponentCreate,
    ComponentUpdate,
    ComponentResponse,
    ComponentMatchResponse,
    BlackDuckReportUpload,
)
from app.schemas.compliance_record import (
    ComplianceRecordCreate,
    ComplianceRecordUpdate,
    ComplianceRecordResponse,
    ComplianceRecordSubmit,
    ComplianceRecordApprove,
    ComplianceRecordReject,
    RecordStatusEnum,
)
from app.schemas.approval import (
    ApprovalHistoryResponse,
    ApprovalActionEnum,
)
from app.schemas.dashboard import DashboardTodoResponse, DashboardStatsResponse
from app.schemas.auth import Token, TokenPayload, EmailLoginRequest

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Component
    "ComponentCreate",
    "ComponentUpdate",
    "ComponentResponse",
    "ComponentMatchResponse",
    "BlackDuckReportUpload",
    # Compliance Record
    "ComplianceRecordCreate",
    "ComplianceRecordUpdate",
    "ComplianceRecordResponse",
    "ComplianceRecordSubmit",
    "ComplianceRecordApprove",
    "ComplianceRecordReject",
    "RecordStatusEnum",
    # Approval
    "ApprovalHistoryResponse",
    "ApprovalActionEnum",
    # Dashboard
    "DashboardTodoResponse",
    "DashboardStatsResponse",
    # Auth
    "Token",
    "TokenPayload",
    "EmailLoginRequest",
]
