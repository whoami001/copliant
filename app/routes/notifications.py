"""
通知相关路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    MarkAsReadResponse,
)
from app.models.user import User, UserRole
from app.services.notification import get_notification_service
from app.core.permissions import get_current_user_from_token
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """获取当前用户的通知列表"""
    service = get_notification_service(db)

    notifications = service.get_user_notifications(
        user=current_user,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
    )

    unread_count = service.get_unread_count(user=current_user)

    return NotificationListResponse(
        items=notifications,
        total=len(notifications),
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """获取当前用户未读通知数"""
    service = get_notification_service(db)
    count = service.get_unread_count(user=current_user)
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/mark-as-read", response_model=MarkAsReadResponse)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """标记单个通知为已读"""
    service = get_notification_service(db)
    success = service.mark_as_read(notification_id=notification_id, user=current_user)

    if not success:
        raise HTTPException(status_code=404, detail="通知不存在或不属于当前用户")

    return MarkAsReadResponse(success=True)


@router.post("/mark-all-as-read", response_model=MarkAsReadResponse)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """标记所有通知为已读"""
    service = get_notification_service(db)
    count = service.mark_all_as_read(user=current_user)
    logger.info(f"用户 {current_user.id} 标记了 {count} 个通知为已读")
    return MarkAsReadResponse(success=True)
