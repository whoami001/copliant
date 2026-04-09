"""
组件匹配服务

核心功能：
- 根据 name+version 匹配历史组件
- 支持模糊匹配（同名不同版本）
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.component import Component
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ComponentMatchService:
    """组件匹配服务"""

    def __init__(self, db: Session):
        self.db = db

    def find_exact_match(self, name: str, version: str) -> Optional[Component]:
        """
        查找完全匹配的组件

        Args:
            name: 组件名
            version: 版本号

        Returns:
            匹配的组件，未找到返回 None
        """
        component = (
            self.db.query(Component)
            .filter(Component.name == name, Component.version == version)
            .first()
        )

        if component:
            logger.info(f"找到完全匹配组件：{name}@{version}")
        else:
            logger.info(f"未找到完全匹配组件：{name}@{version}")

        return component

    def find_similar_matches(self, name: str, version: str, limit: int = 5) -> list[Component]:
        """
        查找相似组件（同名不同版本）

        Args:
            name: 组件名
            version: 版本号
            limit: 返回数量限制

        Returns:
            相似组件列表
        """
        components = (
            self.db.query(Component)
            .filter(Component.name == name, Component.version != version)
            .order_by(Component.created_at.desc())
            .limit(limit)
            .all()
        )

        if components:
            logger.info(f"找到 {len(components)} 个相似组件：{name}")
        else:
            logger.info(f"未找到相似组件：{name}")

        return components

    def check_duplicate(self, name: str, version: str) -> bool:
        """
        检查组件是否已存在

        Args:
            name: 组件名
            version: 版本号

        Returns:
            True 表示已存在（重复），False 表示不存在
        """
        exists = (
            self.db.query(Component)
            .filter(Component.name == name, Component.version == version)
            .first()
            is not None
        )
        return exists

    def get_match_result(self, name: str, version: str) -> Tuple[bool, Optional[Component], list[Component]]:
        """
        获取完整的匹配结果

        Args:
            name: 组件名
            version: 版本号

        Returns:
            (是否完全匹配，完全匹配的组件，相似组件列表)
        """
        exact_match = self.find_exact_match(name, version)
        similar_matches = []

        if not exact_match:
            similar_matches = self.find_similar_matches(name, version)

        return (exact_match is not None, exact_match, similar_matches)


def get_component_match_service(db: Session) -> ComponentMatchService:
    """获取组件匹配服务实例"""
    return ComponentMatchService(db)
