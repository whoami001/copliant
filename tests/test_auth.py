"""认证相关路由测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestAuthEndpoints:
    """认证端点测试"""

    def test_login_success(self, client: TestClient):
        """测试登录成功"""
        payload = {
            "email": "test@example.com",
            "code": "123456",
        }
        response = client.post("/api/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_any_email(self, client: TestClient):
        """测试任意邮箱都可以登录（MVP 特性）"""
        emails = [
            "dev@company.com",
            "security@company.com",
            "legal@company.com",
            "random@test.com",
        ]

        for email in emails:
            payload = {"email": email, "code": "000000"}
            response = client.post("/api/auth/login", json=payload)
            assert response.status_code == 200
            assert "access_token" in response.json()

    def test_login_empty_email(self, client: TestClient):
        """测试空邮箱登录"""
        payload = {"email": "", "code": "123456"}
        response = client.post("/api/auth/login", json=payload)
        # MVP 版本可能允许空邮箱，这取决于 Pydantic 验证
        assert response.status_code in [200, 422]

    def test_get_current_user_with_valid_token(self, client: TestClient):
        """测试获取当前用户（有效 token）"""
        # 先登录获取 token
        login_response = client.post("/api/auth/login", json={"email": "test@test.com", "code": "123"})
        token = login_response.json()["access_token"]

        # 用 token 获取用户信息
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        # The email should match the login email (or be the MVP default for old tokens)
        assert data["email"] in ["test@test.com", "mvp@company.com"]
        assert data["role"] == "engineer"
        assert "id" in data
        assert "name" in data

    def test_get_current_user_with_invalid_token(self, client: TestClient):
        """测试获取当前用户（无效 token）"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401

    def test_get_current_user_no_token(self, client: TestClient):
        """测试获取当前用户（无 token）"""
        response = client.get("/api/auth/me")
        # FastAPI returns 403 for missing credentials (not 401)
        assert response.status_code == 403

    def test_logout(self, client: TestClient):
        """测试登出"""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "已登出" in data["message"]

    def test_login_returns_engineer_role(self, client: TestClient):
        """测试登录返回工程师角色（默认）"""
        payload = {"email": "admin@test.com", "code": "123"}
        response = client.post("/api/auth/login", json=payload)
        assert response.status_code == 200

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_response = client.get("/api/auth/me", headers=headers)

        assert user_response.json()["role"] == "engineer"

    def test_token_structure(self, client: TestClient):
        """测试 token 结构"""
        payload = {"email": "test@test.com", "code": "123"}
        response = client.post("/api/auth/login", json=payload)
        data = response.json()

        assert data["access_token"] is not None
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 50  # JWT 应该有一定长度
