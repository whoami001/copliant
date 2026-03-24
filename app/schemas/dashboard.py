"""仪表板相关 Schema"""

from typing import List, Optional
from pydantic import BaseModel


class DashboardTodoItem(BaseModel):
    """待办事项项"""
    id: int
    record_name: str
    system_name: str
    status: str
    requires_action: bool
    # 审批意见（驳回原因/要求补充信息）
    rejection_reason: Optional[str] = None
    required_fields: Optional[List[str]] = None


class DashboardTodoResponse(BaseModel):
    """待办事项响应"""
    items: List[DashboardTodoItem]
    total: int


class DashboardStatsResponse(BaseModel):
    """统计信息响应"""
    pending_my_action: int
    approved_this_month: int
    avg_processing_days: float
    total_records: int


class DashboardSystemGroupedTodoItem(BaseModel):
    """按系统分组的待办事项项"""
    system_name: str
    component_count: int
    status: str
    earliest_created_at: str
    record_ids: List[int]
    # 用于显示操作按钮
    first_record_id: int
    # 审批意见（聚合该系统下所有记录的驳回原因）
    rejection_reason: Optional[str] = None
    # 需要补充的字段（聚合该系统下所有记录的要求）
    required_fields: Optional[List[str]] = None


class DashboardSystemGroupedTodoResponse(BaseModel):
    """按系统分组的待办事项响应"""
    items: List[DashboardSystemGroupedTodoItem]
    total: int
