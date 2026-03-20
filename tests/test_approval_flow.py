"""审批流服务测试"""

import pytest
from datetime import datetime

from app.services.approval_flow import ApprovalFlowService, VALID_TRANSITIONS
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.exceptions import InvalidStatusTransitionError, ForbiddenError, ValidationError


class TestApprovalFlowService:
    """审批流服务测试"""

    def test_valid_transitions_defined(self):
        """测试状态转换规则已定义"""
        assert (RecordStatus.DRAFT, RecordStatus.PENDING_SECURITY) in VALID_TRANSITIONS
        assert (RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL) in VALID_TRANSITIONS
        assert (RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED) in VALID_TRANSITIONS

    def test_can_transition_valid(self, db_session):
        """测试合法状态转换检测"""
        service = ApprovalFlowService(db_session)

        # 研发可以提交审批
        assert service.can_transition(
            RecordStatus.DRAFT,
            RecordStatus.PENDING_SECURITY,
            UserRole.ENGINEER,
        ) is True

        # 安全可以转到法务审批
        assert service.can_transition(
            RecordStatus.PENDING_SECURITY,
            RecordStatus.PENDING_LEGAL,
            UserRole.SECURITY,
        ) is True

        # 法务可以批准
        assert service.can_transition(
            RecordStatus.PENDING_LEGAL,
            RecordStatus.APPROVED,
            UserRole.LEGAL,
        ) is True

    def test_can_transition_invalid(self, db_session):
        """测试非法状态转换检测"""
        service = ApprovalFlowService(db_session)

        # 研发不能直接跳到法务审批
        assert service.can_transition(
            RecordStatus.DRAFT,
            RecordStatus.PENDING_LEGAL,
            UserRole.ENGINEER,
        ) is False

        # 研发不能审批自己的记录
        assert service.can_transition(
            RecordStatus.PENDING_SECURITY,
            RecordStatus.PENDING_LEGAL,
            UserRole.ENGINEER,
        ) is False

    def test_submit_for_review(self, db_session):
        """测试提交审批"""
        # 准备数据
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)

        service = ApprovalFlowService(db_session)
        result = service.submit_for_review(record, user)

        assert result.status == RecordStatus.PENDING_SECURITY
        assert result.filled_by == user.id
        assert result.submitted_at is not None

    def test_submit_for_review_invalid_status(self, db_session):
        """测试提交审批 - 非法状态"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,  # 不是草稿状态
        )
        db_session.add(record)

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ValidationError):
            service.submit_for_review(record, user)

    def test_legal_approve(self, db_session):
        """测试法务审批通过"""
        # 准备数据
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)

        service = ApprovalFlowService(db_session)
        result = service.legal_approve(record, user, approve=True, comments=" approved")

        assert result.status == RecordStatus.APPROVED
        assert result.approved_by_legal == user.id
        assert result.legal_approved_at is not None

    def test_legal_reject_requires_comments(self, db_session):
        """测试法务驳回必须填写原因"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ValidationError, match="驳回必须填写原因"):
            service.legal_approve(record, user, approve=False, comments=None)
