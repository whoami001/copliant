"""法务声明相关 Schema"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
import enum


class UsageTypeEnum(str, enum.Enum):
    """使用方式枚举"""
    STANDALONE = "standalone"  # 独立可执行程序
    DYNAMICALLY_LINKED = "dynamically_linked"  # 动态链接库（Python/Perl/Ruby/Java 等）
    STATICALLY_LINKED = "statically_linked"  # 静态链接库（C/C++ 等）
    BROWSER_CODE = "browser_code"  # 浏览器代码（HTML/CSS/JS）
    OTHER = "other"  # 其他


class IsModifiedEnum(str, enum.Enum):
    """是否修改枚举"""
    YES = "yes"
    NO = "no"


class LegalDeclarationBase(BaseModel):
    """法务声明基础 Schema"""
    purpose_of_use: str = Field(
        ...,
        max_length=500,
        description="使用目的（简述 OSS 组件实现的功能）"
    )
    url_to_source: str = Field(
        ...,
        max_length=500,
        description="源代码下载位置"
    )
    license_info_url: str = Field(
        ...,
        max_length=500,
        description="许可证和例外条款说明页面"
    )
    license_text_url: str = Field(
        ...,
        max_length=500,
        description="许可证全文 URL"
    )
    license_name: str = Field(
        ...,
        max_length=100,
        description="SPDX 许可证 ID（如 GPL-2.0-only）"
    )
    is_modified: IsModifiedEnum = Field(
        ...,
        description="是否修改过"
    )
    usage_type: UsageTypeEnum = Field(
        ...,
        description="使用方式"
    )


class LegalDeclarationCreate(LegalDeclarationBase):
    """创建法务声明请求"""
    compliance_record_id: int = Field(..., description="关联合规记录 ID")


class LegalDeclarationUpdate(BaseModel):
    """更新法务声明请求"""
    purpose_of_use: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="使用目的"
    )
    url_to_source: Optional[str] = Field(
        None,
        max_length=500,
        description="源代码下载位置"
    )
    license_info_url: Optional[str] = Field(
        None,
        max_length=500,
        description="许可证说明页面"
    )
    license_text_url: Optional[str] = Field(
        None,
        max_length=500,
        description="许可证全文 URL"
    )
    license_name: Optional[str] = Field(
        None,
        max_length=100,
        description="SPDX 许可证 ID"
    )
    is_modified: Optional[IsModifiedEnum] = Field(
        None,
        description="是否修改过"
    )
    usage_type: Optional[UsageTypeEnum] = Field(
        None,
        description="使用方式"
    )


class LegalDeclarationSubmit(BaseModel):
    """提交法务声明请求"""
    pass


class ComplianceRecordRef(BaseModel):
    """合规记录引用"""
    id: int
    system_name: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ComponentRef(BaseModel):
    """组件引用"""
    id: int
    name: str
    version: str
    license: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LegalDeclarationResponse(LegalDeclarationBase):
    """法务声明响应"""
    id: int
    compliance_record_id: int
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalTimelineEntry(BaseModel):
    """审批时间线条目"""
    stage: str  # "security_review" or "legal_approve"
    stage_name: str  # "安全审批" or "法务审批"
    approver_email: Optional[str] = None
    approved_at: Optional[datetime] = None
    status: str  # "pending" or "approved"


class LegalDeclarationDetailResponse(LegalDeclarationResponse):
    """法务声明详情响应（含关联信息）"""
    compliance_record: Optional[ComplianceRecordRef] = None
    component: Optional[ComponentRef] = None
    approval_timeline: Optional[List[ApprovalTimelineEntry]] = None
    current_status: Optional[str] = None


class BulkImportResult(BaseModel):
    """批量导入结果"""
    success_count: int
    failed_count: int
    results: List["BulkImportItemResult"]


class BulkImportItemResult(BaseModel):
    """批量导入单项结果"""
    component_name: str
    component_version: str
    success: bool
    declaration_id: Optional[int] = None
    error: Optional[str] = None


class ApprovalTimelineResponse(BaseModel):
    """审批时间线响应"""
    timeline: List[ApprovalTimelineEntry]
    current_status: str


class HistorySuggestion(BaseModel):
    """历史复用建议"""
    id: int
    system_name: str
    license_name: str
    purpose_of_use: str
    usage_type: str
    is_modified: str
    approved_at: datetime
    approved_by: Optional[str] = None


class HistorySuggestionResponse(BaseModel):
    """历史复用建议响应"""
    has_history: bool
    suggestions: List[HistorySuggestion]


class BulkAutofillItem(BaseModel):
    """批量预填充单项结果"""
    component_name: str
    component_version: str
    license_name: str = ""
    url_to_source: str = ""
    license_info_url: str = ""
    license_text_url: str = ""
    is_modified: str = "no"
    usage_type: str = ""
    purpose_of_use: str = ""
    purpose_of_use_suggestion: str = ""
    source: str = "spdx"  # "spdx" 或 "history"
    is_approved: bool = False  # 组件是否已法务审批通过


class BulkAutofillResponse(BaseModel):
    """批量预填充响应"""
    items: List[BulkAutofillItem]


# 更新 forward references
LegalDeclarationDetailResponse.model_rebuild()
