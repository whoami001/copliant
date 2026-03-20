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
