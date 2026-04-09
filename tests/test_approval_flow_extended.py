"""审批流服务测试（补充）"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from app.services.approval_flow import ApprovalFlowService, VALID_TRANSITIONS
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.models.approval_history import ApprovalHistory
from app.exceptions import InvalidStatusTransitionError, ForbiddenError, ValidationError


class TestApprovalFlowServiceTransitions:
    """审批流状态转换测试"""

    def test_all_valid_transitions_defined(self):
        """测试所有合法状态转换已定义"""
        expected_transitions = [
            (RecordStatus.DRAFT, RecordStatus.PENDING_SECURITY),
            (RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL),
            (RecordStatus.PENDING_SECURITY, RecordStatus.DRAFT),
            (RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED),
            (RecordStatus.PENDING_LEGAL, RecordStatus.DRAFT),
            (RecordStatus.PENDING_LEGAL, RecordStatus.REJECTED),
        ]

        for transition in expected_transitions:
            assert transition in VALID_TRANSITIONS

    def test_can_transition_all_roles(self, db_session):
        """测试所有角色的状态转换权限"""
        service = ApprovalFlowService(db_session)

        # ENGINEER: DRAFT -> PENDING_SECURITY
        assert service.can_transition(RecordStatus.DRAFT, RecordStatus.PENDING_SECURITY, UserRole.ENGINEER) is True

        # SECURITY: PENDING_SECURITY -> PENDING_LEGAL
        assert service.can_transition(RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL, UserRole.SECURITY) is True
        assert service.can_transition(RecordStatus.PENDING_SECURITY, RecordStatus.DRAFT, UserRole.SECURITY) is True

        # LEGAL: PENDING_LEGAL -> APPROVED/DRAFT/REJECTED
        assert service.can_transition(RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED, UserRole.LEGAL) is True
        assert service.can_transition(RecordStatus.PENDING_LEGAL, RecordStatus.DRAFT, UserRole.LEGAL) is True
        assert service.can_transition(RecordStatus.PENDING_LEGAL, RecordStatus.REJECTED, UserRole.LEGAL) is True

    def test_cannot_transition_wrong_role(self, db_session):
        """测试角色权限校验"""
        service = ApprovalFlowService(db_session)

        # ENGINEER 不能执行 SECURITY 的操作
        assert service.can_transition(RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL, UserRole.ENGINEER) is False

        # ENGINEER 不能执行 LEGAL 的操作
        assert service.can_transition(RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED, UserRole.ENGINEER) is False

        # SECURITY 不能执行 LEGAL 的操作
        assert service.can_transition(RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED, UserRole.SECURITY) is False

        # ADMIN 没有明确权限（不在 VALID_TRANSITIONS 中）
        assert service.can_transition(RecordStatus.DRAFT, RecordStatus.PENDING_SECURITY, UserRole.ADMIN) is False

    def test_undefined_transition(self, db_session):
        """测试未定义的状态转换"""
        service = ApprovalFlowService(db_session)

        # 未定义的转换应该返回 False
        assert service.can_transition(RecordStatus.DRAFT, RecordStatus.APPROVED, UserRole.ENGINEER) is False
        assert service.can_transition(RecordStatus.APPROVED, RecordStatus.DRAFT, UserRole.LEGAL) is False


class TestApprovalFlowServiceSubmit:
    """提交审批测试"""

    def test_submit_for_review_success(self, db_session):
        """测试提交审批成功"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)
        db_session.add(user)
        db_session.commit()

        service = ApprovalFlowService(db_session)
        result = service.submit_for_review(record, user)

        assert result.status == RecordStatus.PENDING_SECURITY
        assert result.filled_by == user.id
        assert result.submitted_at is not None

    def test_submit_for_review_admin(self, db_session):
        """测试管理员提交审批"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="admin@test.com", role=UserRole.ADMIN)

        service = ApprovalFlowService(db_session)
        result = service.submit_for_review(record, user)

        assert result.status == RecordStatus.PENDING_SECURITY

    def test_submit_for_review_invalid_status(self, db_session):
        """测试提交审批 - 非法状态"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ValidationError, match="只有草稿状态"):
            service.submit_for_review(record, user)

    def test_submit_for_review_wrong_role(self, db_session):
        """测试提交审批 - 错误角色"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="security@test.com", role=UserRole.SECURITY)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ForbiddenError, match="只有研发"):
            service.submit_for_review(record, user)


class TestApprovalFlowServiceSecurityReview:
    """安全校验测试"""

    def test_security_review_pass(self, db_session):
        """测试安全校验通过"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="security@test.com", role=UserRole.SECURITY)

        service = ApprovalFlowService(db_session)
        result = service.security_review(record, user, pass_review=True)

        assert result.status == RecordStatus.PENDING_LEGAL
        assert result.reviewed_by_security == user.id
        assert result.security_reviewed_at is not None

    def test_security_review_fail(self, db_session):
        """测试安全校验驳回"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="security@test.com", role=UserRole.SECURITY)

        service = ApprovalFlowService(db_session)
        result = service.security_review(record, user, pass_review=False, comments="security issue")

        assert result.status == RecordStatus.DRAFT
        assert result.comments == "security issue"

    def test_security_review_wrong_status(self, db_session):
        """测试安全校验 - 错误状态"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="security@test.com", role=UserRole.SECURITY)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ValidationError, match="不在安全校验状态"):
            service.security_review(record, user, pass_review=True)

    def test_security_review_wrong_role(self, db_session):
        """测试安全校验 - 错误角色"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ForbiddenError, match="只有安全角色"):
            service.security_review(record, user, pass_review=True)


class TestApprovalFlowServiceLegalApprove:
    """法务审批测试"""

    def test_legal_approve_success(self, db_session):
        """测试法务审批通过"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)

        service = ApprovalFlowService(db_session)
        result = service.legal_approve(record, user, approve=True)

        assert result.status == RecordStatus.APPROVED
        assert result.approved_by_legal == user.id
        assert result.legal_approved_at is not None

    def test_legal_reject_success(self, db_session):
        """测试法务驳回"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)

        service = ApprovalFlowService(db_session)
        result = service.legal_approve(record, user, approve=False, comments="license issue")

        assert result.status == RecordStatus.REJECTED
        assert result.comments == "license issue"

    def test_legal_reject_no_comments(self, db_session):
        """测试法务驳回必须填写原因"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ValidationError, match="驳回必须填写原因"):
            service.legal_approve(record, user, approve=False, comments=None)

        with pytest.raises(ValidationError, match="驳回必须填写原因"):
            service.legal_approve(record, user, approve=False, comments="")

    def test_legal_approve_wrong_status(self, db_session):
        """测试法务审批 - 错误状态"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ValidationError, match="不在法务审批状态"):
            service.legal_approve(record, user, approve=True)

    def test_legal_approve_wrong_role(self, db_session):
        """测试法务审批 - 错误角色"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ForbiddenError, match="只有法务角色"):
            service.legal_approve(record, user, approve=True)


