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

    def _find_or_create_system_notification(
        self,
        user: User,
        record: ComplianceRecord,
        title: str,
        message: str,
        notification_type: NotificationType,
    ) -> Notification:
        """
        查找或创建系统级别的通知（按系统名称聚合）

        如果同一系统已有相同类型的未读通知，则追加内容而不是创建新通知
        """
        # 查找同一系统的未读通知
        existing = self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.type == notification_type,
            Notification.is_read == False,
            Notification.message.ilike(f"%{record.system_name}%"),
        ).first()

        if existing:
            # 追加内容到已有通知
            component_info = f"({record.component.name}@{record.component.version})"
            if component_info not in existing.message:
                # 追加组件信息
                existing.message = existing.message.rstrip(".") + f"，{component_info} 等组件。\n"
            existing.created_at = datetime.utcnow()  # 更新时间
            self.db.commit()
            return existing

        # 创建新通知
        return self.create_notification(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_record=record,
        )

    def notify_security_rejected(
        self,
        user: User,
        record: ComplianceRecord,
        reason: str,
        required_fields: List[str] = None,
    ) -> Notification:
        """通知安全驳回（按系统聚合，支持组件计数）"""
        import re
        from sqlalchemy import or_

        # 查找同一系统的未读通知
        # 支持新旧两种格式：
        # 新格式：系统：<system_name>（N 个组件）\n...
        # 旧格式：您的合规记录「<component>@<version> - <system_name>」...
        existing = self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.type == NotificationType.SECURITY_REJECTED,
            Notification.is_read == False,
            or_(
                Notification.message.ilike(f"系统：{record.system_name}%"),
                Notification.message.ilike(f"%- {record.system_name}%"),
            )
        ).first()

        if existing:
            # 更新驳回原因
            if reason:
                existing.message = re.sub(
                    r'驳回原因：[^\n]*',
                    f"驳回原因：{reason}",
                    existing.message
                )

            # 更新需要补充的字段
            if required_fields:
                current_fields_match = re.search(r'需要补充的字段：([^\n]*)', existing.message)
                if current_fields_match:
                    current_fields = current_fields_match.group(1).strip()
                    # 合并字段列表（去重）
                    all_fields = set(f.strip() for f in current_fields.split(',') if f.strip())
                    all_fields.update(required_fields)
                    new_fields_str = ', '.join(sorted(all_fields))
                    existing.message = existing.message.replace(
                        f"需要补充的字段：{current_fields}",
                        f"需要补充的字段：{new_fields_str}"
                    )
                else:
                    fields_str = ', '.join(required_fields)
                    existing.message += f"\n需要补充的字段：{fields_str}"

            # 更新备注（如果没有或需要更新）
            if "备注：" not in existing.message:
                existing.message += f"\n备注：{reason}"

            existing.created_at = datetime.utcnow()
            self.db.commit()
            return existing

        # 创建新通知 - 简化格式（包含组件计数）
        fields_str = ", ".join(required_fields) if required_fields else "无"
        message = (
            f"系统：{record.system_name}（1 个组件）\n"
            f"驳回原因：{reason}\n"
            f"需要补充的字段：{fields_str}\n"
            f"备注：{reason}"
        )
        return self.create_notification(
            user=user,
            title="安全校验被驳回",
            message=message,
            notification_type=NotificationType.SECURITY_REJECTED,
            related_record=record,
        )

    def notify_legal_rejected(
        self,
        user: User,
        record: ComplianceRecord,
        reason: str,
    ) -> Notification:
        """通知法务驳回（要求修改，按系统聚合）"""
        # 查找同一系统的未读通知
        existing = self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.type == NotificationType.LEGAL_REJECTED,
            Notification.is_read == False,
            Notification.message.ilike(f"%系统：{record.system_name}%"),
        ).first()

        if existing:
            # 更新驳回原因
            if reason and reason not in existing.message:
                existing.message = existing.message.replace(
                    f"驳回原因：{existing.reason if hasattr(existing, 'reason') else '待补充'}",
                    f"驳回原因：{reason}"
                )
            existing.created_at = datetime.utcnow()
            self.db.commit()
            return existing

        # 创建新通知 - 简化格式
        message = f"系统：{record.system_name}\n驳回原因：{reason}\n请修改后重新提交。"
        return self.create_notification(
            user=user,
            title="法务审批被驳回（要求修改）",
            message=message,
            notification_type=NotificationType.LEGAL_REJECTED,
            related_record=record,
        )

    def notify_legal_denied(
        self,
        user: User,
        record: ComplianceRecord,
        reason: str,
    ) -> Notification:
        """通知法务拒绝（按系统聚合）"""
        # 查找同一系统的未读通知
        existing = self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.type == NotificationType.LEGAL_DENIED,
            Notification.is_read == False,
            Notification.message.ilike(f"%系统：{record.system_name}%"),
        ).first()

        if existing:
            # 更新拒绝原因
            if reason and reason not in existing.message:
                existing.message = existing.message.replace(
                    f"拒绝原因：{existing.reason if hasattr(existing, 'reason') else '待补充'}",
                    f"拒绝原因：{reason}"
                )
            existing.created_at = datetime.utcnow()
            self.db.commit()
            return existing

        # 创建新通知 - 简化格式
        message = f"系统：{record.system_name}\n拒绝原因：{reason}"
        return self.create_notification(
            user=user,
            title="法务审批被拒绝",
            message=message,
            notification_type=NotificationType.LEGAL_DENIED,
            related_record=record,
        )

    def notify_legal_approved(
        self,
        user: User,
        record: ComplianceRecord,
        comments: Optional[str] = None,
    ) -> Notification:
        """通知法务审批通过（按系统聚合）"""
        # 查找同一系统的未读通知
        existing = self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.type == NotificationType.LEGAL_APPROVED,
            Notification.is_read == False,
            Notification.message.ilike(f"%系统：{record.system_name}%"),
        ).first()

        component_info = f"{record.component.name}@{record.component.version}"

        if existing:
            # 追加组件到已有通知
            if component_info not in existing.message:
                # 在系统名称后追加组件信息
                if f"，{component_info}" not in existing.message:
                    # 找到系统名称位置，在其后追加
                    import re
                    match = re.search(r'系统：([^\n]+)', existing.message)
                    if match:
                        existing.message = existing.message.replace(
                            f"系统：{match.group(1)}",
                            f"系统：{match.group(1)}（{component_info} 等）"
                        )
                    else:
                        existing.message = existing.message.rstrip(".") + f"，{component_info} 等组件。"
            existing.created_at = datetime.utcnow()
            self.db.commit()
            return existing

        # 创建新通知 - 简化格式
        message = f"系统：{record.system_name} 已通过法务审批。"
        if comments:
            message += f"\n\n备注：{comments}"
        return self.create_notification(
            user=user,
            title="法务审批通过",
            message=message,
            notification_type=NotificationType.LEGAL_APPROVED,
            related_record=record,
        )

    def notify_security_approved(
        self,
        user: User,
        record: ComplianceRecord,
        comments: Optional[str] = None,
    ) -> Notification:
        """通知安全审批通过（按系统聚合）"""
        # 查找同一系统的未读通知
        existing = self.db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.type == NotificationType.SECURITY_APPROVED,
            Notification.is_read == False,
            Notification.message.ilike(f"%系统：{record.system_name}%"),
        ).first()

        component_info = f"{record.component.name}@{record.component.version}"

        if existing:
            # 追加组件到已有通知
            if component_info not in existing.message:
                # 在系统名称后追加组件信息
                if f"，{component_info}" not in existing.message:
                    import re
                    match = re.search(r'系统：([^\n]+)', existing.message)
                    if match:
                        existing.message = existing.message.replace(
                            f"系统：{match.group(1)}",
                            f"系统：{match.group(1)}（{component_info} 等）"
                        )
                    else:
                        existing.message = existing.message.rstrip(".") + f"，{component_info} 等组件。"
            existing.created_at = datetime.utcnow()
            self.db.commit()
            return existing

        # 创建新通知 - 简化格式
        message = f"系统：{record.system_name} 已通过安全校验。"
        if comments:
            message += f"\n\n备注：{comments}"
        return self.create_notification(
            user=user,
            title="安全校验通过",
            message=message,
            notification_type=NotificationType.SECURITY_APPROVED,
            related_record=record,
        )

    def get_user_notifications(
        self,
        user: User,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
        hours: Optional[int] = None,
    ) -> List[Notification]:
        """
        获取用户通知列表

        Args:
            user: 用户
            skip: 跳过数量
            limit: 限制数量
            unread_only: 是否只获取未读
            hours: 限制最近 X 小时的通知（用于已读消息）

        Returns:
            通知列表
        """
        from datetime import timedelta

        query = self.db.query(Notification).filter(Notification.user_id == user.id)

        if unread_only:
            query = query.filter(Notification.is_read == False)
        elif hours is not None:
            # 已读消息只显示最近 X 小时的
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(Notification.created_at >= cutoff)

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
