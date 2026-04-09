"""
审批流服务

核心功能：
- 状态机管理
- 状态转换校验
- 权限校验
"""

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.approval_history import ApprovalHistory
from app.models.user import User, UserRole
from app.exceptions import InvalidStatusTransitionError, ForbiddenError, ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


# 状态转换规则
# key: (当前状态，目标状态), value: 允许的角色
VALID_TRANSITIONS = {
    (RecordStatus.DRAFT, RecordStatus.PENDING_SECURITY): [UserRole.ENGINEER],
    (RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL): [UserRole.SECURITY],
    (RecordStatus.PENDING_SECURITY, RecordStatus.DRAFT): [UserRole.SECURITY],  # 驳回
    (RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED): [UserRole.LEGAL],
    (RecordStatus.PENDING_LEGAL, RecordStatus.DRAFT): [UserRole.LEGAL],  # 驳回/要求修改
    (RecordStatus.PENDING_LEGAL, RecordStatus.REJECTED): [UserRole.LEGAL],  # 直接拒绝
}


class ApprovalFlowService:
    """审批流服务"""

    def __init__(self, db: Session):
        self.db = db

    def can_transition(
        self,
        current_status: RecordStatus,
        target_status: RecordStatus,
        user_role: UserRole,
    ) -> bool:
        """
        检查状态转换是否合法

        Args:
            current_status: 当前状态
            target_status: 目标状态
            user_role: 用户角色

        Returns:
            True 表示允许转换
        """
        key = (current_status, target_status)
        allowed_roles = VALID_TRANSITIONS.get(key, [])
        return user_role in allowed_roles

    def submit_for_review(self, record: ComplianceRecord, user: User) -> ComplianceRecord:
        """
        提交审批

        Args:
            record: 合规记录
            user: 提交用户

        Returns:
            更新后的记录
        """
        if record.status != RecordStatus.DRAFT:
            raise ValidationError("只有草稿状态可以提交审批")

        if user.role not in [UserRole.ENGINEER, UserRole.ADMIN]:
            raise ForbiddenError("只有研发可以提交审批")

        old_status = record.status
        record.status = RecordStatus.PENDING_SECURITY
        record.filled_by = user.id
        record.submitted_at = datetime.utcnow()

        self._add_history(record, user, "submit", old_status, record.status)

        logger.info(f"记录 {record.id} 已提交审批，当前状态：{record.status}")
        return record

    def security_review(
        self,
        record: ComplianceRecord,
        user: User,
        pass_review: bool,
        comments: Optional[str] = None,
    ) -> ComplianceRecord:
        """
        安全校验

        Args:
            record: 合规记录
            user: 安全用户
            pass_review: 是否通过
            comments: 意见

        Returns:
            更新后的记录
        """
        if record.status != RecordStatus.PENDING_SECURITY:
            raise ValidationError("记录不在安全校验状态")

        if user.role not in [UserRole.SECURITY, UserRole.ADMIN]:
            raise ForbiddenError("只有安全角色可以执行安全校验")

        old_status = record.status

        if pass_review:
            record.status = RecordStatus.PENDING_LEGAL
            record.reviewed_by_security = user.id
            record.security_reviewed_at = datetime.utcnow()
            action = "approve"
        else:
            record.status = RecordStatus.DRAFT
            action = "request_changes"

        record.comments = comments
        self._add_history(record, user, action, old_status, record.status, comments)

        logger.info(f"记录 {record.id} 安全校验完成，当前状态：{record.status}")
        return record

    def legal_approve(
        self,
        record: ComplianceRecord,
        user: User,
        approve: bool,
        comments: Optional[str] = None,
    ) -> ComplianceRecord:
        """
        法务审批

        Args:
            record: 合规记录
            user: 法务用户
            approve: 是否通过
            comments: 意见

        Returns:
            更新后的记录
        """
        if record.status != RecordStatus.PENDING_LEGAL:
            raise ValidationError("记录不在法务审批状态")

        if user.role not in [UserRole.LEGAL, UserRole.ADMIN]:
            raise ForbiddenError("只有法务角色可以执行审批")

        old_status = record.status

        if approve:
            record.status = RecordStatus.APPROVED
            record.approved_by_legal = user.id
            record.legal_approved_at = datetime.utcnow()
            action = "approve"
        else:
            if not comments:
                raise ValidationError("驳回必须填写原因")
            record.status = RecordStatus.REJECTED
            action = "reject"

        record.comments = comments
        self._add_history(record, user, action, old_status, record.status, comments)

        logger.info(f"记录 {record.id} 法务审批完成，当前状态：{record.status}")
        return record

    def request_changes(
        self,
        record: ComplianceRecord,
        user: User,
        comments: str,
    ) -> ComplianceRecord:
        """
        要求修改（安全或法务用）

        Args:
            record: 合规记录
            user: 安全或法务用户
            comments: 修改意见

        Returns:
            更新后的记录
        """
        if record.status not in [RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL]:
            raise ValidationError("记录不在审批状态")

        if user.role not in [UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN]:
            raise ForbiddenError("只有安全或法务角色可以要求修改")

        old_status = record.status
        record.status = RecordStatus.DRAFT
        record.comments = comments

        self._add_history(record, user, "request_changes", old_status, record.status, comments)

        logger.info(f"记录 {record.id} 要求修改，当前状态：{record.status}")
        return record

    def _add_history(
        self,
        record: ComplianceRecord,
        user: User,
        action: str,
        previous_status: RecordStatus,
        new_status: RecordStatus,
        comments: Optional[str] = None,
    ):
        """添加审批历史记录"""
        history = ApprovalHistory(
            record_id=record.id,
            action=action,
            actor=user.id,
            role=user.role.value,
            previous_status=previous_status.value,
            new_status=new_status.value,
            comments=comments,
        )
        self.db.add(history)


def get_approval_flow_service(db: Session) -> ApprovalFlowService:
    """获取审批流服务实例"""
    return ApprovalFlowService(db)
