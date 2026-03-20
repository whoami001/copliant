"""组件匹配服务测试"""

import pytest
from sqlalchemy.orm import Session

from app.services.component_match import ComponentMatchService
from app.models.component import Component


class TestComponentMatchService:
    """组件匹配服务测试"""

    def test_find_exact_match_found(self, db_session: Session):
        """测试完全匹配 - 找到"""
        # 准备数据
        component = Component(
            name="lodash",
            version="4.17.21",
            license="MIT",
            copyright="Copyright (c) JS Foundation",
            usage_type="direct",
            license_risk_level="safe",
        )
        db_session.add(component)
        db_session.commit()

        # 执行测试
        service = ComponentMatchService(db_session)
        result = service.find_exact_match("lodash", "4.17.21")

        assert result is not None
        assert result.name == "lodash"
        assert result.version == "4.17.21"

    def test_find_exact_match_not_found(self, db_session: Session):
        """测试完全匹配 - 未找到"""
        service = ComponentMatchService(db_session)
        result = service.find_exact_match("nonexistent", "1.0.0")

        assert result is None

    def test_find_similar_matches(self, db_session: Session):
        """测试相似匹配"""
        # 准备数据 - 同名不同版本
        for version in ["4.17.20", "4.17.19", "4.17.18"]:
            component = Component(
                name="lodash",
                version=version,
                license="MIT",
            )
            db_session.add(component)
        db_session.commit()

        service = ComponentMatchService(db_session)
        results = service.find_similar_matches("lodash", "4.17.21")

        assert len(results) == 3
        assert all(c.name == "lodash" for c in results)
        assert all(c.version != "4.17.21" for c in results)

    def test_check_duplicate_true(self, db_session: Session):
        """测试重复检查 - 已存在"""
        component = Component(name="express", version="4.18.2", license="MIT")
        db_session.add(component)
        db_session.commit()

        service = ComponentMatchService(db_session)
        assert service.check_duplicate("express", "4.18.2") is True

    def test_check_duplicate_false(self, db_session: Session):
        """测试重复检查 - 不存在"""
        service = ComponentMatchService(db_session)
        assert service.check_duplicate("nonexistent", "1.0.0") is False

    def test_get_match_result_exact(self, db_session: Session):
        """测试完整匹配结果 - 完全匹配"""
        component = Component(name="react", version="18.2.0", license="MIT")
        db_session.add(component)
        db_session.commit()

        service = ComponentMatchService(db_session)
        is_exact, exact_match, similar = service.get_match_result("react", "18.2.0")

        assert is_exact is True
        assert exact_match is not None
        assert len(similar) == 0
