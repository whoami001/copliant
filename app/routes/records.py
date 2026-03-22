"""
合规记录相关路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.database import get_db
from app.schemas.compliance_record import (
    ComplianceRecordCreate,
    ComplianceRecordResponse,
    ComplianceRecordUpdate,
    ComplianceRecordSubmit,
    ComplianceRecordApprove,
    ComplianceRecordReject,
    RecordStatusEnum,
)
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.services.approval_flow import get_approval_flow_service
from app.core.permissions import get_current_user_from_token, can
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=List[ComplianceRecordResponse])
async def list_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    status: Optional[RecordStatusEnum] = None,
    system_name: Optional[str] = None,
    response: Response = None,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """获取合规记录列表（支持状态和系统过滤）"""
    from app.models.component import Component

    query = db.query(ComplianceRecord).join(Component, isouter=True).options(joinedload(ComplianceRecord.component))

    if status:
        query = query.filter(ComplianceRecord.status == status)

    if system_name:
        query = query.filter(ComplianceRecord.system_name.ilike(f"%{system_name}%"))

    # 角色数据过滤：Engineer 只能看到自己的记录和 NULL 遗留数据
    if current_user.role == UserRole.ENGINEER:
        logger.debug(f"用户 {current_user.id} 查询记录，应用数据过滤")
        query = query.filter(
            or_(
                ComplianceRecord.filled_by == current_user.id,
                ComplianceRecord.filled_by.is_(None)
            )
        )

    # 获取总数
    total = query.count()

    records = query.order_by(ComplianceRecord.created_at.desc()).offset(skip).limit(limit).all()

    # 在 response header 中返回总数
    if response:
        response.headers["X-Total-Count"] = str(total)

    return records


@router.post("", response_model=ComplianceRecordResponse)
async def create_record(
    record_data: ComplianceRecordCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """创建合规记录"""
    # 检查组件是否存在
    from app.models.component import Component
    component = db.query(Component).filter(Component.id == record_data.component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    record = ComplianceRecord(
        component_id=record_data.component_id,
        system_name=record_data.system_name,
        comments=record_data.comments,
        status=RecordStatus.DRAFT,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(f"创建合规记录：{record.id}")
    return record


@router.get("/{record_id}", response_model=ComplianceRecordResponse)
async def get_record(record_id: int, db: Session = Depends(get_db)):
    """获取合规记录详情"""
    record = db.query(ComplianceRecord).options(joinedload(ComplianceRecord.component)).filter(ComplianceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.put("/{record_id}", response_model=ComplianceRecordResponse)
async def update_record(
    record_id: int,
    update_data: ComplianceRecordUpdate,
    db: Session = Depends(get_db),
):
    """更新合规记录（仅限草稿状态）"""
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if record.status != RecordStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只有草稿状态可以修改")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    return record


@router.post("/{record_id}/submit", response_model=ComplianceRecordResponse)
async def submit_record(
    record_id: int,
    submit_data: ComplianceRecordSubmit,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """提交审批"""
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # 检查权限：Engineer 只能提交自己的记录
    if record.filled_by is not None and record.filled_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="权限不足：只能提交自己创建的记录")

    approval_service = get_approval_flow_service(db)

    record = approval_service.submit_for_review(record, current_user)
    db.commit()
    db.refresh(record)

    return record


@router.post("/{record_id}/approve", response_model=ComplianceRecordResponse)
async def approve_record(
    record_id: int,
    approve_data: ComplianceRecordApprove,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """审批通过（安全或法务）"""
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    approval_service = get_approval_flow_service(db)

    if record.status == RecordStatus.PENDING_SECURITY:
        # 安全校验通过
        user = User(id=2, email="security@company.com", role=UserRole.SECURITY)
        record = approval_service.security_review(record, user, pass_review=True, comments=approve_data.comments)
    elif record.status == RecordStatus.PENDING_LEGAL:
        # 法务审批通过
        user = User(id=3, email="legal@company.com", role=UserRole.LEGAL)
        record = approval_service.legal_approve(record, user, approve=True, comments=approve_data.comments)

        # 方案 A: 组件全局审批 — 法务通过后，自动标记组件为已审批
        record.component.is_approved = True
        db.add(record.component)
    else:
        raise HTTPException(status_code=400, detail="当前状态不能执行审批操作")

    db.commit()
    db.refresh(record)

    return record


@router.post("/{record_id}/reject", response_model=ComplianceRecordResponse)
async def reject_record(
    record_id: int,
    reject_data: ComplianceRecordReject,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """审批驳回"""
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    approval_service = get_approval_flow_service(db)

    if record.status == RecordStatus.PENDING_SECURITY:
        user = User(id=2, email="security@company.com", role=UserRole.SECURITY)
        record = approval_service.security_review(record, user, pass_review=False, comments=reject_data.comments)
    elif record.status == RecordStatus.PENDING_LEGAL:
        user = User(id=3, email="legal@company.com", role=UserRole.LEGAL)
        record = approval_service.legal_approve(record, user, approve=False, comments=reject_data.comments)
    else:
        raise HTTPException(status_code=400, detail="当前状态不能执行驳回操作")

    db.commit()
    db.refresh(record)

    return record


@router.post("/{record_id}/request-changes", response_model=ComplianceRecordResponse)
async def request_changes(
    record_id: int,
    reject_data: ComplianceRecordReject,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """要求修改（法务用）"""
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    approval_service = get_approval_flow_service(db)

    user = User(id=3, email="legal@company.com", role=UserRole.LEGAL)
    record = approval_service.request_changes(record, user, comments=reject_data.comments)

    db.commit()
    db.refresh(record)

    return record
