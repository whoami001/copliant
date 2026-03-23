"""
通知服务

功能：
- 创建通知
- 获取用户通知列表
- 标记通知为已读
- 获取未读通知数
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.models.compliance_record import ComplianceRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """通知服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user: User,
        title: str,
        message: str,
        notification_type: NotificationType,
        related_record: Optional[ComplianceRecord] = None,
    ) -> Notification:
        """
        创建通知

        Args:
            user: 接收通知的用户
            title: 通知标题
            message: 通知内容
            notification_type: 通知类型
            related_record: 关联的合规记录

        Returns:
            创建的通知对象
        """
        notification = Notification(
            user_id=user.id,
            title=title,
            message=message,
            type=notification_type,
            related_record_id=related_record.id if related_record else None,
        )
        self.db.add(notification)
        logger.info(f"创建通知：用户 {user.id}, 类型 {notification_type.value}")
        return notification

    def notify_security_rejected(
        self,
        user: User,
        record: ComplianceRecord,
        reason: str,
    ) -> Notification:
        """通知安全驳回"""
        return self.create_notification(
            user=user,
            title="安全校验被驳回",
            message=f"您的合规记录「{record.component.name}@{record.component.version} - {record.system_name}」在安全校验阶段被驳回。\n\n驳回原因：{reason}\n\n请修改后重新提交。",
            notification_type=NotificationType.SECURITY_REJECTED,
            related_record=record,
        )

    def notify_legal_rejected(
        self,
        user: User,
        record: ComplianceRecord,
        reason: str,
    ) -> Notification:
        """通知法务驳回（要求修改）"""
        return self.create_notification(
            user=user,
            title="法务审批被驳回（要求修改）",
            message=f"您的合规记录「{record.component.name}@{record.component.version} - {record.system_name}」在法务审批阶段被驳回，需要修改。\n\n驳回原因：{reason}\n\n请修改后重新提交。",
            notification_type=NotificationType.LEGAL_REJECTED,
            related_record=record,
        )

    def notify_legal_denied(
        self,
        user: User,
        record: ComplianceRecord,
        reason: str,
    ) -> Notification:
        """通知法务拒绝"""
        return self.create_notification(
            user=user,
            title="法务审批被拒绝",
            message=f"您的合规记录「{record.component.name}@{record.component.version} - {record.system_name}」在法务审批阶段被拒绝。\n\n拒绝原因：{reason}",
            notification_type=NotificationType.LEGAL_DENIED,
            related_record=record,
        )

    def get_user_notifications(
        self,
        user: User,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[Notification]:
        """
        获取用户通知列表

        Args:
            user: 用户
            skip: 跳过数量
            limit: 限制数量
            unread_only: 是否只获取未读

        Returns:
            通知列表
        """
        query = self.db.query(Notification).filter(Notification.user_id == user.id)

        if unread_only:
            query = query.filter(Notification.is_read == False)

        # 未读通知排在前面，同按创建时间倒序
        return query.order_by(
            Notification.is_read.asc(),
            Notification.created_at.desc()
        ).offset(skip).limit(limit).all()

    def get_unread_count(self, user: User) -> int:
        """获取用户未读通知数"""
        return self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).count()

    def mark_as_read(self, notification_id: int, user: User) -> bool:
        """
        标记通知为已读

        Args:
            notification_id: 通知 ID
            user: 用户

        Returns:
            是否成功
        """
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        ).first()

        if not notification:
            return False

        notification.is_read = True
        self.db.commit()
        return True

    def mark_all_as_read(self, user: User) -> int:
        """
        标记所有通知为已读

        Args:
            user: 用户

        Returns:
            标记为已读的数量
        """
        result = self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).update({"is_read": True})

        self.db.commit()
        return result


def get_notification_service(db: Session) -> NotificationService:
    """获取通知服务实例"""
    return NotificationService(db)
