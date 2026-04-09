"""add_component_special_requirements

Revision ID: 007
Revises: 006
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Component 表添加特殊使用要求字段
    op.add_column('components', sa.Column('special_requirements', sa.Text(), nullable=True,
                                          comment="特殊使用要求，如'修改后需开源'、'不可商业分发'"))

    # 2. Component 表添加需要补充信息的标记
    op.add_column('components', sa.Column('requires_additional_info', sa.Boolean(), nullable=False, server_default='false',
                                          comment="是否需要补充信息"))

    # 3. Component 表添加需要补充的字段列表（JSON）
    op.add_column('components', sa.Column('additional_info_fields', sa.JSON(), nullable=True,
                                          comment="需要补充的字段列表，如 ['security_review_notes', 'export_control_info']"))

    # 4. ComplianceRecord 添加审批人备注（要求补充信息时使用）
    op.add_column('compliance_records', sa.Column('rejection_reason', sa.Text(), nullable=True,
                                                  comment="驳回/要求补充的原因"))

    # 5. ComplianceRecord 添加需要补充的字段列表
    op.add_column('compliance_records', sa.Column('required_fields', sa.JSON(), nullable=True,
                                                  comment="审批人要求补充的字段列表"))


def downgrade() -> None:
    op.drop_column('compliance_records', 'required_fields')
    op.drop_column('compliance_records', 'rejection_reason')
    op.drop_column('components', 'additional_info_fields')
    op.drop_column('components', 'requires_additional_info')
    op.drop_column('components', 'special_requirements')
