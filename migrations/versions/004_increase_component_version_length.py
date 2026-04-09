"""increase component version column length to 255

Revision ID: 004
Revises: 003_add_legal_declarations
Create Date: 2026-03-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003_add_legal_declarations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 增加 components.version 字段长度从 50 到 255
    # 用于支持包含 Git commit hash 的长版本号
    op.alter_column('components', 'version',
               existing_type=sa.String(length=50),
               type_=sa.String(length=255),
               existing_nullable=False)


def downgrade() -> None:
    # 回滚：将 version 字段长度恢复为 50
    # 注意：如果已有数据超过 50 字符，回滚会失败
    op.alter_column('components', 'version',
               existing_type=sa.String(length=255),
               type_=sa.String(length=50),
               existing_nullable=False)
