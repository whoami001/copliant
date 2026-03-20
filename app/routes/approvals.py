"""
审批历史相关路由
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.approval import ApprovalHistoryResponse
from app.models.approval_history import ApprovalHistory
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{record_id}/history", response_model=List[ApprovalHistoryResponse])
async def get_approval_history(record_id: int, db: Session = Depends(get_db)):
    """获取审批历史"""
    histories = (
        db.query(ApprovalHistory)
        .filter(ApprovalHistory.record_id == record_id)
        .order_by(ApprovalHistory.created_at.desc())
        .all()
    )

    # 关联查询用户信息
    from app.models.user import User
    for history in histories:
        user = db.query(User).filter(User.id == history.actor).first()
        history.actor_name = user.name if user else f"User-{history.actor}"

    return histories
