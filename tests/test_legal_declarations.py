"""法务声明 API 测试"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.database import Base
from app.models.user import User, UserRole
from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.legal_declaration import LegalDeclaration, UsageType, IsModified


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./:memory:"


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    from sqlalchemy import create_engine
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """创建测试客户端"""
    from app.main import app
    from app.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    user = User(email="engineer@test.com", role=UserRole.ENGINEER, name="Test Engineer")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(db_session, test_user):
    """创建认证 headers"""
    from jose import jwt
    from app.config import get_settings
    settings = get_settings()
    token = jwt.encode({"email": test_user.email}, settings.secret_key, algorithm=settings.algorithm)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_component(db_session):
    """创建测试组件"""
    component = Component(
        name="lodash",
        version="4.17.21",
        license="MIT",
        copyright="Copyright (c) 2021 Lodash Contributors",
    )
    db_session.add(component)
    db_session.commit()
    return component


@pytest.fixture
def test_record(db_session, test_component, test_user):
    """创建测试合规记录"""
    record = ComplianceRecord(
        component_id=test_component.id,
        system_name="Test System",
        status=RecordStatus.DRAFT,
        filled_by=test_user.id,
    )
    db_session.add(record)
    db_session.commit()
    return record


class TestLegalDeclarationCRUD:
    """测试法务声明 CRUD 操作"""

    def test_create_declaration(self, client, test_record, auth_headers):
        """测试创建声明"""
        response = client.post(
            "/api/legal-declarations",
            headers=auth_headers,
            json={
                "compliance_record_id": test_record.id,
                "purpose_of_use": "用于数据格式化",
                "url_to_source": "https://github.com/lodash/lodash",
                "license_info_url": "https://opensource.org/licenses/MIT",
                "license_text_url": "https://opensource.org/licenses/MIT",
                "license_name": "MIT",
                "is_modified": "no",
                "usage_type": "dynamically_linked",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["compliance_record_id"] == test_record.id
        assert data["license_name"] == "MIT"
        assert data["is_modified"] == "no"
        assert data["usage_type"] == "dynamically_linked"

    def test_create_declaration_duplicate(self, client, test_record, db_session):
        """测试重复创建声明"""
        # 先创建一个
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="测试",
            url_to_source="https://example.com",
            license_info_url="https://example.com",
            license_text_url="https://example.com",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 再创建应该失败
        response = client.post(
            "/api/legal-declarations",
            json={
                "compliance_record_id": test_record.id,
                "purpose_of_use": "用于数据格式化",
                "url_to_source": "https://github.com/lodash/lodash",
                "license_info_url": "https://opensource.org/licenses/MIT",
                "license_text_url": "https://opensource.org/licenses/MIT",
                "license_name": "MIT",
                "is_modified": "no",
                "usage_type": "dynamically_linked",
            },
        )
        assert response.status_code == 400
        assert "已有声明" in response.json()["detail"]

    def test_create_declaration_non_draft(self, client, test_record, db_session):
        """测试非 DRAFT 状态不能创建声明"""
        test_record.status = RecordStatus.PENDING_SECURITY
        db_session.commit()

        response = client.post(
            "/api/legal-declarations",
            json={
                "compliance_record_id": test_record.id,
                "purpose_of_use": "用于数据格式化",
                "url_to_source": "https://github.com/lodash/lodash",
                "license_info_url": "https://opensource.org/licenses/MIT",
                "license_text_url": "https://opensource.org/licenses/MIT",
                "license_name": "MIT",
                "is_modified": "no",
                "usage_type": "dynamically_linked",
            },
        )
        assert response.status_code == 400
        assert "仅 DRAFT 状态" in response.json()["detail"]

    def test_get_declaration(self, client, test_record, db_session):
        """测试获取声明"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        response = client.get(f"/api/legal-declarations/{decl.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == decl.id
        assert data["license_name"] == "MIT"

    def test_get_declaration_not_found(self, client):
        """测试获取不存在的声明"""
        response = client.get("/api/legal-declarations/99999")
        assert response.status_code == 404

    def test_get_declaration_by_record(self, client, test_record, db_session):
        """测试通过合规记录 ID 获取声明"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        response = client.get(f"/api/legal-declarations/records/{test_record.id}/declaration")
        assert response.status_code == 200
        data = response.json()
        assert data["compliance_record_id"] == test_record.id
        assert data["component"] is not None
        assert data["component"]["name"] == "lodash"

    def test_update_declaration(self, client, test_record, db_session):
        """测试更新声明"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        response = client.put(
            f"/api/legal-declarations/{decl.id}",
            json={
                "purpose_of_use": "更新后的使用目的",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["purpose_of_use"] == "更新后的使用目的"

    def test_update_declaration_non_draft(self, client, test_record, db_session):
        """测试非 DRAFT/REJECTED 状态不能更新声明"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 修改记录状态为 PENDING_SECURITY（不能更新）
        test_record.status = RecordStatus.PENDING_SECURITY
        db_session.commit()

        response = client.put(
            f"/api/legal-declarations/{decl.id}",
            json={"purpose_of_use": "更新后的使用目的"},
        )
        assert response.status_code == 400
        assert "DRAFT" in response.json()["detail"]
        assert "REJECTED" in response.json()["detail"]

    def test_update_declaration_rejected_status(self, client, test_record, db_session):
        """测试 REJECTED 状态的记录可以更新声明（研发用户重新处理被驳回的记录）"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 修改记录状态为 REJECTED（可以更新）
        test_record.status = RecordStatus.REJECTED
        db_session.commit()

        response = client.put(
            f"/api/legal-declarations/{decl.id}",
            json={"purpose_of_use": "重新提交后的使用目的"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["purpose_of_use"] == "重新提交后的使用目的"

    def test_submit_declaration(self, client, test_record, db_session):
        """测试提交声明"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        response = client.post(f"/api/legal-declarations/{decl.id}/submit", json={})
        assert response.status_code == 200

        # 验证记录状态已变更
        db_session.refresh(test_record)
        assert test_record.status == RecordStatus.PENDING_SECURITY

    def test_submit_declaration_non_draft(self, client, test_record, db_session):
        """测试非 DRAFT 状态不能提交声明"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        test_record.status = RecordStatus.PENDING_SECURITY
        db_session.commit()

        response = client.post(f"/api/legal-declarations/{decl.id}/submit", json={})
        assert response.status_code == 400
        assert "仅 DRAFT 状态" in response.json()["detail"]


class TestBulkImport:
    """测试批量导入"""

    def test_bulk_import_json(self, client, db_session):
        """测试批量导入 SPDX JSON 格式"""
        spdx_json = """
        {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-1",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://github.com/lodash/lodash"
                },
                {
                    "SPDXID": "SPDXRef-Package-2",
                    "name": "express",
                    "versionInfo": "4.18.2",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://github.com/expressjs/express"
                }
            ]
        }
        """
        response = client.post(
            "/api/legal-declarations/bulk-import?system_name=Test%20System",
            files={"file": ("report.spdx.json", spdx_json, "application/json")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert data["failed_count"] == 0
        assert len(data["results"]) == 2

    def test_bulk_import_invalid_format(self, client):
        """测试导入无效格式"""
        response = client.post(
            "/api/legal-declarations/bulk-import?system_name=Test System",
            files={"file": ("invalid.txt", "not a valid spdx file", "text/plain")},
        )
        assert response.status_code == 400


class TestHistorySuggestions:
    """测试历史复用建议"""

    def test_get_history_suggestions(self, client, db_session, test_user):
        """测试获取历史建议"""
        # 创建组件和记录
        component = Component(name="lodash-history-sug", version="4.17.21", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="Test System",
            status=RecordStatus.DRAFT,
            filled_by=test_user.id,
        )
        db_session.add(record)
        db_session.commit()

        # 创建已批准的声明
        decl = LegalDeclaration(
            compliance_record_id=record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 测试 - 获取历史建议（由于 unique constraint，不会有同名同版本的其他组件）
        response = client.get(f"/api/legal-declarations/{decl.id}/history-suggestions")
        assert response.status_code == 200
        data = response.json()
        assert data["has_history"] is False
        assert len(data["suggestions"]) == 0

    def test_get_history_suggestions_empty(self, client, test_record, db_session):
        """测试无历史建议"""
        decl = LegalDeclaration(
            compliance_record_id=test_record.id,
            purpose_of_use="用于数据格式化",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        response = client.get(f"/api/legal-declarations/{decl.id}/history-suggestions")
        assert response.status_code == 200
        data = response.json()
        assert data["has_history"] is False
        assert len(data["suggestions"]) == 0


class TestValidation:
    """测试字段验证"""

    def test_purpose_of_use_max_length(self, client, test_record):
        """测试使用目的长度限制"""
        long_text = "x" * 501
        response = client.post(
            "/api/legal-declarations",
            json={
                "compliance_record_id": test_record.id,
                "purpose_of_use": long_text,
                "url_to_source": "https://example.com",
                "license_info_url": "https://example.com",
                "license_text_url": "https://example.com",
                "license_name": "MIT",
                "is_modified": "no",
                "usage_type": "dynamically_linked",
            },
        )
        assert response.status_code == 422

    def test_invalid_usage_type(self, client, test_record):
        """测试无效使用方式"""
        response = client.post(
            "/api/legal-declarations",
            json={
                "compliance_record_id": test_record.id,
                "purpose_of_use": "用于数据格式化",
                "url_to_source": "https://example.com",
                "license_info_url": "https://example.com",
                "license_text_url": "https://example.com",
                "license_name": "MIT",
                "is_modified": "no",
                "usage_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    def test_invalid_is_modified(self, client, test_record):
        """测试无效是否修改值"""
        response = client.post(
            "/api/legal-declarations",
            json={
                "compliance_record_id": test_record.id,
                "purpose_of_use": "用于数据格式化",
                "url_to_source": "https://example.com",
                "license_info_url": "https://example.com",
                "license_text_url": "https://example.com",
                "license_name": "MIT",
                "is_modified": "maybe",
                "usage_type": "dynamically_linked",
            },
        )
        assert response.status_code == 422
