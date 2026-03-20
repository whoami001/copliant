"""Schema 验证测试"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.auth import EmailLoginRequest, Token
from app.schemas.user import UserResponse, UserCreate
from app.schemas.component import (
    ComponentCreate,
    ComponentResponse,
    ComponentUpdate,
    ComponentMatchResponse,
    BlackDuckReportUpload,
)
from app.schemas.compliance_record import (
    ComplianceRecordCreate,
    ComplianceRecordResponse,
    ComplianceRecordUpdate,
    ComplianceRecordSubmit,
    ComplianceRecordApprove,
    ComplianceRecordReject,
    RecordStatusEnum,
)
from app.schemas.approval import ApprovalHistoryResponse
from app.schemas.dashboard import DashboardTodoResponse, DashboardTodoItem, DashboardStatsResponse
from app.models.user import UserRole
from app.models.compliance_record import RecordStatus


class TestAuthSchemas:
    """认证 Schema 测试"""

    def test_email_login_request_valid(self):
        """测试邮箱登录请求 - 有效"""
        request = EmailLoginRequest(email="test@example.com", code="123456")
        assert request.email == "test@example.com"
        assert request.code == "123456"

    def test_email_login_request_empty_email(self):
        """测试邮箱登录请求 - 空邮箱"""
        with pytest.raises(ValidationError):
            EmailLoginRequest(email="", code="123456")

    def test_email_login_request_short_code(self):
        """测试邮箱登录请求 - 短验证码"""
        request = EmailLoginRequest(email="test@example.com", code="1")
        assert request.code == "1"

    def test_token_valid(self):
        """测试 Token - 有效"""
        token = Token(access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", token_type="bearer")
        assert token.access_token is not None
        assert token.token_type == "bearer"


class TestUserSchemas:
    """用户 Schema 测试"""

    def test_user_response_valid(self):
        """测试用户响应 - 有效"""
        user = UserResponse(
            id=1,
            email="test@example.com",
            name="Test User",
            role="engineer",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        assert user.id == 1
        assert user.role == "engineer"

    def test_user_response_all_roles(self):
        """测试用户响应 - 所有角色"""
        roles = ["engineer", "security", "legal", "admin"]
        for role in roles:
            user = UserResponse(
                id=1,
                email="test@example.com",
                role=role,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            assert user.role == role

    def test_user_create_valid(self):
        """测试创建用户 - 有效"""
        user = UserCreate(email="test@example.com", name="Test User")
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_user_create_no_name(self):
        """测试创建用户 - 无名字"""
        user = UserCreate(email="test@example.com")
        assert user.name is None or user.name == ""


class TestComponentSchemas:
    """组件 Schema 测试"""

    def test_component_create_valid(self):
        """测试创建组件 - 有效"""
        component = ComponentCreate(name="lodash", version="4.17.21", license="MIT")
        assert component.name == "lodash"
        assert component.version == "4.17.21"

    def test_component_create_minimal(self):
        """测试创建组件 - 最小化"""
        component = ComponentCreate(name="test-lib", version="1.0.0")
        assert component.name == "test-lib"
        assert component.version == "1.0.0"
        assert component.license is None

    def test_component_response_valid(self):
        """测试组件响应 - 有效"""
        component = ComponentResponse(
            id=1,
            name="lodash",
            version="4.17.21",
            license="MIT",
            usage_type="direct",
            license_risk_level="safe",
            is_approved=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=None,
        )
        assert component.id == 1
        assert component.name == "lodash"
        # ComponentResponse 没有 full_name 属性，这是 Model 的属性

    def test_component_update_valid(self):
        """测试更新组件 - 有效"""
        update = ComponentUpdate(license="Apache-2.0", license_risk_level="safe")
        assert update.license == "Apache-2.0"
        assert update.license_risk_level == "safe"

    def test_component_update_partial(self):
        """测试更新组件 - 部分字段"""
        update = ComponentUpdate(license_risk_level="safe")
        assert update.license is None
        assert update.license_risk_level == "safe"

    def test_blackduck_report_upload_valid(self):
        """测试 Black Duck 报告上传 - 有效"""
        # BlackDuckReportUpload 需要 report_id 和 system_name
        report = BlackDuckReportUpload(report_id="test-123", system_name="test-system")
        assert report.report_id == "test-123"
        assert report.system_name == "test-system"

    def test_component_match_response_matched(self):
        """测试组件匹配响应 - 匹配"""
        existing = ComponentResponse(
            id=1,
            name="lodash",
            version="4.17.21",
            license="MIT",
            license_risk_level="safe",
            is_approved=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=None,
        )
        response = ComponentMatchResponse(
            matched=True,
            existing_component=existing,
            message="找到历史合规结论",
        )
        assert response.matched is True
        assert response.existing_component is not None

    def test_component_match_response_not_matched(self):
        """测试组件匹配响应 - 未匹配"""
        response = ComponentMatchResponse(
            matched=False,
            existing_component=None,
            message="未找到匹配",
        )
        assert response.matched is False
        assert response.existing_component is None


class TestComplianceRecordSchemas:
    """合规记录 Schema 测试"""

    def test_record_status_enum(self):
        """测试记录状态枚举"""
        statuses = ["draft", "pending_security", "pending_legal", "approved", "rejected"]
        for status in statuses:
            s = RecordStatusEnum(status)
            assert s.value == status

    def test_record_create_valid(self):
        """测试创建记录 - 有效"""
        record = ComplianceRecordCreate(component_id=1, system_name="test-system", comments="test")
        assert record.component_id == 1
        assert record.system_name == "test-system"

    def test_record_create_minimal(self):
        """测试创建记录 - 最小化"""
        record = ComplianceRecordCreate(component_id=1, system_name="test-system")
        assert record.component_id == 1
        assert record.system_name == "test-system"
        assert record.comments is None

    def test_record_update_valid(self):
        """测试更新记录 - 有效"""
        update = ComplianceRecordUpdate(comments="new comments")
        assert update.comments == "new comments"

    def test_record_submit_valid(self):
        """测试提交记录 - 有效"""
        submit = ComplianceRecordSubmit()
        assert submit is not None

    def test_record_approve_valid(self):
        """测试审批通过 - 有效"""
        approve = ComplianceRecordApprove(comments="approved")
        assert approve.comments == "approved"

    def test_record_approve_no_comments(self):
        """测试审批通过 - 无评论"""
        approve = ComplianceRecordApprove()
        assert approve.comments is None

    def test_record_reject_valid(self):
        """测试审批驳回 - 有效"""
        reject = ComplianceRecordReject(comments="license issue")
        assert reject.comments == "license issue"

    def test_record_reject_empty_comments(self):
        """测试审批驳回 - 空评论（Pydantic 允许空字符串）"""
        # Pydantic v2 allows empty string for str type without Field validation
        reject = ComplianceRecordReject(comments="")
        assert reject.comments == ""

    def test_record_response_valid(self):
        """测试记录响应 - 有效"""
        record = ComplianceRecordResponse(
            id=1,
            component_id=1,
            system_name="test-system",
            status=RecordStatusEnum.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert record.id == 1
        assert record.status == RecordStatusEnum.DRAFT


class TestApprovalSchemas:
    """审批 Schema 测试"""

    def test_approval_history_response_valid(self):
        """测试审批历史响应 - 有效"""
        history = ApprovalHistoryResponse(
            id=1,
            record_id=1,
            action="submit",
            actor=1,
            role="engineer",
            previous_status="draft",
            new_status="pending_security",
            created_at=datetime.utcnow(),
        )
        assert history.id == 1
        assert history.action == "submit"


class TestDashboardSchemas:
    """仪表板 Schema 测试"""

    def test_todo_item_valid(self):
        """测试待办事项 - 有效"""
        item = DashboardTodoItem(
            id=1,
            record_name="lodash@4.17.21",
            system_name="test-system",
            status="pending_security",
            requires_action=True,
        )
        assert item.id == 1
        assert item.requires_action is True

    def test_todo_response_valid(self):
        """测试待办事项响应 - 有效"""
        items = [
            DashboardTodoItem(id=1, record_name="lib@1.0", system_name="sys1", status="pending_security", requires_action=True),
            DashboardTodoItem(id=2, record_name="lib@2.0", system_name="sys2", status="pending_legal", requires_action=True),
        ]
        response = DashboardTodoResponse(items=items, total=2)
        assert response.total == 2
        assert len(response.items) == 2

    def test_stats_response_valid(self):
        """测试统计响应 - 有效"""
        stats = DashboardStatsResponse(
            pending_my_action=5,
            approved_this_month=10,
            avg_processing_days=2.3,
            total_records=100,
        )
        assert stats.pending_my_action == 5
        assert stats.avg_processing_days == 2.3

    def test_stats_response_zero_values(self):
        """测试统计响应 - 零值"""
        stats = DashboardStatsResponse(
            pending_my_action=0,
            approved_this_month=0,
            avg_processing_days=0.0,
            total_records=0,
        )
        assert stats.pending_my_action == 0
        assert stats.total_records == 0
