"""催促功能相关测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.user import User, UserRole
from app.models.urgency import Urgency, UrgencyTarget


class TestUrgencyModel:
    """催促模型测试"""

    def test_urgency_creation(self, db_session: Session, engineer):
        """测试创建催促记录"""
        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        urgency = Urgency(
            record_id=record.id,
            urged_by=engineer.id,
            target_role=UrgencyTarget.SECURITY,
        )
        db_session.add(urgency)
        db_session.commit()

        assert urgency.id is not None
        assert urgency.record_id == record.id
        assert urgency.urged_by == engineer.id
        assert urgency.target_role == UrgencyTarget.SECURITY
        assert urgency.created_at is not None

    def test_urgency_relationships(self, db_session: Session, engineer):
        """测试催促记录关联关系"""
        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        urgency = Urgency(
            record_id=record.id,
            urged_by=engineer.id,
            target_role=UrgencyTarget.SECURITY,
        )
        db_session.add(urgency)
        db_session.commit()

        # 测试关联关系
        assert urgency.record == record
        assert urgency.user == engineer
        assert urgency in record.urgencies
        assert urgency in engineer.urgencies


class TestUrgencyEndpoints:
    """催促端点测试"""

    def _get_auth_token(self, client, user):
        """获取认证 token"""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import get_settings
        settings = get_settings()

        expire = datetime.utcnow() + timedelta(minutes=60)
        to_encode = {
            "email": user.email,
            "role": user.role.value,
            "exp": expire
        }
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    def test_urge_record_pending_security(self, db_session: Session, client: TestClient, engineer):
        """测试催促 - 待安全校验状态"""
        token = self._get_auth_token(client, engineer)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # 验证催促记录已创建
        urgency = db_session.query(Urgency).filter(Urgency.record_id == record.id).first()
        assert urgency is not None
        assert urgency.urged_by == engineer.id
        assert urgency.target_role == UrgencyTarget.SECURITY

    def test_urge_record_pending_legal(self, db_session: Session, client: TestClient, engineer):
        """测试催促 - 待法务审批状态"""
        token = self._get_auth_token(client, engineer)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # 验证催促记录已创建
        urgency = db_session.query(Urgency).filter(Urgency.record_id == record.id).first()
        assert urgency is not None
        assert urgency.target_role == UrgencyTarget.LEGAL

    def test_urge_record_not_found(self, client: TestClient, engineer):
        """测试催促 - 记录不存在"""
        token = self._get_auth_token(client, engineer)

        response = client.post(
            "/api/compliance-records/999/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
        assert "Record not found" in response.json()["detail"]

    def test_urge_record_invalid_status(self, db_session: Session, client: TestClient, engineer):
        """测试催促 - 状态不正确（草稿状态不能催促）"""
        token = self._get_auth_token(client, engineer)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.DRAFT,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "当前状态不能催促" in response.json()["detail"]

    def test_urge_record_approved_status(self, db_session: Session, client: TestClient, engineer):
        """测试催促 - 已审批状态不能催促"""
        token = self._get_auth_token(client, engineer)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.APPROVED,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "当前状态不能催促" in response.json()["detail"]

    def test_urge_engineer_can_urge_own_record(self, db_session: Session, client: TestClient, engineer):
        """测试催促 - 工程师可以催促自己的记录"""
        token = self._get_auth_token(client, engineer)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_urge_engineer_cannot_urge_others_record(self, db_session: Session, client: TestClient, engineer):
        """测试催促 - 工程师不能催促其他人的记录"""
        token = self._get_auth_token(client, engineer)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        # 创建其他用户的记录
        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=999,  # 其他用户 ID
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "权限不足：只能催促自己的记录" in response.json()["detail"]

    def test_urge_admin_can_urge_any_record(self, db_session: Session, client: TestClient, admin):
        """测试催促 - 管理员可以催促任何记录"""
        token = self._get_auth_token(client, admin)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        # 创建其他用户的记录
        other_user = User(id=999, email="other@test.com", role=UserRole.ENGINEER, is_active=True)
        db_session.add(other_user)

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=other_user.id,
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        urgency = db_session.query(Urgency).filter(Urgency.record_id == record.id).first()
        assert urgency is not None
        assert urgency.urged_by == admin.id

    def test_urge_security_can_urge(self, db_session: Session, client: TestClient, security):
        """测试催促 - 安全用户可以催促"""
        token = self._get_auth_token(client, security)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=None,  # NULL filled_by
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_urge_legal_can_urge(self, db_session: Session, client: TestClient, legal):
        """测试催促 - 法务用户可以催促"""
        token = self._get_auth_token(client, legal)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_LEGAL,
            filled_by=None,
        )
        db_session.add(record)
        db_session.commit()

        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_urge_multiple_urgencies_same_record(self, db_session: Session, client: TestClient, engineer, security):
        """测试催促 - 同一记录可以被多次催促（不同用户）"""
        token_engineer = self._get_auth_token(client, engineer)
        token_security = self._get_auth_token(client, security)

        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        # 工程师催促
        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token_engineer}"}
        )
        assert response.status_code == 200

        # 安全用户也催促
        response = client.post(
            f"/api/compliance-records/{record.id}/urge",
            headers={"Authorization": f"Bearer {token_security}"}
        )
        assert response.status_code == 200

        # 验证创建了两条催促记录
        urgencies = db_session.query(Urgency).filter(Urgency.record_id == record.id).all()
        assert len(urgencies) == 2


class TestUrgencyPermissionMatrix:
    """催促权限矩阵测试"""

    def _get_auth_token(self, client, user):
        """获取认证 token"""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.config import get_settings
        settings = get_settings()

        expire = datetime.utcnow() + timedelta(minutes=60)
        to_encode = {
            "email": user.email,
            "role": user.role.value,
            "exp": expire
        }
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    def test_all_roles_can_urge(self, db_session: Session, client: TestClient, engineer, security, legal, admin):
        """测试所有角色都可以催促待审批记录"""
        component = Component(name="test-component", version="1.0.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        record = ComplianceRecord(
            component_id=component.id,
            system_name="test-system",
            status=RecordStatus.PENDING_SECURITY,
            filled_by=engineer.id,
        )
        db_session.add(record)
        db_session.commit()

        # 所有角色都应该能够催促
        for user in [engineer, security, legal, admin]:
            token = self._get_auth_token(client, user)
            response = client.post(
                f"/api/compliance-records/{record.id}/urge",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200, f"{user.role} 应该能够催促"
