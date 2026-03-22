"""
仪表板相关路由
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardTodoResponse, DashboardStatsResponse, DashboardTodoItem
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.core.permissions import get_current_user_from_token
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/todo", response_model=DashboardTodoResponse)
async def get_dashboard_todo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """获取我的待办事项（根据角色过滤）"""

    # 根据角色过滤待办事项
    if current_user.role == UserRole.ENGINEER:
        # 研发：显示草稿状态和已驳回的记录（自己的）
        pending_records = (
            db.query(ComplianceRecord)
            .filter(
                ComplianceRecord.filled_by == current_user.id,
                ComplianceRecord.status.in_([
                    RecordStatus.DRAFT,
                    RecordStatus.REJECTED,
                ])
            )
            .order_by(ComplianceRecord.created_at.desc())
            .all()
        )
    elif current_user.role == UserRole.SECURITY:
        # 安全：显示待安全校验的记录
        pending_records = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.status == RecordStatus.PENDING_SECURITY)
            .order_by(ComplianceRecord.created_at.desc())
            .all()
        )
    elif current_user.role == UserRole.LEGAL:
        # 法务：显示待法务审批的记录
        pending_records = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.status == RecordStatus.PENDING_LEGAL)
            .order_by(ComplianceRecord.created_at.desc())
            .all()
        )
    else:
        # Admin：显示所有待处理记录
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
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """获取统计信息（根据角色过滤）"""

    # 待我处理数量 - 根据角色过滤
    if current_user.role == UserRole.ENGINEER:
        pending_count = (
            db.query(ComplianceRecord)
            .filter(
                ComplianceRecord.filled_by == current_user.id,
                ComplianceRecord.status.in_([
                    RecordStatus.DRAFT,
                    RecordStatus.REJECTED,
                ])
            )
            .count()
        )
    elif current_user.role == UserRole.SECURITY:
        pending_count = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.status == RecordStatus.PENDING_SECURITY)
            .count()
        )
    elif current_user.role == UserRole.LEGAL:
        pending_count = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.status == RecordStatus.PENDING_LEGAL)
            .count()
        )
    else:
        # Admin
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

    # 平均处理时间（天）- MVP 简化
    avg_days = 2.3

    # 总记录数
    total_count = db.query(ComplianceRecord).count()

    return DashboardStatsResponse(
        pending_my_action=pending_count,
        approved_this_month=approved_count,
        avg_processing_days=avg_days,
        total_records=total_count,
    )
