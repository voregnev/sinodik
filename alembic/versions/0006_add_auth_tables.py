"""Add users and otp_codes tables for OTP-based authentication.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def _ensure_base_tables() -> None:
    """
    Идемпотентное создание таблиц авторизации.
    Безопасно при первичной установке и при повторном запуске.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="user"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "otp_codes" not in tables:
        op.create_table(
            "otp_codes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("code_hash", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_otp_codes_email", "otp_codes", ["email"])


def upgrade() -> None:
    _ensure_base_tables()


def downgrade() -> None:
    op.drop_index("ix_otp_codes_email", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")