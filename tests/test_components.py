"""组件相关路由测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.user import User, UserRole


class TestComponentsEndpoints:
    """组件端点测试"""

    def test_list_components_empty(self, client: TestClient):
        """测试组件列表 - 空"""
        response = client.get("/api/components")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_components_with_data(self, db_session: Session, client: TestClient):
        """测试组件列表 - 有数据"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        response = client.get("/api/components")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "lodash"
        assert data[0]["version"] == "4.17.21"

    def test_list_components_pagination(self, db_session: Session, client: TestClient):
        """测试组件分页"""
        for i in range(25):
            component = Component(name=f"component-{i}", version="1.0.0", license="MIT")
            db_session.add(component)
        db_session.commit()

        response = client.get("/api/components?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

        response = client.get("/api/components?skip=10&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    def test_list_components_search(self, db_session: Session, client: TestClient):
        """测试组件搜索"""
        db_session.add(Component(name="lodash", version="4.17.21", license="MIT"))
        db_session.add(Component(name="react", version="18.2.0", license="MIT"))
        db_session.add(Component(name="react-dom", version="18.2.0", license="MIT"))
        db_session.commit()

        response = client.get("/api/components?search=react")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [c["name"] for c in data]
        assert "react" in names
        assert "react-dom" in names

    def test_list_components_search_case_insensitive(self, db_session: Session, client: TestClient):
        """测试组件搜索 - 大小写不敏感"""
        db_session.add(Component(name="React", version="18.2.0", license="MIT"))
        db_session.commit()

        response = client.get("/api/components?search=react")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_components_filter_by_license_risk(self, db_session: Session, client: TestClient):
        """测试按许可证风险过滤"""
        db_session.add(Component(name="safe-lib", version="1.0.0", license_risk_level="safe"))
        db_session.add(Component(name="warning-lib", version="1.0.0", license_risk_level="warning"))
        db_session.add(Component(name="caution-lib", version="1.0.0", license_risk_level="caution"))
        db_session.commit()

        response = client.get("/api/components?license_risk=safe")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "safe-lib"

    def test_get_component_success(self, db_session: Session, client: TestClient):
        """测试获取组件详情"""
        component = Component(name="express", version="4.18.2", license="MIT", copyright="Copyright TJ")
        db_session.add(component)
        db_session.commit()

        response = client.get(f"/api/components/{component.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == component.id
        assert data["name"] == "express"
        assert data["copyright"] == "Copyright TJ"

    def test_get_component_not_found(self, client: TestClient):
        """测试获取组件 - 不存在"""
        response = client.get("/api/components/999")
        assert response.status_code == 404
        assert "Component not found" in response.json()["detail"]

    def test_upload_blackduck_report(self, client: TestClient):
        """测试上传 Black Duck 报告（模拟数据）"""
        # BlackDuckReportUpload requires both report_id and system_name
        payload = {"report_id": "test-report-123", "system_name": "test-system"}
        response = client.post("/api/components/blackduck", json=payload)
        assert response.status_code == 200
        data = response.json()
        # 模拟数据返回 3 个组件
        assert len(data) >= 1

    def test_match_component_found(self, db_session: Session, client: TestClient):
        """测试组件匹配 - 找到"""
        component = Component(name="lodash", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        # Use POST instead of GET to avoid route conflict with /{component_id}
        response = client.post("/api/components/match", params={"name": "lodash", "version": "4.17.21"})
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["existing_component"]["name"] == "lodash"

    def test_match_component_not_found(self, db_session: Session, client: TestClient):
        """测试组件匹配 - 未找到"""
        # Use POST instead of GET to avoid route conflict with /{component_id}
        response = client.post("/api/components/match", params={"name": "nonexistent", "version": "1.0.0"})
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False
        assert data["existing_component"] is None

    def test_match_component_similar(self, db_session: Session, client: TestClient):
        """测试组件匹配 - 相似匹配"""
        db_session.add(Component(name="lodash", version="4.17.20", license="MIT"))
        db_session.add(Component(name="lodash", version="4.17.19", license="MIT"))
        db_session.commit()

        # Use POST instead of GET to avoid route conflict with /{component_id}
        response = client.post("/api/components/match", params={"name": "lodash", "version": "4.17.21"})
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False
        # Message should mention similar components found
        assert "2" in data["message"] and "同名" in data["message"]

    def test_update_component_success(self, db_session: Session, client: TestClient):
        """测试更新组件"""
        component = Component(name="express", version="4.18.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        # ComponentUpdate only has license, copyright, usage_type, license_risk_level
        payload = {"license": "Apache-2.0", "license_risk_level": "caution"}
        response = client.put(f"/api/components/{component.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["license"] == "Apache-2.0"
        assert data["license_risk_level"] == "caution"

    def test_update_component_not_found(self, client: TestClient):
        """测试更新组件 - 不存在"""
        payload = {"license": "MIT"}
        response = client.put("/api/components/999", json=payload)
        assert response.status_code == 404

    def test_update_component_partial(self, db_session: Session, client: TestClient):
        """测试部分更新组件"""
        component = Component(name="express", version="4.18.0", license="MIT", copyright="Original")
        db_session.add(component)
        db_session.commit()

        payload = {"copyright": "Updated"}
        response = client.put(f"/api/components/{component.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["copyright"] == "Updated"
        # 其他字段不变
        assert data["license"] == "MIT"


class TestComponentsLimitValidation:
    """组件端点限制验证测试"""

    def test_list_components_limit_max(self, client: TestClient):
        """测试最大限制"""
        response = client.get("/api/components?limit=100")
        assert response.status_code == 200

    def test_list_components_limit_exceeded(self, client: TestClient):
        """测试超过最大限制"""
        response = client.get("/api/components?limit=101")
        assert response.status_code == 422

    def test_list_components_limit_negative(self, client: TestClient):
        """测试负数限制"""
        response = client.get("/api/components?limit=-1")
        assert response.status_code == 422

    def test_list_components_skip_negative(self, client: TestClient):
        """测试负数跳过"""
        response = client.get("/api/components?skip=-1")
        assert response.status_code == 422
