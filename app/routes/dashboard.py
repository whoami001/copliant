"""
仪表板相关路由
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardTodoResponse, DashboardStatsResponse, DashboardTodoItem, DashboardSystemGroupedTodoItem, DashboardSystemGroupedTodoResponse
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
        # 研发：显示草稿状态和已驳回的记录（自己的），按系统分组
        query = (
            db.query(
                ComplianceRecord.system_name,
                func.count(ComplianceRecord.id).label('component_count'),
                func.min(ComplianceRecord.status).label('status'),
                func.array_agg(ComplianceRecord.id).label('record_ids'),
            )
            .filter(
                ComplianceRecord.filled_by == current_user.id,
                ComplianceRecord.status.in_([
                    RecordStatus.DRAFT,
                    RecordStatus.REJECTED,
                ])
            )
            .group_by(ComplianceRecord.system_name)
            .order_by(func.min(ComplianceRecord.created_at).desc())
        )
        results = query.all()

        # 将分组结果转换为扁平列表（兼容前端现有逻辑）
        items = []
        for row in results:
            # 获取该系统下所有记录的详情
            records = db.query(ComplianceRecord).filter(
                ComplianceRecord.id.in_(row.record_ids)
            ).all()

            for record in records:
                items.append(
                    DashboardTodoItem(
                        id=record.id,
                        record_name=f"{record.component.name}@{record.component.version}",
                        system_name=record.system_name,
                        status=record.status.value,
                        requires_action=True,
                        rejection_reason=record.rejection_reason,
                        required_fields=record.required_fields,
                    )
                )
    elif current_user.role == UserRole.SECURITY:
        # 安全：显示待安全校验的记录
        pending_records = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.status == RecordStatus.PENDING_SECURITY)
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
                rejection_reason=record.rejection_reason,
                required_fields=record.required_fields,
            )
            for record in pending_records
        ]
    elif current_user.role == UserRole.LEGAL:
        # 法务：显示待法务审批的记录
        pending_records = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.status == RecordStatus.PENDING_LEGAL)
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
                rejection_reason=record.rejection_reason,
                required_fields=record.required_fields,
            )
            for record in pending_records
        ]
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
                rejection_reason=record.rejection_reason,
                required_fields=record.required_fields,
            )
            for record in pending_records
        ]

    return DashboardTodoResponse(items=items, total=len(items))


@router.get("/todo/system-grouped", response_model=DashboardSystemGroupedTodoResponse)
async def get_dashboard_todo_system_grouped(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """获取我的待办事项（按系统分组显示）"""

    # 根据角色过滤待办事项
    if current_user.role == UserRole.SECURITY:
        # 安全：按系统分组显示待安全校验的记录
        query = (
            db.query(
                ComplianceRecord.system_name,
                func.count(ComplianceRecord.id).label('component_count'),
                func.min(ComplianceRecord.status).label('status'),
                func.min(ComplianceRecord.created_at).label('earliest_created_at'),
                func.array_agg(ComplianceRecord.id).label('record_ids'),
            )
            .filter(ComplianceRecord.status == RecordStatus.PENDING_SECURITY)
            .group_by(ComplianceRecord.system_name)
            .order_by(func.min(ComplianceRecord.created_at).desc())
        )
        results = query.all()

        items = [
            DashboardSystemGroupedTodoItem(
                system_name=row.system_name or '未命名系统',
                component_count=row.component_count,
                status=RecordStatus.PENDING_SECURITY.value,
                earliest_created_at=row.earliest_created_at.isoformat() if row.earliest_created_at else '',
                record_ids=list(row.record_ids) if row.record_ids else [],
                first_record_id=row.record_ids[0] if row.record_ids else None,
            )
            for row in results
        ]
    elif current_user.role == UserRole.LEGAL:
        # 法务：按系统分组显示待法务审批的记录
        query = (
            db.query(
                ComplianceRecord.system_name,
                func.count(ComplianceRecord.id).label('component_count'),
                func.min(ComplianceRecord.status).label('status'),
                func.min(ComplianceRecord.created_at).label('earliest_created_at'),
                func.array_agg(ComplianceRecord.id).label('record_ids'),
            )
            .filter(ComplianceRecord.status == RecordStatus.PENDING_LEGAL)
            .group_by(ComplianceRecord.system_name)
            .order_by(func.min(ComplianceRecord.created_at).desc())
        )
        results = query.all()

        items = [
            DashboardSystemGroupedTodoItem(
                system_name=row.system_name or '未命名系统',
                component_count=row.component_count,
                status=RecordStatus.PENDING_LEGAL.value,
                earliest_created_at=row.earliest_created_at.isoformat() if row.earliest_created_at else '',
                record_ids=list(row.record_ids) if row.record_ids else [],
                first_record_id=row.record_ids[0] if row.record_ids else None,
            )
            for row in results
        ]
    elif current_user.role == UserRole.ADMIN:
        # Admin：按系统分组显示所有待处理记录
        query = (
            db.query(
                ComplianceRecord.system_name,
                func.count(ComplianceRecord.id).label('component_count'),
                func.min(ComplianceRecord.status).label('status'),
                func.min(ComplianceRecord.created_at).label('earliest_created_at'),
                func.array_agg(ComplianceRecord.id).label('record_ids'),
            )
            .filter(ComplianceRecord.status.in_([
                RecordStatus.PENDING_SECURITY,
                RecordStatus.PENDING_LEGAL,
            ]))
            .group_by(ComplianceRecord.system_name)
            .order_by(func.min(ComplianceRecord.created_at).desc())
        )
        results = query.all()

        items = [
            DashboardSystemGroupedTodoItem(
                system_name=row.system_name or '未命名系统',
                component_count=row.component_count,
                status=row.status.value if isinstance(row.status, RecordStatus) else row.status,
                earliest_created_at=row.earliest_created_at.isoformat() if row.earliest_created_at else '',
                record_ids=list(row.record_ids) if row.record_ids else [],
                first_record_id=row.record_ids[0] if row.record_ids else None,
            )
            for row in results
        ]
    elif current_user.role == UserRole.ENGINEER:
        # 研发：按系统分组显示草稿和已驳回的记录（自己的）
        query = (
            db.query(
                ComplianceRecord.system_name,
                func.count(ComplianceRecord.id).label('component_count'),
                func.min(ComplianceRecord.status).label('status'),
                func.array_agg(ComplianceRecord.id).label('record_ids'),
            )
            .filter(
                ComplianceRecord.filled_by == current_user.id,
                ComplianceRecord.status.in_([
                    RecordStatus.DRAFT,
                    RecordStatus.REJECTED,
                ])
            )
            .group_by(ComplianceRecord.system_name)
            .order_by(func.min(ComplianceRecord.created_at).desc())
        )
        results = query.all()

        items = [
            DashboardSystemGroupedTodoItem(
                system_name=row.system_name or '未命名系统',
                component_count=row.component_count,
                status=row.status.value if isinstance(row.status, RecordStatus) else row.status,
                earliest_created_at='',
                record_ids=list(row.record_ids) if row.record_ids else [],
                first_record_id=row.record_ids[0] if row.record_ids else None,
            )
            for row in results
        ]
    else:
        # 其他角色：返回空
        items = []

    return DashboardSystemGroupedTodoResponse(items=items, total=len(items))


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
