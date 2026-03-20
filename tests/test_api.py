"""API 端点测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self, client: TestClient):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestComponentsEndpoint:
    """组件端点测试"""

    def test_list_components_empty(self, client: TestClient):
        """测试组件列表 - 空"""
        response = client.get("/api/components")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_components_with_data(self, db_session: Session, client: TestClient):
        """测试组件列表 - 有数据"""
        # 准备数据
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        response = client.get("/api/components")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "lodash"

    def test_create_component_via_blackduck(self, client: TestClient):
        """测试通过 Black Duck 创建组件（使用模拟数据）"""
        payload = {
            "report_id": "test-report-123",
            "system_name": "test-system",
        }
        response = client.post("/api/components/blackduck", json=payload)
        assert response.status_code == 200
        data = response.json()
        # 模拟数据有 3 个组件
        assert len(data) >= 1


class TestRecordsEndpoint:
    """合规记录端点测试"""

    def test_list_records_empty(self, client: TestClient):
        """测试合规记录列表 - 空"""
        response = client.get("/api/compliance-records")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_record(self, db_session: Session, client: TestClient):
        """测试创建合规记录"""
        # 准备组件
        component = Component(name="express", version="4.18.2", license="MIT")
        db_session.add(component)
        db_session.commit()

        payload = {
            "component_id": component.id,
            "system_name": "order-system",
            "comments": "test comment",
        }
        response = client.post("/api/compliance-records", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["component_id"] == component.id
        assert data["system_name"] == "order-system"
        assert data["status"] == "draft"


class TestDashboardEndpoint:
    """仪表板端点测试"""

    def test_get_todo_empty(self, client: TestClient):
        """测试待办事项 - 空"""
        response = client.get("/api/dashboard/todo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_get_stats(self, client: TestClient):
        """测试统计信息"""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pending_my_action" in data
        assert "approved_this_month" in data
        assert "avg_processing_days" in data
        assert "total_records" in data
