"""Initial migration - create all tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    # Create components table
    op.create_table(
        "components",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("license", sa.String(length=100), nullable=True),
        sa.Column("copyright", sa.Text(), nullable=True),
        sa.Column("usage_type", sa.String(length=50), nullable=True),
        sa.Column("license_risk_level", sa.String(length=20), nullable=True),
        sa.Column("black_duck_report_id", sa.String(length=100), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=True, default=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_component_name_version"),
    )
    op.create_index(op.f("ix_components_id"), "components", ["id"], unique=False)
    op.create_index(op.f("ix_components_name"), "components", ["name"], unique=False)
    op.create_index(op.f("ix_components_name_version"), "components", ["name", "version"], unique=False)

    # Create compliance_records table
    op.create_table(
        "compliance_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("system_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("filled_by", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by_security", sa.Integer(), nullable=True),
        sa.Column("security_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by_legal", sa.Integer(), nullable=True),
        sa.Column("legal_approved_at", sa.DateTime(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"]),
        sa.ForeignKeyConstraint(["filled_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_security"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_legal"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compliance_records_id"), "compliance_records", ["id"], unique=False)
    op.create_index(op.f("ix_compliance_records_component_id"), "compliance_records", ["component_id"], unique=False)
    op.create_index(op.f("ix_compliance_records_status"), "compliance_records", ["status"], unique=False)
    op.create_index(op.f("ix_compliance_records_system_name"), "compliance_records", ["system_name"], unique=False)

    # Create approval_history table
    op.create_table(
        "approval_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("actor", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("ip_address", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor"], ["users.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["compliance_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_history_id"), "approval_history", ["id"], unique=False)
    op.create_index(op.f("ix_approval_history_record_id"), "approval_history", ["record_id"], unique=False)
    op.create_index(op.f("ix_approval_history_created_at"), "approval_history", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("approval_history")
    op.drop_table("compliance_records")
    op.drop_table("components")
    op.drop_table("users")