class TestApprovalFlowServiceRequestChanges:
    """要求修改测试"""

    def test_request_changes_success(self, db_session):
        """测试要求修改成功"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)

        service = ApprovalFlowService(db_session)
        result = service.request_changes(record, user, comments="need more info")

        assert result.status == RecordStatus.DRAFT
        assert result.comments == "need more info"

    def test_request_changes_wrong_status(self, db_session):
        """测试要求修改 - 错误状态"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="legal@test.com", role=UserRole.LEGAL)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ValidationError, match="不在法务审批状态"):
            service.request_changes(record, user, comments="test")

    def test_request_changes_wrong_role(self, db_session):
        """测试要求修改 - 错误角色"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)
        service = ApprovalFlowService(db_session)

        with pytest.raises(ForbiddenError, match="只有法务角色"):
            service.request_changes(record, user, comments="test")


class TestApprovalFlowServiceHistory:
    """审批历史测试"""

    def test_add_history(self, db_session):
        """测试添加审批历史"""
        record = ComplianceRecord(
            component_id=1,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="engineer@test.com", role=UserRole.ENGINEER)
        db_session.add(user)
        db_session.commit()

        service = ApprovalFlowService(db_session)
        service._add_history(
            record,
            user,
            "submit",
            RecordStatus.DRAFT,
            RecordStatus.PENDING_SECURITY,
            "test comment",
        )

        db_session.commit()

        history = db_session.query(ApprovalHistory).filter_by(record_id=record.id).first()
        assert history is not None
        assert history.action == "submit"
        assert history.actor == user.id
        assert history.role == "engineer"
        assert history.previous_status == "draft"
        assert history.new_status == "pending_security"
        assert history.comments == "test comment"
