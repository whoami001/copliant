"""仪表板相关路由测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus
from datetime import datetime


class TestDashboardEndpoints:
    """仪表板端点测试"""

    def test_get_todo_empty(self, client: TestClient):
        """测试获取待办事项 - 空"""
        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_get_todo_with_pending_security(self, db_session: Session, client: TestClient):
        """测试获取待办事项 - 安全待处理"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
        )
        db_session.add(record)
        db_session.commit()

        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "pending_security"
        assert data["items"][0]["requires_action"] is True

    def test_get_todo_with_pending_legal(self, db_session: Session, client: TestClient):
        """测试获取待办事项 - 法务待处理"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending_legal"

    def test_get_todo_excludes_approved(self, db_session: Session, client: TestClient):
        """测试待办事项排除已通过记录"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        approved = ComplianceRecord(component_id=component.id, system_name="approved-sys", status=RecordStatus.APPROVED)
        rejected = ComplianceRecord(component_id=component.id, system_name="rejected-sys", status=RecordStatus.REJECTED)
        db_session.add_all([approved, rejected])
        db_session.commit()

        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_get_todo_excludes_draft(self, db_session: Session, client: TestClient):
        """测试待办事项排除草稿"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        draft = ComplianceRecord(component_id=component.id, system_name="draft-sys", status=RecordStatus.DRAFT)
        db_session.add(draft)
        db_session.commit()

        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_todo_multiple_items(self, db_session: Session, client: TestClient):
        """测试获取多个待办事项"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        for i in range(5):
            record = ComplianceRecord(
                component_id=component.id,
                system_name=f"system-{i}",
                status=RecordStatus.PENDING_SECURITY if i % 2 == 0 else RecordStatus.PENDING_LEGAL,
            )
            db_session.add(record)
        db_session.commit()

        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_get_stats_empty(self, client: TestClient):
        """测试获取统计信息 - 空"""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pending_my_action" in data
        assert "approved_this_month" in data
        assert "avg_processing_days" in data
        assert "total_records" in data
        assert data["pending_my_action"] == 0
        assert data["total_records"] == 0

    def test_get_stats_with_data(self, db_session: Session, client: TestClient):
        """测试获取统计信息 - 有数据"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        # 创建各种状态的记录
        pending_security = ComplianceRecord(component_id=component.id, system_name="sys1", status=RecordStatus.PENDING_SECURITY)
        pending_legal = ComplianceRecord(component_id=component.id, system_name="sys2", status=RecordStatus.PENDING_LEGAL)
        approved = ComplianceRecord(component_id=component.id, system_name="sys3", status=RecordStatus.APPROVED)
        draft = ComplianceRecord(component_id=component.id, system_name="sys4", status=RecordStatus.DRAFT)

        db_session.add_all([pending_security, pending_legal, approved, draft])
        db_session.commit()

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["pending_my_action"] == 2  # pending_security + pending_legal
        assert data["total_records"] == 4

    def test_get_stats_approved_this_month(self, db_session: Session, client: TestClient):
        """测试获取本月通过的统计"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        # 创建本月通过的记录
        now = datetime.utcnow()
        approved = ComplianceRecord(
            component_id=component.id,
            system_name="sys1",
            status=RecordStatus.APPROVED,
            legal_approved_at=now,
        )
        db_session.add(approved)
        db_session.commit()

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["approved_this_month"] >= 1

    def test_get_stats_avg_days_fixed(self, client: TestClient):
        """测试平均处理时间是固定值（MVP 实现）"""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        # MVP 版本固定为 2.3 天
        assert data["avg_processing_days"] == 2.3

    def test_todo_item_structure(self, db_session: Session, client: TestClient):
        """测试待办事项数据结构"""
        component = Component(name="axios", version="1.4.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
        )
        db_session.add(record)
        db_session.commit()

        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()

        item = data["items"][0]
        assert "id" in item
        assert "record_name" in item
        assert "system_name" in item
        assert "status" in item
        assert "requires_action" in item
        assert item["requires_action"] is True
        # record_name 应该包含组件名和版本
        assert "axios" in item["record_name"].lower()
        assert "1.4.0" in item["record_name"]
