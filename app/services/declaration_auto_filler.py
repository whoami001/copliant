"""法务声明自动预填充服务

根据 SPDX 数据、历史记录、许可证知识库，自动填充法务声明表单。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.legal_declaration import LegalDeclaration, UsageType, IsModified
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.component import Component
from app.services.spdx_parser import SpdxComponent
from app.utils.logger import get_logger

logger = get_logger(__name__)


# 常见开源许可证 URL 映射表
LICENSE_URL_MAP = {
    # MIT
    "MIT": ("https://opensource.org/licenses/MIT", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/MIT.txt"),
    "MIT-0": ("https://opensource.org/licenses/MIT-0", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/MIT-0.txt"),

    # Apache
    "Apache-2.0": ("https://www.apache.org/licenses/LICENSE-2.0", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/Apache-2.0.txt"),
    "Apache-1.1": ("https://www.apache.org/licenses/LICENSE-1.1", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/Apache-1.1.txt"),

    # GPL
    "GPL-2.0-only": ("https://www.gnu.org/licenses/old-licenses/gpl-2.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-2.0-only.txt"),
    "GPL-2.0-or-later": ("https://www.gnu.org/licenses/old-licenses/gpl-2.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-2.0-or-later.txt"),
    "GPL-3.0-only": ("https://www.gnu.org/licenses/gpl-3.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-3.0-only.txt"),
    "GPL-3.0-or-later": ("https://www.gnu.org/licenses/gpl-3.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-3.0-or-later.txt"),
    "LGPL-2.0-only": ("https://www.gnu.org/licenses/old-licenses/lgpl-2.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/LGPL-2.0-only.txt"),
    "LGPL-2.0-or-later": ("https://www.gnu.org/licenses/old-licenses/lgpl-2.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/LGPL-2.0-or-later.txt"),
    "LGPL-2.1-only": ("https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/LGPL-2.1-only.txt"),
    "LGPL-2.1-or-later": ("https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/LGPL-2.1-or-later.txt"),
    "LGPL-3.0-only": ("https://www.gnu.org/licenses/lgpl-3.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/LGPL-3.0-only.txt"),
    "LGPL-3.0-or-later": ("https://www.gnu.org/licenses/lgpl-3.0.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/LGPL-3.0-or-later.txt"),

    # BSD
    "BSD-2-Clause": ("https://opensource.org/licenses/BSD-2-Clause", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/BSD-2-Clause.txt"),
    "BSD-3-Clause": ("https://opensource.org/licenses/BSD-3-Clause", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/BSD-3-Clause.txt"),
    "BSD-4-Clause": ("https://opensource.org/licenses/BSD-4-Clause", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/BSD-4-Clause.txt"),

    # ISC
    "ISC": ("https://opensource.org/licenses/ISC", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/ISC.txt"),

    # Unlicense
    "Unlicense": ("https://unlicense.org/", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/Unlicense.txt"),

    # MPL
    "MPL-2.0": ("https://www.mozilla.org/MPL/2.0/", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/MPL-2.0.txt"),

    # EPL
    "EPL-1.0": ("https://www.eclipse.org/legal/epl-v10.html", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/EPL-1.0.txt"),
    "EPL-2.0": ("https://www.eclipse.org/legal/epl-2.0/", "https://raw.githubusercontent.com/spdx/license-list-data/main/text/EPL-2.0.txt"),
}


class DeclarationAutoFiller:
    """法务声明自动预填充服务"""

    def __init__(self, db: Session):
        self.db = db

    def fill_from_spdx(self, spdx_component: SpdxComponent) -> Dict[str, Any]:
        """从 SPDX 数据预填充

        Args:
            spdx_component: SPDX 解析的组件信息

        Returns:
            预填充的字段字典
        """
        # 许可证 URL 映射
        license_info_url, license_text_url = self._lookup_license_urls(spdx_component.license_concluded)

        return {
            "license_name": spdx_component.license_concluded if spdx_component.license_concluded != "UNKNOWN" else "",
            "url_to_source": spdx_component.download_location if spdx_component.download_location and spdx_component.download_location != "NOASSERTION" else "",
            "license_info_url": license_info_url,
            "license_text_url": license_text_url,
            "is_modified": IsModified.NO.value,  # 默认未修改
            "usage_type": "",  # 需要人工选择
            "purpose_of_use": "",  # 必须人工填写
        }

    def _lookup_license_urls(self, license_name: str) -> tuple:
        """查找许可证的说明页面和全文 URL

        Args:
            license_name: SPDX 许可证 ID

        Returns:
            (license_info_url, license_text_url) 元组
        """
        if not license_name or license_name == "UNKNOWN":
            return ("", "")

        # 精确匹配
        if license_name in LICENSE_URL_MAP:
            return LICENSE_URL_MAP[license_name]

        # 尝试去掉 -only 或 -or-later 后缀匹配
        base_name = license_name.replace("-only", "").replace("-or-later", "")
        for key, urls in LICENSE_URL_MAP.items():
            if key.startswith(base_name):
                return urls

        # 未知许可证，返回空
        return ("", "")

    def fill_from_history(self, component_name: str, component_version: str, exclude_record_id: Optional[int] = None) -> Dict[str, Any]:
        """从历史记录预填充

        查询相同组件（名称 + 版本）的已批准声明，返回最近一次的声明数据。

        Args:
            component_name: 组件名称
            component_version: 组件版本
            exclude_record_id: 排除的合规记录 ID（用于排除当前正在编辑的记录）

        Returns:
            预填充的字段字典，如果没有历史记录则返回空字典
        """
        filters = [
            Component.name == component_name,
            Component.version == component_version,
            ComplianceRecord.status == RecordStatus.APPROVED,
        ]

        if exclude_record_id:
            filters.append(ComplianceRecord.id != exclude_record_id)

        result = (
            self.db.query(LegalDeclaration)
            .join(ComplianceRecord, LegalDeclaration.compliance_record_id == ComplianceRecord.id)
            .join(Component, ComplianceRecord.component_id == Component.id)
            .filter(and_(*filters))
            .order_by(ComplianceRecord.legal_approved_at.desc())
            .first()
        )

        if not result:
            return {}

        return {
            "purpose_of_use": result.purpose_of_use,
            "usage_type": result.usage_type,
            "is_modified": result.is_modified,
            "license_info_url": result.license_info_url,
            "license_text_url": result.license_text_url,
        }

    def fill_purpose_with_ai(self, component_name: str, component_version: str, license_name: str) -> str:
        """AI 辅助填写使用目的

        根据组件名称和许可证类型，生成使用目的的 AI 建议。
        目前返回一个模板文本，后续可以集成 LLM。

        Args:
            component_name: 组件名称
            component_version: 组件版本
            license_name: 许可证名称

        Returns:
            AI 生成的使用目的建议
        """
        # TODO: 集成 LLM 生成更智能的建议
        # 目前返回一个基于组件名称的模板

        # 常见组件类型的用途模板
        purpose_templates = {
            "react": "用于构建用户界面的 JavaScript 库",
            "vue": "用于构建用户界面的渐进式 JavaScript 框架",
            "angular": "用于构建 Web 应用的 TypeScript 框架",
            "express": "用于构建 Web 服务器和 API 的 Node.js 框架",
            "axios": "用于发送 HTTP 请求的 JavaScript 客户端",
            "lodash": "提供实用函数的 JavaScript 工具库",
            "typescript": "JavaScript 的超集，编译为纯 JavaScript",
            "webpack": "JavaScript 应用的模块打包工具",
            "babel": "JavaScript 编译器，用于将新语法转换为兼容版本",
            "eslint": "JavaScript 代码静态分析工具",
            "prettier": "代码格式化工具",
            "jest": "JavaScript 测试框架",
            "mocha": "JavaScript 测试运行器",
            "chai": "JavaScript 断言库",
            "moment": "日期处理库",
            "dayjs": "轻量级日期处理库",
            "underscore": "JavaScript 工具库",
        }

        # 匹配组件名称前缀
        name_lower = component_name.lower()
        for key, purpose in purpose_templates.items():
            if key in name_lower:
                return f"{purpose}。{license_name} 许可证。"

        # 默认模板
        return f"用于项目功能实现的第三方组件。{license_name} 许可证。"

    def get_batch_autofill(
        self,
        components: List[Dict[str, str]],
        system_name: str
    ) -> List[Dict[str, Any]]:
        """批量获取预填充数据

        Args:
            components: 组件列表，每个组件包含 name, version 字段
            system_name: 系统名称

        Returns:
            预填充数据列表
        """
        results = []

        for comp in components:
            name = comp.get("name", "")
            version = comp.get("version", "")

            # 1. 从 SPDX 预填充
            spdx_comp = SpdxComponent(
                name=name,
                version=version,
                license_concluded=comp.get("license_concluded", ""),
                download_location=comp.get("download_location", ""),
                license_info_from_files=comp.get("license_info_from_files"),
            )
            autofill_data = self.fill_from_spdx(spdx_comp)

            # 2. 从历史记录预填充（优先）
            history_data = self.fill_from_history(name, version)
            if history_data:
                # 历史记录优先，覆盖 SPDX 数据
                autofill_data.update(history_data)
                autofill_data["source"] = "history"
            else:
                autofill_data["source"] = "spdx"

            # 3. AI 辅助填写使用目的（如果还没有）
            if not autofill_data.get("purpose_of_use"):
                autofill_data["purpose_of_use_suggestion"] = self.fill_purpose_with_ai(
                    name, version, autofill_data.get("license_name", "")
                )

            # 4. 检查组件是否已法务审批通过
            is_approved = self.db.query(Component).filter(
                Component.name == name,
                Component.version == version,
                Component.is_approved == True
            ).first() is not None

            autofill_data["component_name"] = name
            autofill_data["component_version"] = version
            autofill_data["is_approved"] = is_approved

            results.append(autofill_data)

        return results


def get_auto_filler_service(db: Session) -> DeclarationAutoFiller:
    """获取自动填充服务实例"""
    return DeclarationAutoFiller(db)
