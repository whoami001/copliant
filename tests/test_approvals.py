"""审批历史路由测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.models.approval_history import ApprovalHistory


class TestApprovalsEndpoints:
    """审批历史端点测试"""

    def test_get_approval_history_empty(self, db_session: Session, client: TestClient):
        """测试获取空审批历史"""
        response = client.get("/api/approvals/1/history")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_approval_history_with_data(self, db_session: Session, client: TestClient):
        """测试获取审批历史 - 有数据"""
        # 创建记录
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

        # 创建用户
        user = User(id=1, email="test@test.com", role=UserRole.ENGINEER, name="Test User")
        db_session.add(user)
        db_session.commit()

        # 创建审批历史
        history = ApprovalHistory(
            record_id=record.id,
            action="submit",
            actor=user.id,
            role="engineer",
            previous_status="draft",
            new_status="pending_security",
            comments="submitted for review",
        )
        db_session.add(history)
        db_session.commit()

        response = client.get(f"/api/approvals/{record.id}/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["action"] == "submit"
        assert data[0]["actor_name"] == "Test User"
        assert data[0]["role"] == "engineer"

    def test_get_approval_history_multiple(self, db_session: Session, client: TestClient):
        """测试获取多条审批历史"""
        from datetime import datetime

        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test-system", status=RecordStatus.DRAFT)
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="test@test.com", role=UserRole.ENGINEER, name="Test User")
        db_session.add(user)
        db_session.commit()

        # 创建多条历史记录 - use datetime objects, not strings
        histories = [
            ApprovalHistory(record_id=record.id, action="submit", actor=user.id, role="engineer", previous_status="draft", new_status="pending_security", created_at=datetime(2026, 3, 18, 10, 0, 0)),
            ApprovalHistory(record_id=record.id, action="approve", actor=user.id, role="security", previous_status="pending_security", new_status="pending_legal", created_at=datetime(2026, 3, 18, 11, 0, 0)),
            ApprovalHistory(record_id=record.id, action="approve", actor=user.id, role="legal", previous_status="pending_legal", new_status="approved", created_at=datetime(2026, 3, 18, 12, 0, 0)),
        ]
        db_session.add_all(histories)
        db_session.commit()

        response = client.get(f"/api/approvals/{record.id}/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # 应该按时间倒序
        assert data[0]["action"] == "approve"  # 最新的在前

    def test_get_approval_history_record_not_found(self, db_session: Session, client: TestClient):
        """测试获取不存在的记录的审批历史"""
        # 记录不存在，但端点可能仍然返回空列表
        response = client.get("/api/approvals/999/history")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_approval_history_ordering(self, db_session: Session, client: TestClient):
        """测试审批历史排序"""
        from datetime import datetime, timedelta

        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test-system", status=RecordStatus.DRAFT)
        db_session.add(record)
        db_session.commit()

        user = User(id=1, email="test@test.com", role=UserRole.ENGINEER)
        db_session.add(user)
        db_session.commit()

        # 创建不同时间的历史记录 - use valid action enum values
        actions = ["submit", "approve", "approve", "submit", "approve"]
        base_time = datetime(2026, 3, 18, 10, 0, 0)
        for i in range(5):
            history = ApprovalHistory(
                record_id=record.id,
                action=actions[i],
                actor=user.id,
                role="engineer",
                previous_status="draft",
                new_status="pending_security",
                created_at=base_time + timedelta(hours=i),
            )
            db_session.add(history)
        db_session.commit()

        response = client.get(f"/api/approvals/{record.id}/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        # 验证倒序：最新的在最后添加，应该在列表前面
        assert data[0]["action"] == "approve"
        # The last one (earliest) should be submit (i=0)
        assert data[-1]["action"] == "submit"
