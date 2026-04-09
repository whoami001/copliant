"""SPDX 解析器测试"""

import pytest
from app.services.spdx_parser import (
    parse_spdx_file,
    SpdxParser,
    SpdxParseError,
    SpdxComponent,
)


class TestSpdxParser:
    """测试 SPDX 解析器"""

    def test_parse_json_simple(self):
        """测试解析简单 JSON 格式"""
        content = """
        {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-1",
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://github.com/lodash/lodash"
                }
            ]
        }
        """
        components = parse_spdx_file(content)
        assert len(components) == 1
        assert components[0].name == "lodash"
        assert components[0].version == "4.17.21"
        assert components[0].license_concluded == "MIT"
        assert components[0].download_location == "https://github.com/lodash/lodash"

    def test_parse_json_multiple(self):
        """测试解析多个组件"""
        content = """
        {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "name": "lodash",
                    "versionInfo": "4.17.21",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://github.com/lodash/lodash"
                },
                {
                    "name": "express",
                    "versionInfo": "4.18.2",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://github.com/expressjs/express"
                },
                {
                    "name": "react",
                    "versionInfo": "18.2.0",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://github.com/facebook/react"
                }
            ]
        }
        """
        components = parse_spdx_file(content)
        assert len(components) == 3
        assert components[0].name == "lodash"
        assert components[1].name == "express"
        assert components[2].name == "react"

    def test_parse_json_noassertion_license(self):
        """测试解析 NOASSERTION 许可证"""
        content = """
        {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "name": "unknown-package",
                    "versionInfo": "1.0.0",
                    "licenseConcluded": "NOASSERTION",
                    "downloadLocation": "https://example.com"
                }
            ]
        }
        """
        components = parse_spdx_file(content)
        assert len(components) == 1
        assert components[0].license_concluded == "UNKNOWN"

    def test_parse_json_missing_version(self):
        """测试解析缺少版本的包"""
        content = """
        {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "name": "package-without-version",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://example.com"
                }
            ]
        }
        """
        components = parse_spdx_file(content)
        assert len(components) == 1
        assert components[0].version == ""

    def test_parse_json_empty_name(self):
        """测试解析空名称的包（应跳过）"""
        content = """
        {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "name": "",
                    "versionInfo": "1.0.0",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://example.com"
                },
                {
                    "name": "valid-package",
                    "versionInfo": "1.0.0",
                    "licenseConcluded": "MIT",
                    "downloadLocation": "https://example.com"
                }
            ]
        }
        """
        components = parse_spdx_file(content)
        assert len(components) == 1
        assert components[0].name == "valid-package"

    def test_parse_json_invalid_json(self):
        """测试解析无效 JSON"""
        content = "{ not valid json }"
        parser = SpdxParser()
        with pytest.raises(SpdxParseError) as exc_info:
            parser.parse_json(content)
        assert "无效的 JSON 格式" in str(exc_info.value)

    def test_parse_json_missing_packages(self):
        """测试解析缺少 packages 字段"""
        content = '{"spdxVersion": "SPDX-2.3"}'
        with pytest.raises(SpdxParseError) as exc_info:
            parse_spdx_file(content)
        assert "缺少 packages 字段" in str(exc_info.value)

    def test_parse_tag_value_simple(self):
        """测试解析简单 tag-value 格式"""
        content = """
        SPDXVersion: SPDX-2.3
        PackageName: lodash
        PackageVersion: 4.17.21
        LicenseConcluded: MIT
        DownloadLocation: https://github.com/lodash/lodash
        CopyrightText: Copyright (c) 2021 Lodash Contributors
        """
        components = parse_spdx_file(content, file_format="tag-value")
        assert len(components) == 1
        assert components[0].name == "lodash"
        assert components[0].version == "4.17.21"
        assert components[0].license_concluded == "MIT"
        assert "lodash/lodash" in components[0].download_location

    def test_parse_tag_value_multiple(self):
        """测试解析多个组件 tag-value 格式"""
        content = """
        SPDXVersion: SPDX-2.3
        PackageName: lodash
        PackageVersion: 4.17.21
        LicenseConcluded: MIT
        DownloadLocation: https://github.com/lodash/lodash

        PackageName: express
        PackageVersion: 4.18.2
        LicenseConcluded: MIT
        DownloadLocation: https://github.com/expressjs/express
        """
        components = parse_spdx_file(content, file_format="tag-value")
        assert len(components) == 2
        assert components[0].name == "lodash"
        assert components[1].name == "express"

    def test_parse_tag_value_with_license_info(self):
        """测试解析许可证信息 tag-value 格式"""
        content = """
        SPDXVersion: SPDX-2.3
        PackageName: test-package
        PackageVersion: 1.0.0
        LicenseConcluded: MIT
        LicenseInfoFromFiles: https://opensource.org/licenses/MIT
        DownloadLocation: https://example.com
        """
        components = parse_spdx_file(content, file_format="tag-value")
        assert len(components) == 1
        assert "opensource.org" in components[0].license_info_from_files

    def test_detect_format_json(self):
        """测试检测 JSON 格式"""
        content = '{"spdxVersion": "SPDX-2.3", "packages": []}'
        parser = SpdxParser()
        fmt = parser.detect_format(content)
        assert fmt == "json"

    def test_detect_format_tag_value(self):
        """测试检测 tag-value 格式"""
        content = "SPDXVersion: SPDX-2.3\nPackageName: test"
        parser = SpdxParser()
        fmt = parser.detect_format(content)
        assert fmt == "tag-value"

    def test_detect_format_invalid(self):
        """测试检测无效格式"""
        content = "not a valid spdx file at all"
        parser = SpdxParser()
        with pytest.raises(SpdxParseError) as exc_info:
            parser.detect_format(content)
        assert "无法识别" in str(exc_info.value)

    def test_spdx_component_to_dict(self):
        """测试组件转字典"""
        comp = SpdxComponent(
            name="test",
            version="1.0.0",
            license_concluded="MIT",
            download_location="https://example.com",
            license_info_from_files="https://example.com/license",
            copyright_text="Copyright 2024",
            spdx_id="SPDXRef-Package-1",
        )
        d = comp.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0.0"
        assert d["license_concluded"] == "MIT"
        assert d["spdx_id"] == "SPDXRef-Package-1"
