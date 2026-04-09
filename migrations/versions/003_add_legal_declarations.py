"""Add legal_declarations table

Revision ID: 003_add_legal_declarations
Revises: 002
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_legal_declarations"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 先删除可能存在的枚举类型（处理事务回滚导致的残留）
    op.execute("DROP TYPE IF EXISTS usagetype CASCADE")
    op.execute("DROP TYPE IF EXISTS ismodified CASCADE")

    # 创建 legal_declarations 表
    # 使用 String 类型而非 ENUM，提高灵活性和 SQLite 兼容性
    op.create_table(
        "legal_declarations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("compliance_record_id", sa.Integer(), nullable=False),
        sa.Column("purpose_of_use", sa.String(length=500), nullable=False, comment="使用目的"),
        sa.Column("url_to_source", sa.String(length=500), nullable=False, comment="源代码下载位置"),
        sa.Column("license_info_url", sa.String(length=500), nullable=False, comment="许可证说明页面"),
        sa.Column("license_text_url", sa.String(length=500), nullable=False, comment="许可证全文 URL"),
        sa.Column("license_name", sa.String(length=100), nullable=False, comment="SPDX 许可证 ID"),
        sa.Column(
            "is_modified",
            sa.String(length=10),
            nullable=False,
            default="no",
            comment="是否修改"
        ),
        sa.Column(
            "usage_type",
            sa.String(length=50),
            nullable=False,
            comment="使用方式"
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, default=sa.func.now(), comment="提交时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now(), comment="更新时间"),
        sa.ForeignKeyConstraint(["compliance_record_id"], ["compliance_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("compliance_record_id", name="uq_legal_declaration_record"),
    )
    op.create_index(op.f("ix_legal_declarations_id"), "legal_declarations", ["id"], unique=False)
    op.create_index(
        op.f("ix_legal_declarations_compliance_record_id"),
        "legal_declarations",
        ["compliance_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_legal_declarations_compliance_record_id"), table_name="legal_declarations")
    op.drop_index(op.f("ix_legal_declarations_id"), table_name="legal_declarations")
    op.drop_table("legal_declarations")
