"""create notifications table

Revision ID: 008
Revises: 007
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建通知表
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False, comment='通知标题'),
        sa.Column('message', sa.Text(), nullable=False, comment='通知内容'),
        sa.Column('type', sa.String(50), nullable=False, comment='通知类型：security_rejected/legal_rejected/legal_denied/urgency_added'),
        sa.Column('related_record_id', sa.Integer(), sa.ForeignKey('compliance_records.id'), nullable=True, comment='关联的合规记录 ID'),
        sa.Column('is_read', sa.Boolean(), default=False, comment='是否已读'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )

    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_related_record_id', 'notifications', ['related_record_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_user_id')
    op.drop_index('ix_notifications_related_record_id')
    op.drop_table('notifications')
