"""
仪表板相关路由
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardTodoResponse, DashboardStatsResponse, DashboardTodoItem, DashboardSystemGroupedTodoItem, DashboardSystemGroupedTodoResponse, DashboardStatsDetailResponse
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.core.permissions import get_current_user_from_token, require_role
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/todo", response_model=DashboardTodoResponse)
@require_role([UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN])
async def get_dashboard_todo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """获取我的待办事项（根据角色过滤）"""

    # 根据角色过滤待办事项
    if current_user.role == UserRole.ENGINEER:
        # 研发：显示草稿状态和已驳回的记录（自己的）
        # 先查询记录列表，然后在 Python 中按系统分组（兼容 SQLite）
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

        # 在 Python 中按系统分组
        from collections import defaultdict
        system_groups = defaultdict(list)
        for record in pending_records:
            system_groups[record.system_name].append(record)

        # 转换为扁平列表（兼容前端现有逻辑）
        items = []
        for system_name, records in system_groups.items():
            for record in records:
                # 根据记录状态判断来源
                source = 'security' if record.status == RecordStatus.PENDING_SECURITY else 'legal' if record.status == RecordStatus.PENDING_LEGAL else None
                items.append(
                    DashboardTodoItem(
                        id=record.id,
                        record_name=f"{record.component.name}@{record.component.version}",
                        system_name=record.system_name,
                        status=record.status.value,
                        requires_action=True,
                        rejection_reason=record.rejection_reason,
                        required_fields=record.required_fields,
                        rejection_source=source,
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
                rejection_source='security',
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
                rejection_source='legal',
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
@require_role([UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN])
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
        # 先查询所有记录，然后在 Python 中分组（兼容 SQLite）
        pending_records = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.status.in_([
                RecordStatus.PENDING_SECURITY,
                RecordStatus.PENDING_LEGAL,
            ]))
            .order_by(ComplianceRecord.created_at.desc())
            .all()
        )

        # 在 Python 中按系统分组
        from collections import defaultdict
        system_groups = defaultdict(list)
        for record in pending_records:
            system_groups[record.system_name].append(record)

        items = []
        for system_name, records in system_groups.items():
            # 使用第一个记录的状态作为该系统状态
            first_record = records[0]
            # 聚合审批意见（收集所有记录的 rejection_reason，去重）
            rejection_reasons_set = set()
            rejection_sources = set()
            for r in records:
                if r.rejection_reason:
                    rejection_reasons_set.add(r.rejection_reason)
                # 根据记录状态判断来源
                if r.status == RecordStatus.PENDING_SECURITY or r.status == RecordStatus.REJECTED:
                    # 检查是否是安全驳回（通过审批历史判断）
                    if r.rejection_reason:
                        rejection_sources.add('security')
                    else:
                        rejection_sources.add('legal')
                elif r.status == RecordStatus.PENDING_LEGAL:
                    if r.rejection_reason:
                        rejection_sources.add('legal')

            required_fields_set = set()
            for r in records:
                if r.required_fields:
                    required_fields_set.update(r.required_fields)

            items.append(
                DashboardSystemGroupedTodoItem(
                    system_name=system_name or '未命名系统',
                    component_count=len(records),
                    status=first_record.status.value,
                    earliest_created_at=min(r.created_at.isoformat() for r in records),
                    record_ids=[r.id for r in records],
                    first_record_id=records[0].id,
                    rejection_reason='; '.join(rejection_reasons_set) if rejection_reasons_set else None,
                    required_fields=list(required_fields_set) if required_fields_set else None,
                    rejection_sources=list(rejection_sources) if rejection_sources else None,
                )
            )
    elif current_user.role == UserRole.ENGINEER:
        # 研发：按系统分组显示草稿和已驳回的记录（自己的）
        # 先查询所有记录，然后在 Python 中分组（兼容 SQLite）
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

        # 在 Python 中按系统分组
        from collections import defaultdict
        system_groups = defaultdict(list)
        for record in pending_records:
            system_groups[record.system_name].append(record)

        items = []
        for system_name, records in system_groups.items():
            first_record = records[0]
            # 聚合审批意见（收集所有记录的 rejection_reason，去重）
            rejection_reasons_set = set()
            rejection_sources = set()
            for r in records:
                if r.rejection_reason:
                    rejection_reasons_set.add(r.rejection_reason)
                    # 根据状态判断来源：REJECTED 状态需要查看是谁驳回的
                    if r.status == RecordStatus.REJECTED:
                        # 通过审批历史判断是安全还是法务驳回
                        # 简单判断：如果有 rejection_reason 且状态是 REJECTED，来源于最后一个驳回的用户角色
                        # 这里简化处理：如果 reason 存在，标记为 legal（因为法务是最终审批）
                        rejection_sources.add('legal')
                    else:
                        rejection_sources.add('security')

            required_fields_set = set()
            for r in records:
                if r.required_fields:
                    required_fields_set.update(r.required_fields)

            # 计算最早创建时间（取所有记录的最小值）
            earliest_date = min(r.created_at for r in records)

            items.append(
                DashboardSystemGroupedTodoItem(
                    system_name=system_name or '未命名系统',
                    component_count=len(records),
                    status=first_record.status.value,
                    earliest_created_at=earliest_date.isoformat() if earliest_date else '',
                    record_ids=[r.id for r in records],
                    first_record_id=records[0].id,
                    rejection_reason='; '.join(rejection_reasons_set) if rejection_reasons_set else None,
                    required_fields=list(required_fields_set) if required_fields_set else None,
                    rejection_sources=list(rejection_sources) if rejection_sources else None,
                )
            )
    else:
        # 其他角色：返回空
        items = []

    return DashboardSystemGroupedTodoResponse(items=items, total=len(items))


@router.get("/stats", response_model=DashboardStatsResponse)
@require_role([UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN])
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

    # 平均处理时间（天）- 从提交到法务审批通过的时间
    # 只计算已完成的记录（APPROVED 或 REJECTED 且有审批时间）
    completed_records = (
        db.query(ComplianceRecord)
        .filter(
            ComplianceRecord.status == RecordStatus.APPROVED,
            ComplianceRecord.submitted_at.isnot(None),
            ComplianceRecord.legal_approved_at.isnot(None),
        )
        .all()
    )

    if completed_records and len(completed_records) > 0:
        total_days = 0
        valid_count = 0
        for record in completed_records:
            if record.submitted_at and record.legal_approved_at:
                delta = record.legal_approved_at - record.submitted_at
                total_days += delta.total_seconds() / 86400  # 转换为天
                valid_count += 1
        avg_days = round(total_days / valid_count, 1) if valid_count > 0 else 0
    else:
        avg_days = 0

    # 总记录数
    total_count = db.query(ComplianceRecord).count()

    return DashboardStatsResponse(
        pending_my_action=pending_count,
        approved_this_month=approved_count,
        avg_processing_days=avg_days,
        total_records=total_count,
    )


@router.get("/stats-detail", response_model=DashboardStatsDetailResponse)
@require_role([UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN])
async def get_dashboard_stats_detail(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """获取统计详情（用于图表展示）"""
    from datetime import timedelta

    # 近 7 天处理趋势（按批准日期统计）
    today = datetime.utcnow().date()
    trend_data = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        next_date = date + timedelta(days=1)

        count = (
            db.query(ComplianceRecord)
            .filter(
                ComplianceRecord.status == RecordStatus.APPROVED,
                ComplianceRecord.legal_approved_at >= date,
                ComplianceRecord.legal_approved_at < next_date,
            )
            .count()
        )

        trend_data.append({
            "label": f"{date.month}/{date.day}",
            "count": count
        })

    # 状态分布
    status_counts = (
        db.query(
            ComplianceRecord.status,
            func.count(ComplianceRecord.id).label('count')
        )
        .group_by(ComplianceRecord.status)
        .all()
    )

    status_distribution = {
        record.status.value: record.count
        for record in status_counts
    }

    return DashboardStatsDetailResponse(
        trend=trend_data,
        status_distribution=status_distribution
    )
