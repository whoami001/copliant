"""create urgencies table

Revision ID: 006
Revises: 005
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'urgencies',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('record_id', sa.Integer(), sa.ForeignKey('compliance_records.id'), nullable=False),
        sa.Column('urged_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('target_role', sa.String(20), nullable=False, comment='催促目标：security/legal'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )

    op.create_index('ix_urgencies_record_id', 'urgencies', ['record_id'])
    op.create_index('ix_urgencies_urged_by', 'urgencies', ['urged_by'])


def downgrade() -> None:
    op.drop_index('ix_urgencies_record_id')
    op.drop_index('ix_urgencies_urged_by')
    op.drop_table('urgencies')
