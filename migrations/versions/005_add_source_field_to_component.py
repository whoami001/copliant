"""add source field to component

Revision ID: 005
Revises: 004_increase_component_version_length
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 source 字段，默认值为 'blackduck'
    op.add_column('components', sa.Column('source', sa.String(50), nullable=False, server_default='blackduck', comment='组件来源：blackduck/manual/import'))


def downgrade() -> None:
    op.drop_column('components', 'source')
