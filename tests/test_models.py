"""模型测试"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.models.approval_history import ApprovalHistory


class TestComponentModel:
    """组件模型测试"""

    def test_create_component(self, db_session: Session):
        """测试创建组件"""
        component = Component(
            name="lodash",
            version="4.17.21",
            license="MIT",
        )
        db_session.add(component)
        db_session.commit()

        assert component.id is not None
        assert component.name == "lodash"
        assert component.version == "4.17.21"
        assert component.license == "MIT"

    def test_component_full_name(self, db_session: Session):
        """测试组件全名属性"""
        component = Component(name="express", version="4.18.2", license="MIT")
        db_session.add(component)
        db_session.commit()

        assert component.full_name == "express@4.18.2"

    def test_component_default_values(self, db_session: Session):
        """测试组件默认值"""
        component = Component(name="test-lib", version="1.0.0")
        db_session.add(component)
        db_session.commit()

        assert component.usage_type is None
        assert component.license_risk_level == "unknown"
        assert component.is_approved is False
        assert component.black_duck_report_id is None

    def test_component_unique_constraint(self, db_session: Session):
        """测试组件唯一约束"""
        component1 = Component(name="lodash", version="4.17.21", license="MIT")
        component2 = Component(name="lodash", version="4.17.21", license="Apache-2.0")

        db_session.add(component1)
        db_session.commit()

        # 尝试添加同名同版本的组件应该失败
        db_session.add(component2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_component_relationship_with_records(self, db_session: Session):
        """测试组件与合规记录的关联"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test-system")
        db_session.add(record)
        db_session.commit()

        assert len(component.compliance_records) == 1
        assert component.compliance_records[0].id == record.id

    def test_component_repr(self, db_session: Session):
        """测试组件字符串表示"""
        component = Component(name="react", version="18.2.0")
        db_session.add(component)
        db_session.commit()

        assert "react" in repr(component)
        assert "18.2.0" in repr(component)


class TestComplianceRecordModel:
    """合规记录模型测试"""

    def test_create_record(self, db_session: Session):
        """测试创建合规记录"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.DRAFT,
        )
        db_session.add(record)
        db_session.commit()

        assert record.id is not None
        assert record.status == RecordStatus.DRAFT
        assert record.created_at is not None

    def test_record_default_status(self, db_session: Session):
        """测试记录默认状态"""
        component = Component(name="test", version="1.0.0")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test")
        db_session.add(record)
        db_session.commit()

        assert record.status == RecordStatus.DRAFT

    def test_record_status_transitions(self, db_session: Session):
        """测试记录状态转换"""
        component = Component(name="test", version="1.0.0")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test", status=RecordStatus.DRAFT)
        db_session.add(record)
        db_session.commit()

        # 模拟状态转换
        record.status = RecordStatus.PENDING_SECURITY
        db_session.commit()
        assert record.status == RecordStatus.PENDING_SECURITY

        record.status = RecordStatus.PENDING_LEGAL
        db_session.commit()
        assert record.status == RecordStatus.PENDING_LEGAL

        record.status = RecordStatus.APPROVED
        db_session.commit()
        assert record.status == RecordStatus.APPROVED

    def test_record_timestamps(self, db_session: Session):
        """测试记录时间戳"""
        component = Component(name="test", version="1.0.0")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test")
        db_session.add(record)
        db_session.commit()

        assert record.created_at is not None
        assert record.updated_at is not None
        assert record.created_at <= record.updated_at

    def test_record_repr(self, db_session: Session):
        """测试记录字符串表示"""
        component = Component(name="test", version="1.0.0")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test")
        db_session.add(record)
        db_session.commit()

        assert str(record.id) in repr(record)
        assert str(component.id) in repr(record)


class TestUserModel:
    """用户模型测试"""

    def test_create_user(self, db_session: Session):
        """测试创建用户"""
        user = User(email="test@example.com", name="Test User", role=UserRole.ENGINEER)
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == UserRole.ENGINEER
        assert user.is_active is True

    def test_user_default_role(self, db_session: Session):
        """测试用户默认角色"""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        assert user.role == UserRole.ENGINEER

    def test_user_default_active(self, db_session: Session):
        """测试用户默认激活状态"""
        user = User(email="test@example.com")
        db_session.add(user)
        db_session.commit()

        assert user.is_active is True

    def test_user_roles(self, db_session: Session):
        """测试用户角色枚举"""
        roles = [UserRole.ENGINEER, UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN]

        for role in roles:
            user = User(email=f"{role.value}@test.com", role=role)
            db_session.add(user)
            db_session.commit()
            assert user.role == role

    def test_user_repr(self, db_session: Session):
        """测试用户字符串表示"""
        user = User(email="test@example.com", role=UserRole.ENGINEER)
        db_session.add(user)
        db_session.commit()

        assert user.email in repr(user)
        # The repr shows UserRole.ENGINEER, not just 'engineer'
        assert "ENGINEER" in repr(user)


class TestApprovalHistoryModel:
    """审批历史模型测试"""

    def test_create_history(self, db_session: Session):
        """测试创建审批历史"""
        component = Component(name="test", version="1.0.0")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test")
        db_session.add(record)
        db_session.commit()

        user = User(email="test@example.com", role=UserRole.ENGINEER)
        db_session.add(user)
        db_session.commit()

        history = ApprovalHistory(
            record_id=record.id,
            action="submit",
            actor=user.id,
            role="engineer",
            previous_status="draft",
            new_status="pending_security",
        )
        db_session.add(history)
        db_session.commit()

        assert history.id is not None
        assert history.action == "submit"
        assert history.created_at is not None

    def test_history_actions(self, db_session: Session):
        """测试审批历史动作类型"""
        actions = ["submit", "approve", "reject", "request_changes"]

        for action in actions:
            history = ApprovalHistory(
                record_id=1,
                action=action,
                actor=1,
                role="engineer",
                previous_status="draft",
                new_status="pending_security",
            )
            assert history.action == action

    def test_history_comments_optional(self, db_session: Session):
        """测试审批历史评论可选"""
        history = ApprovalHistory(
            record_id=1,
            action="submit",
            actor=1,
            role="engineer",
            previous_status="draft",
            new_status="pending_security",
        )
        db_session.add(history)
        db_session.commit()

        assert history.comments is None

    def test_history_repr(self, db_session: Session):
        """测试审批历史字符串表示"""
        history = ApprovalHistory(
            record_id=123,
            action="approve",
            actor=1,
            role="legal",
            previous_status="pending_legal",
            new_status="approved",
        )
        assert "123" in repr(history)
        assert "approve" in repr(history)
