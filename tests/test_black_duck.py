"""Black Duck 服务测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.black_duck import BlackDuckService, black_duck_service
from app.exceptions import BlackDuckAPIError, NotFoundError


class TestBlackDuckService:
    """Black Duck 服务测试"""

    def test_service_init(self):
        """测试服务初始化"""
        service = BlackDuckService()
        # 如果未配置，应该为 None 或空
        assert hasattr(service, "base_url")
        assert hasattr(service, "token")
        assert service.timeout == 30.0
        assert service.max_retries == 3

    def test_mock_report_structure(self):
        """测试模拟报告数据结构"""
        service = BlackDuckService()
        report = service._get_mock_report("test-123")

        assert report["reportId"] == "test-123"
        assert report["reportName"] == "模拟报告"
        assert "components" in report
        assert len(report["components"]) == 3

    def test_mock_report_components(self):
        """测试模拟报告的组件内容"""
        service = BlackDuckService()
        report = service._get_mock_report("test-123")

        component_names = [c["componentName"] for c in report["components"]]
        assert "lodash" in component_names
        assert "express" in component_names
        assert "react" in component_names

    def test_extract_license(self):
        """测试许可证提取"""
        service = BlackDuckService()

        item_with_license = {
            "licenses": [{"name": "MIT"}],
        }
        assert service._extract_license(item_with_license) == "MIT"

        item_without_license = {}
        assert service._extract_license(item_without_license) == "UNKNOWN"

        item_empty_licenses = {"licenses": []}
        assert service._extract_license(item_empty_licenses) == "UNKNOWN"

    def test_detect_usage_type_direct(self):
        """测试直接依赖检测"""
        service = BlackDuckService()

        item = {"directDependency": True}
        assert service._detect_usage_type(item) == "direct"

    def test_detect_usage_type_transitive(self):
        """测试传递依赖检测"""
        service = BlackDuckService()

        item = {"directDependency": False}
        assert service._detect_usage_type(item) == "transitive"

        item = {}
        assert service._detect_usage_type(item) == "transitive"

    def test_calculate_risk_level_safe_licenses(self):
        """测试安全许可证风险等级"""
        service = BlackDuckService()

        safe_cases = [
            {"licenses": [{"name": "MIT"}]},
            {"licenses": [{"name": "ISC"}]},
            {"licenses": [{"name": "BSD-2-Clause"}]},
            {"licenses": [{"name": "BSD-3-Clause"}]},
            {"licenses": [{"name": "CC0-1.0"}]},
        ]

        for item in safe_cases:
            assert service._calculate_risk_level(item) == "safe"

    def test_calculate_risk_level_apache_caution(self):
        """测试 Apache 2.0 许可证（需要注意）"""
        service = BlackDuckService()

        item = {"licenses": [{"name": "Apache-2.0"}]}
        assert service._calculate_risk_level(item) == "caution"

    def test_calculate_risk_level_warning_licenses(self):
        """测试警告许可证（传染性）"""
        service = BlackDuckService()

        warning_cases = [
            {"licenses": [{"name": "GPL-2.0"}]},
            {"licenses": [{"name": "GPL-3.0"}]},
            {"licenses": [{"name": "LGPL-2.1"}]},
            {"licenses": [{"name": "LGPL-3.0"}]},
            {"licenses": [{"name": "AGPL-3.0"}]},
        ]

        for item in warning_cases:
            assert service._calculate_risk_level(item) == "warning"

    def test_calculate_risk_level_unknown(self):
        """测试未知许可证"""
        service = BlackDuckService()

        item = {"licenses": [{"name": "UNKNOWN"}]}
        assert service._calculate_risk_level(item) == "unknown"

        item = {"licenses": []}
        assert service._calculate_risk_level(item) == "unknown"

    def test_calculate_risk_level_custom(self):
        """测试自定义许可证"""
        service = BlackDuckService()

        item = {"licenses": [{"name": "Custom-License"}]}
        assert service._calculate_risk_level(item) == "caution"

    def test_should_use_async(self):
        """测试异步处理判断"""
        service = BlackDuckService()

        # 默认阈值是 50
        assert service.should_use_async(10) is False
        assert service.should_use_async(50) is False
        assert service.should_use_async(51) is True
        assert service.should_use_async(100) is True


@pytest.mark.asyncio
class TestBlackDuckServiceAsync:
    """Black Duck 服务异步测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return BlackDuckService()

    async def test_fetch_report_mock_mode(self, service):
        """测试获取报告（模拟模式）"""
        # 当未配置 URL 和 token 时，应该返回模拟数据
        report = await service.fetch_report("test-123")

        assert report["reportId"] == "test-123"
        assert len(report["components"]) >= 1

    async def test_parse_components(self, service):
        """测试解析组件"""
        report_data = {
            "reportId": "test-123",
            "components": [
                {
                    "componentName": "axios",
                    "componentVersion": "1.4.0",
                    "licenses": [{"name": "MIT"}],
                    "copyright": "Copyright (c) 2023",
                    "directDependency": True,
                },
            ],
        }

        components = await service.parse_components(report_data)

        assert len(components) == 1
        assert components[0]["name"] == "axios"
        assert components[0]["version"] == "1.4.0"
        assert components[0]["license"] == "MIT"
        assert components[0]["usage_type"] == "direct"
        assert components[0]["license_risk_level"] == "safe"

    async def test_parse_components_multiple(self, service):
        """测试解析多个组件"""
        report_data = {
            "reportId": "test-123",
            "components": [
                {"componentName": "react", "componentVersion": "18.0.0", "licenses": [{"name": "MIT"}]},
                {"componentName": "lodash", "componentVersion": "4.17.21", "licenses": [{"name": "MIT"}]},
                {"componentName": "express", "componentVersion": "4.18.0", "licenses": [{"name": "MIT"}]},
            ],
        }

        components = await service.parse_components(report_data)

        assert len(components) == 3
        assert all(c["license_risk_level"] == "safe" for c in components)

    async def test_parse_components_with_gpl(self, service):
        """测试解析包含 GPL 许可证的组件"""
        report_data = {
            "reportId": "test-123",
            "components": [
                {"componentName": "gpl-lib", "componentVersion": "1.0.0", "licenses": [{"name": "GPL-3.0"}]},
            ],
        }

        components = await service.parse_components(report_data)

        assert len(components) == 1
        assert components[0]["license_risk_level"] == "warning"
