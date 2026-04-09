"""
Black Duck API 集成服务

支持同步和异步两种模式：
- <=50 个组件：同步处理
- >50 个组件：异步处理（需要任务队列）
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config import get_settings
from app.exceptions import BlackDuckAPIError, NotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BlackDuckService:
    """Black Duck API 服务"""

    def __init__(self):
        self.base_url = settings.black_duck_url
        self.token = settings.black_duck_token
        self.timeout = 30.0  # 30 秒超时
        self.max_retries = 3

    async def fetch_report(self, report_id: str) -> Dict[str, Any]:
        """
        获取 Black Duck 报告

        Args:
            report_id: 报告 ID

        Returns:
            报告数据

        Raises:
            BlackDuckAPIError: API 调用失败
            NotFoundError: 报告不存在
        """
        if not self.base_url or not self.token:
            # 开发环境：返回模拟数据
            logger.warning("Black Duck 未配置，返回模拟数据")
            return self._get_mock_report(report_id)

        url = f"{self.base_url}/api/reports/{report_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise NotFoundError(f"报告不存在：{report_id}")
                elif e.response.status_code == 401:
                    raise BlackDuckAPIError("Black Duck 认证失败")
                else:
                    raise BlackDuckAPIError(f"Black Duck API 错误：{e.response.status_code}")
            except httpx.TimeoutException:
                raise BlackDuckAPIError("Black Duck API 超时")
            except httpx.RequestError as e:
                raise BlackDuckAPIError(f"Black Duck API 请求失败：{str(e)}")

    async def parse_components(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析报告中的组件列表

        Args:
            report_data: 报告数据

        Returns:
            组件列表
        """
        components = []
        raw_components = report_data.get("components", [])

        for item in raw_components:
            component = {
                "name": item.get("componentName", ""),
                "version": item.get("componentVersion", ""),
                "license": self._extract_license(item),
                "copyright": item.get("copyright", ""),
                "usage_type": self._detect_usage_type(item),
                "license_risk_level": self._calculate_risk_level(item),
            }
            components.append(component)

        logger.info(f"解析到 {len(components)} 个组件")
        return components

    def _extract_license(self, item: Dict[str, Any]) -> str:
        """提取许可证信息"""
        licenses = item.get("licenses", [])
        if licenses:
            return licenses[0].get("name", "UNKNOWN")
        return "UNKNOWN"

    def _detect_usage_type(self, item: Dict[str, Any]) -> str:
        """检测使用类型（直接/间接）"""
        # 根据 Black Duck 数据结构判断
        if item.get("directDependency", False):
            return "direct"
        return "transitive"

    def _calculate_risk_level(self, item: Dict[str, Any]) -> str:
        """
        计算许可证风险等级

        Returns:
            'safe' | 'caution' | 'warning' | 'unknown'
        """
        license_name = self._extract_license(item)

        # 安全许可证
        safe_licenses = ["MIT", "ISC", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "CC0-1.0"]
        for safe in safe_licenses:
            if safe.lower() in license_name.lower():
                if license_name == "Apache-2.0":
                    return "caution"  # Apache 2.0 有专利条款
                return "safe"

        # 传染性许可证
        warning_licenses = ["GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0"]
        for warning in warning_licenses:
            if warning.lower() in license_name.lower():
                return "warning"

        # 未知许可证
        if license_name == "UNKNOWN" or not license_name:
            return "unknown"

        return "caution"  # 其他许可证需要人工审查

    def _get_mock_report(self, report_id: str) -> Dict[str, Any]:
        """返回模拟报告数据（开发环境用）"""
        return {
            "reportId": report_id,
            "reportName": "模拟报告",
            "createdAt": datetime.utcnow().isoformat(),
            "components": [
                {
                    "componentName": "lodash",
                    "componentVersion": "4.17.21",
                    "licenses": [{"name": "MIT"}],
                    "copyright": "Copyright (c) JS Foundation",
                    "directDependency": True,
                },
                {
                    "componentName": "express",
                    "componentVersion": "4.18.2",
                    "licenses": [{"name": "MIT"}],
                    "copyright": "Copyright (c) TJ Holowaychuk",
                    "directDependency": True,
                },
                {
                    "componentName": "react",
                    "componentVersion": "18.2.0",
                    "licenses": [{"name": "MIT"}],
                    "copyright": "Copyright (c) Meta Platforms, Inc.",
                    "directDependency": True,
                },
            ],
        }

    def should_use_async(self, component_count: int) -> bool:
        """判断是否应该使用异步处理"""
        return component_count > settings.black_duck_sync_max_components


# 单例
black_duck_service = BlackDuckService()
