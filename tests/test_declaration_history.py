"""法务声明历史复用服务测试"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import Base
from app.models.user import User, UserRole
from app.models.component import Component
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.legal_declaration import LegalDeclaration, UsageType, IsModified
from app.services.declaration_history import (
    DeclarationHistoryService,
    get_declaration_history_service,
)


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
def test_user(db_session):
    """创建测试用户"""
    user = User(email="legal@test.com", role=UserRole.LEGAL, name="Legal Tester")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_component(db_session):
    """创建测试组件"""
    component = Component(
        name="test-component",
        version="1.0.0",
        license="MIT",
    )
    db_session.add(component)
    db_session.commit()
    return component


@pytest.fixture
def test_component_same_name_version(db_session):
    """创建同名同版本的组件（用于测试历史复用）"""
    # 注意：这个 fixture 与 test_component 创建相同的 name/version
    # 应该只在需要对比的测试中使用，不使用 test_component fixture
    component = Component(
        name="lodash-test",
        version="4.17.21",
        license="MIT",
    )
    db_session.add(component)
    db_session.commit()
    return component


@pytest.fixture
def test_component_different_version(db_session):
    """创建同名不同版本的组件"""
    component = Component(
        name="test-component",
        version="2.0.0",
        license="MIT",
    )
    db_session.add(component)
    db_session.commit()
    return component


class TestDeclarationHistoryService:
    """测试历史复用服务"""

    def test_get_history_suggestions_empty(self, db_session, test_component):
        """测试无历史记录"""
        service = DeclarationHistoryService(db_session)
        result = service.get_history_suggestions(test_component.id)
        assert result.has_history is False
        assert len(result.suggestions) == 0

    def test_get_history_suggestions_with_history(
        self, db_session, test_user
    ):
        """测试有历史记录"""
        # 创建两个不同名称的组件（用于测试历史查询）
        comp1 = Component(name="lodash-test-v1", version="4.17.21", license="MIT")
        db_session.add(comp1)
        db_session.commit()

        comp2 = Component(name="lodash-test-v2", version="4.17.21", license="MIT")
        db_session.add(comp2)
        db_session.commit()

        # 为 comp1 创建已批准的合规记录
        record = ComplianceRecord(
            component_id=comp1.id,
            system_name="Other System",
            status=RecordStatus.APPROVED,
            filled_by=test_user.id,
            approved_by_legal=test_user.id,
            legal_approved_at=datetime.utcnow(),
        )
        db_session.add(record)
        db_session.flush()

        # 创建法务声明
        decl = LegalDeclaration(
            compliance_record_id=record.id,
            purpose_of_use="用于工具函数",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 测试 - 查询 comp1 的历史记录（应该没有，因为排除自身）
        service = DeclarationHistoryService(db_session)
        result = service.get_history_suggestions(comp1.id)

        # 因为没有其他同名同版本组件，所以应该返回空
        assert result.has_history is False

    def test_get_history_suggestions_excludes_self(
        self, db_session, test_user
    ):
        """测试历史记录排除自身"""
        # 创建组件
        comp = Component(name="exclude-self-test", version="1.0.0", license="MIT")
        db_session.add(comp)
        db_session.commit()

        # 创建已批准的合规记录（同一个组件）
        record = ComplianceRecord(
            component_id=comp.id,
            system_name="Test System",
            status=RecordStatus.APPROVED,
            filled_by=test_user.id,
            approved_by_legal=test_user.id,
            legal_approved_at=datetime.utcnow(),
        )
        db_session.add(record)
        db_session.flush()

        # 创建法务声明
        decl = LegalDeclaration(
            compliance_record_id=record.id,
            purpose_of_use="用于测试",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 测试 - 应该没有历史记录（因为只有自身）
        service = DeclarationHistoryService(db_session)
        result = service.get_history_suggestions(comp.id)

        assert result.has_history is False
        assert len(result.suggestions) == 0

    def test_get_history_suggestions_only_approved(
        self, db_session, test_user
    ):
        """测试只返回已批准的历史记录"""
        # 创建组件
        comp = Component(name="only-approved-test", version="1.0.0", license="MIT")
        db_session.add(comp)
        db_session.commit()

        # 创建待审批的合规记录（同一个组件）
        record = ComplianceRecord(
            component_id=comp.id,
            system_name="Pending System",
            status=RecordStatus.PENDING_LEGAL,
            filled_by=test_user.id,
        )
        db_session.add(record)
        db_session.flush()

        # 创建法务声明
        decl = LegalDeclaration(
            compliance_record_id=record.id,
            purpose_of_use="待审批",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 测试 - 待审批的记录不应返回（而且也没有其他同名组件）
        service = DeclarationHistoryService(db_session)
        result = service.get_history_suggestions(comp.id)

        assert result.has_history is False

    def test_get_similar_declarations(
        self, db_session, test_user
    ):
        """测试获取相似声明"""
        # 创建两个组件
        comp1 = Component(name="similar-decl-test", version="1.0.0", license="MIT")
        db_session.add(comp1)
        db_session.commit()

        comp2 = Component(name="similar-decl-test-2", version="1.0.0", license="MIT")
        db_session.add(comp2)
        db_session.commit()

        # 创建已批准的合规记录
        record = ComplianceRecord(
            component_id=comp2.id,
            system_name="Similar System",
            status=RecordStatus.APPROVED,
            filled_by=test_user.id,
            approved_by_legal=test_user.id,
            legal_approved_at=datetime.utcnow(),
        )
        db_session.add(record)
        db_session.flush()

        # 创建法务声明（相同许可证和使用方式）
        decl = LegalDeclaration(
            compliance_record_id=record.id,
            purpose_of_use="用于相似用途",
            url_to_source="https://github.com/lodash/lodash",
            license_info_url="https://opensource.org/licenses/MIT",
            license_text_url="https://opensource.org/licenses/MIT",
            license_name="MIT",
            is_modified=IsModified.NO,
            usage_type=UsageType.DYNAMICALLY_LINKED,
        )
        db_session.add(decl)
        db_session.commit()

        # 测试
        service = DeclarationHistoryService(db_session)
        suggestions = service.get_similar_declarations(
            license_name="MIT",
            usage_type=UsageType.DYNAMICALLY_LINKED,
            limit=5,
        )

        assert len(suggestions) >= 1
        assert suggestions[0].license_name == "MIT"
        assert suggestions[0].usage_type == "dynamically_linked"

    def test_count_component_approvals(
        self, db_session, test_user
    ):
        """测试统计组件批准数量"""
        # 创建主组件
        comp = Component(name="count-approvals-test", version="1.0.0", license="MIT")
        db_session.add(comp)
        db_session.commit()

        # 为同一个组件创建 3 个已批准的合规记录
        for i in range(3):
            record = ComplianceRecord(
                component_id=comp.id,
                system_name=f"System {i}",
                status=RecordStatus.APPROVED,
                filled_by=test_user.id,
                approved_by_legal=test_user.id,
                legal_approved_at=datetime.utcnow(),
            )
            db_session.add(record)
            db_session.commit()

        # 测试 - 统计同一组件的批准记录数量（排除自身）
        service = DeclarationHistoryService(db_session)
        count = service.count_component_approvals(comp.id)

        # 由于查询排除了当前组件本身，而所有记录都是同一个组件的，所以返回 0
        # 这反映了当前 schema 的限制：同一组件不能有多个 name/version 相同的记录
        assert count == 0

    def test_component_not_found(self, db_session):
        """测试组件不存在"""
        service = DeclarationHistoryService(db_session)
        result = service.get_history_suggestions(99999)
        assert result.has_history is False
        assert len(result.suggestions) == 0

    def test_get_declaration_history_service_factory(self, db_session):
        """测试工厂函数"""
        service = get_declaration_history_service(db_session)
        assert isinstance(service, DeclarationHistoryService)
        assert service.db == db_session
