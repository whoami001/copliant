"""合规记录相关路由测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole


class TestRecordsEndpoints:
    """合规记录端点测试"""

    def test_list_records_empty(self, client: TestClient):
        """测试合规记录列表 - 空"""
        response = client.get("/api/compliance-records")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_records_with_data(self, db_session: Session, client: TestClient):
        """测试合规记录列表 - 有数据"""
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

        response = client.get("/api/compliance-records")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["system_name"] == "test-system"

    def test_list_records_filter_by_status(self, db_session: Session, client: TestClient):
        """测试合规记录列表 - 按状态过滤"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record1 = ComplianceRecord(component_id=component.id, system_name="sys1", status=RecordStatus.DRAFT)
        record2 = ComplianceRecord(component_id=component.id, system_name="sys2", status=RecordStatus.APPROVED)
        db_session.add_all([record1, record2])
        db_session.commit()

        response = client.get("/api/compliance-records?status=draft")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "draft"

    def test_list_records_filter_by_system_name(self, db_session: Session, client: TestClient):
        """测试合规记录列表 - 按系统名过滤"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record1 = ComplianceRecord(component_id=component.id, system_name="order-system", status=RecordStatus.DRAFT)
        record2 = ComplianceRecord(component_id=component.id, system_name="payment-system", status=RecordStatus.DRAFT)
        db_session.add_all([record1, record2])
        db_session.commit()

        response = client.get("/api/compliance-records?system_name=order")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["system_name"] == "order-system"

    def test_create_record_success(self, db_session: Session, client: TestClient):
        """测试创建合规记录成功"""
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

    def test_create_record_component_not_found(self, client: TestClient):
        """测试创建合规记录 - 组件不存在"""
        payload = {
            "component_id": 999,
            "system_name": "order-system",
            "comments": "test comment",
        }
        response = client.post("/api/compliance-records", json=payload)
        assert response.status_code == 404
        assert "Component not found" in response.json()["detail"]

    def test_get_record_success(self, db_session: Session, client: TestClient):
        """测试获取合规记录成功"""
        component = Component(name="react", version="18.2.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test-system", status=RecordStatus.DRAFT)
        db_session.add(record)
        db_session.commit()

        response = client.get(f"/api/compliance-records/{record.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == record.id
        assert data["system_name"] == "test-system"

    def test_get_record_not_found(self, client: TestClient):
        """测试获取合规记录 - 不存在"""
        response = client.get("/api/compliance-records/999")
        assert response.status_code == 404
        assert "Record not found" in response.json()["detail"]

    def test_update_record_draft_status(self, db_session: Session, client: TestClient):
        """测试更新合规记录 - 草稿状态"""
        component = Component(name="react", version="18.2.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.DRAFT,
            comments="old comment",
        )
        db_session.add(record)
        db_session.commit()

        payload = {"comments": "new comment"}
        response = client.put(f"/api/compliance-records/{record.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["comments"] == "new comment"

    def test_update_record_non_draft_status(self, db_session: Session, client: TestClient):
        """测试更新合规记录 - 非草稿状态"""
        component = Component(name="react", version="18.2.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.APPROVED,
        )
        db_session.add(record)
        db_session.commit()

        payload = {"comments": "new comment"}
        response = client.put(f"/api/compliance-records/{record.id}", json=payload)
        assert response.status_code == 400
        assert "只有草稿状态" in response.json()["detail"]

    def test_submit_record_success(self, db_session: Session, client: TestClient):
        """测试提交合规记录成功"""
        component = Component(name="axios", version="1.4.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(component_id=component.id, system_name="test-system", status=RecordStatus.DRAFT)
        db_session.add(record)
        db_session.commit()

        payload = {}
        response = client.post(f"/api/compliance-records/{record.id}/submit", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_security"

    def test_submit_record_not_found(self, client: TestClient):
        """测试提交合规记录 - 不存在"""
        payload = {}
        response = client.post("/api/compliance-records/999/submit", json=payload)
        assert response.status_code == 404

    def test_approve_record_pending_security(self, db_session: Session, client: TestClient):
        """测试审批通过 - 安全校验状态"""
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

        payload = {"comments": "approved"}
        response = client.post(f"/api/compliance-records/{record.id}/approve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_legal"

    def test_approve_record_pending_legal(self, db_session: Session, client: TestClient):
        """测试审批通过 - 法务审批状态"""
        component = Component(name="axios", version="1.4.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        payload = {"comments": "approved"}
        response = client.post(f"/api/compliance-records/{record.id}/approve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_reject_record_success(self, db_session: Session, client: TestClient):
        """测试驳回合规记录"""
        component = Component(name="axios", version="1.4.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        payload = {"comments": "license issue"}
        response = client.post(f"/api/compliance-records/{record.id}/reject", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_request_changes_success(self, db_session: Session, client: TestClient):
        """测试要求修改"""
        component = Component(name="axios", version="1.4.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
        )
        db_session.add(record)
        db_session.commit()

        payload = {"comments": "need to update license"}
        response = client.post(f"/api/compliance-records/{record.id}/request-changes", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"


class TestRecordsPagination:
    """合规记录分页测试"""

    def test_list_records_pagination(self, db_session: Session, client: TestClient):
        """测试分页获取合规记录"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        # 创建 25 条记录
        for i in range(25):
            record = ComplianceRecord(
                component_id=component.id,
                system_name=f"system-{i}",
                status=RecordStatus.DRAFT,
            )
            db_session.add(record)
        db_session.commit()

        # 获取第一页
        response = client.get("/api/compliance-records?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

        # 获取第二页
        response = client.get("/api/compliance-records?skip=10&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    def test_list_records_limit_validation(self, client: TestClient):
        """测试分页限制验证"""
        # 超过最大限制
        response = client.get("/api/compliance-records?limit=101")
        assert response.status_code == 422

        # 负数
        response = client.get("/api/compliance-records?skip=-1")
        assert response.status_code == 422
