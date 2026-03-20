"""
仪表板相关路由
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardTodoResponse, DashboardStatsResponse, DashboardTodoItem
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/todo", response_model=DashboardTodoResponse)
async def get_dashboard_todo(db: Session = Depends(get_db)):
    """获取我的待办事项"""
    # MVP 版本：返回所有待处理记录
    # 生产环境需要根据用户角色过滤

    pending_records = (
        db.query(ComplianceRecord)
        .filter(ComplianceRecord.status.in_([
            RecordStatus.PENDING_SECURITY,
            RecordStatus.PENDING_LEGAL,
        ]))
        .order_by(ComplianceRecord.created_at.desc())
        .all()
    )

    items = [
        DashboardTodoItem(
            id=record.id,
            record_name=f"{record.component.name}@{record.component.version}",
            system_name=record.system_name,
            status=record.status.value,
            requires_action=True,
        )
        for record in pending_records
    ]

    return DashboardTodoResponse(items=items, total=len(items))


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取统计信息"""
    # 待我处理数量
    pending_count = (
        db.query(ComplianceRecord)
        .filter(ComplianceRecord.status.in_([
            RecordStatus.PENDING_SECURITY,
            RecordStatus.PENDING_LEGAL,
        ]))
        .count()
    )

    # 本月通过数量
    this_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    approved_count = (
        db.query(ComplianceRecord)
        .filter(
            ComplianceRecord.status == RecordStatus.APPROVED,
            ComplianceRecord.legal_approved_at >= this_month,
        )
        .count()
    )

    # 平均处理时间（天）
    # MVP 简化：假设平均 2.3 天
    avg_days = 2.3

    # 总记录数
    total_count = db.query(ComplianceRecord).count()

    return DashboardStatsResponse(
        pending_my_action=pending_count,
        approved_this_month=approved_count,
        avg_processing_days=avg_days,
        total_records=total_count,
    )
