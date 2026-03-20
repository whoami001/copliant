"""法务声明历史复用服务

查询组件的历史审批记录，帮助法务/R&D 快速复用已有声明。
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.legal_declaration import LegalDeclaration, UsageType, IsModified
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.component import Component
from app.schemas.legal_declaration import HistorySuggestion, HistorySuggestionResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DeclarationHistoryService:
    """法务声明历史查询服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_history_suggestions(
        self,
        component_id: int,
        limit: int = 5
    ) -> HistorySuggestionResponse:
        """获取组件的历史审批建议

        查询同一组件（name+version 匹配）在所有系统中的已批准声明。

        Args:
            component_id: 组件 ID
            limit: 返回结果数量限制

        Returns:
            历史建议响应
        """
        # 获取目标组件信息
        target_component = self.db.query(Component).filter(Component.id == component_id).first()
        if not target_component:
            return HistorySuggestionResponse(has_history=False, suggestions=[])

        # 查询同一组件名称 + 版本的历史声明
        query = (
            self.db.query(LegalDeclaration, ComplianceRecord, Component)
            .join(ComplianceRecord, LegalDeclaration.compliance_record_id == ComplianceRecord.id)
            .join(Component, ComplianceRecord.component_id == Component.id)
            .filter(
                and_(
                    Component.name == target_component.name,
                    Component.version == target_component.version,
                    ComplianceRecord.status == RecordStatus.APPROVED,
                    Component.id != component_id,  # 排除当前组件本身
                )
            )
            .order_by(ComplianceRecord.legal_approved_at.desc())
            .limit(limit)
        )

        results = query.all()
        suggestions = []

        # 批量获取审批人邮箱（避免 N+1 查询）
        legal_user_ids = list(set([record.approved_by_legal for _, record, _ in results if record.approved_by_legal]))
        users_map = {}
        if legal_user_ids:
            from app.models.user import User
            users = self.db.query(User).filter(User.id.in_(legal_user_ids)).all()
            users_map = {u.id: u.email for u in users}

        for decl, record, comp in results:
            # 获取审批人邮箱
            approved_by_email = users_map.get(record.approved_by_legal) if record.approved_by_legal else None

            suggestions.append(
                HistorySuggestion(
                    id=decl.id,
                    system_name=record.system_name,
                    license_name=decl.license_name,
                    purpose_of_use=decl.purpose_of_use,
                    usage_type=decl.usage_type.value,
                    is_modified=decl.is_modified.value,
                    approved_at=record.legal_approved_at or decl.submitted_at,
                    approved_by=approved_by_email,
                )
            )

        return HistorySuggestionResponse(
            has_history=len(suggestions) > 0,
            suggestions=suggestions,
        )

    def get_similar_declarations(
        self,
        license_name: str,
        usage_type: UsageType,
        limit: int = 3
    ) -> List[HistorySuggestion]:
        """获取相似声明（相同许可证 + 使用方式）

        用于帮助 R&D 参考类似的声明填写。

        Args:
            license_name: 许可证名称
            usage_type: 使用方式
            limit: 返回结果数量限制

        Returns:
            相似声明列表
        """
        query = (
            self.db.query(LegalDeclaration, ComplianceRecord, Component)
            .join(ComplianceRecord, LegalDeclaration.compliance_record_id == ComplianceRecord.id)
            .join(Component, ComplianceRecord.component_id == Component.id)
            .filter(
                and_(
                    LegalDeclaration.license_name == license_name,
                    LegalDeclaration.usage_type == usage_type,
                    ComplianceRecord.status == RecordStatus.APPROVED,
                )
            )
            .order_by(ComplianceRecord.legal_approved_at.desc())
            .limit(limit)
        )

        results = query.all()
        suggestions = []

        for decl, record, comp in results:
            suggestions.append(
                HistorySuggestion(
                    id=decl.id,
                    system_name=record.system_name,
                    license_name=decl.license_name,
                    purpose_of_use=decl.purpose_of_use,
                    usage_type=decl.usage_type.value,
                    is_modified=decl.is_modified.value,
                    approved_at=record.legal_approved_at or decl.submitted_at,
                    approved_by=None,
                )
            )

        return suggestions

    def count_component_approvals(self, component_id: int) -> int:
        """统计同一组件的批准数量

        Args:
            component_id: 组件 ID

        Returns:
            批准数量
        """
        target_component = self.db.query(Component).filter(Component.id == component_id).first()
        if not target_component:
            return 0

        count = (
            self.db.query(ComplianceRecord)
            .join(Component, ComplianceRecord.component_id == Component.id)
            .filter(
                and_(
                    Component.name == target_component.name,
                    Component.version == target_component.version,
                    ComplianceRecord.status == RecordStatus.APPROVED,
                    Component.id != component_id,
                )
            )
            .count()
        )

        return count


def get_declaration_history_service(db: Session) -> DeclarationHistoryService:
    """获取历史查询服务实例"""
    return DeclarationHistoryService(db)
