"""组件相关 Schema"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ComponentBase(BaseModel):
    """组件基础 Schema"""
    name: str
    version: str
    license: Optional[str] = None
    copyright: Optional[str] = None
    usage_type: Optional[str] = None


class ComponentCreate(ComponentBase):
    """创建组件请求"""
    black_duck_report_id: Optional[str] = None


class ComponentUpdate(BaseModel):
    """更新组件请求"""
    license: Optional[str] = None
    copyright: Optional[str] = None
    usage_type: Optional[str] = None
    license_risk_level: Optional[str] = None


class ComponentResponse(ComponentBase):
    """组件响应"""
    id: int
    license_risk_level: str
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ComponentMatchResponse(BaseModel):
    """组件匹配结果"""
    matched: bool
    existing_component: Optional[ComponentResponse] = None
    message: str


class BlackDuckReportUpload(BaseModel):
    """上传 Black Duck 报告请求"""
    report_id: str
    system_name: str
