"""SPDX 文件解析服务

支持 SPDX JSON 和 tag-value 格式解析。
使用 spdx-tools 库进行标准解析。
"""

import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SpdxComponent:
    """SPDX 解析出的组件信息"""
    name: str
    version: str
    license_concluded: str
    download_location: str
    license_info_from_files: Optional[str] = None
    copyright_text: Optional[str] = None
    spdx_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "license_concluded": self.license_concluded,
            "download_location": self.download_location,
            "license_info_from_files": self.license_info_from_files,
            "copyright_text": self.copyright_text,
            "spdx_id": self.spdx_id,
        }


class SpdxParseError(Exception):
    """SPDX 解析错误"""
    pass


class SpdxParser:
    """SPDX 文件解析器"""

    def __init__(self):
        self.spdx_data: Optional[Dict] = None

    def parse_json(self, content: str) -> List[SpdxComponent]:
        """解析 SPDX JSON 格式

        Args:
            content: SPDX JSON 文件内容

        Returns:
            解析出的组件列表

        Raises:
            SpdxParseError: 解析失败时抛出
        """
        try:
            self.spdx_data = json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            raise SpdxParseError(f"无效的 JSON 格式：{e}")

        if "packages" not in self.spdx_data:
            raise SpdxParseError("SPDX 文件缺少 packages 字段")

        components = []
        for pkg in self.spdx_data["packages"]:
            try:
                component = self._parse_package(pkg)
                if component:
                    components.append(component)
            except Exception as e:
                logger.warning(f"解析包 {pkg.get('name', 'unknown')} 失败：{e}")
                continue

        return components

    def parse_tag_value(self, content: str) -> List[SpdxComponent]:
        """解析 SPDX tag-value 格式

        Args:
            content: SPDX tag-value 文件内容

        Returns:
            解析出的组件列表

        Raises:
            SpdxParseError: 解析失败时抛出
        """
        components = []
        current_package: Dict[str, Any] = {}

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "PackageName":
                    if current_package.get("name"):
                        # 保存上一个包
                        try:
                            component = self._parse_package(current_package)
                            if component:
                                components.append(component)
                        except Exception as e:
                            logger.warning(f"解析包 {current_package.get('name', 'unknown')} 失败：{e}")
                    current_package = {"name": value}
                elif key == "PackageVersion":
                    current_package["versionInfo"] = value
                elif key == "LicenseConcluded":
                    current_package["licenseConcluded"] = value
                elif key == "DownloadLocation":
                    current_package["downloadLocation"] = value
                elif key == "LicenseInfoFromFiles":
                    current_package["licenseInfoFromFiles"] = value
                elif key == "CopyrightText":
                    current_package["copyrightText"] = value

        # 处理最后一个包
        if current_package.get("name"):
            try:
                component = self._parse_package(current_package)
                if component:
                    components.append(component)
            except Exception as e:
                logger.warning(f"解析包 {current_package.get('name', 'unknown')} 失败：{e}")

        return components

    def _parse_package(self, pkg: Dict[str, Any]) -> Optional[SpdxComponent]:
        """解析单个包数据"""
        name = pkg.get("name", "").strip()
        if not name:
            return None

        version = pkg.get("versionInfo", pkg.get("version", "")).strip()
        license_concluded = pkg.get("licenseConcluded", "NOASSERTION").strip()
        download_location = pkg.get("downloadLocation", "").strip()

        # 清理许可证字段
        if license_concluded == "NOASSERTION":
            license_concluded = "UNKNOWN"

        return SpdxComponent(
            name=name,
            version=version,
            license_concluded=license_concluded,
            download_location=download_location,
            license_info_from_files=pkg.get("licenseInfoFromFiles", "").strip() or None,
            copyright_text=pkg.get("copyrightText", "").strip() or None,
            spdx_id=pkg.get("SPDXID"),
        )

    def detect_format(self, content: str) -> str:
        """检测 SPDX 文件格式

        Args:
            content: 文件内容

        Returns:
            'json' 或 'tag-value'

        Raises:
            SpdxParseError: 无法识别格式时抛出
        """
        content = content.strip()

        # 尝试 JSON
        if content.startswith("{"):
            try:
                json.loads(content)
                return "json"
            except json.JSONDecodeError:
                pass

        # 尝试 tag-value
        if "SPDXVersion:" in content or "PackageName:" in content:
            return "tag-value"

        raise SpdxParseError("无法识别 SPDX 文件格式，支持 JSON 和 tag-value")


def parse_spdx_file(content: str, file_format: Optional[str] = None) -> List[SpdxComponent]:
    """解析 SPDX 文件内容

    Args:
        content: 文件内容
        file_format: 可选，'json' 或 'tag-value'，不指定则自动检测

    Returns:
        解析出的组件列表

    Raises:
        SpdxParseError: 解析失败时抛出
    """
    parser = SpdxParser()

    if file_format is None:
        file_format = parser.detect_format(content)

    if file_format == "json":
        return parser.parse_json(content)
    elif file_format == "tag-value":
        return parser.parse_tag_value(content)
    else:
        raise SpdxParseError(f"不支持的 SPDX 格式：{file_format}")
