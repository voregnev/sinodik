"""Extend schema: position, need_receipt, ordered_at, nullable starts_at/expires_at

Revision ID: 0001
Revises:
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def _ensure_base_tables() -> None:
    """
    Fresh install safety: если таблиц ещё нет, создаём их с актуальной схемой.

    В старых БД 0001 предполагала уже существующие таблицы и делала ALTER.
    В новой БД Alembic идёт с нуля, поэтому сначала создаём каркас, а затем
    ниже выполняем те же ALTER‑операции (они станут no-op).
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "persons" not in tables:
        op.create_table(
            "persons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("canonical_name", sa.String(length=100), nullable=False, unique=True),
            sa.Column("genitive_name", sa.String(length=100), nullable=True),
            sa.Column("gender", sa.String(length=1), nullable=True),
            sa.Column("name_variants", sa.ARRAY(sa.String()), nullable=True),
            sa.Column("embedding", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "orders" not in tables:
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_email", sa.String(length=255), nullable=True),
            sa.Column("need_receipt", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("source_channel", sa.String(length=30), nullable=True),
            sa.Column("source_raw", sa.Text(), nullable=True),
            sa.Column("external_id", sa.String(length=100), nullable=True, unique=True),
            sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "commemorations" not in tables:
        op.create_table(
            "commemorations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("person_id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=True),
            sa.Column("order_type", sa.String(length=20), nullable=False),
            sa.Column("period_type", sa.String(length=30), nullable=False),
            sa.Column("prefix", sa.String(length=100), nullable=True),
            sa.Column("suffix", sa.String(length=100), nullable=True),
            sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("position", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["person_id"],
                ["persons.id"],
                ondelete="CASCADE",
                name="commemorations_person_id_fkey",
            ),
            sa.ForeignKeyConstraint(
                ["order_id"],
                ["orders.id"],
                ondelete="CASCADE",
                name="commemorations_order_id_fkey",
            ),
        )


def upgrade() -> None:
    # Создаём базовые таблицы, если их ещё нет (новая БД).
    _ensure_base_tables()

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    comm_cols = {c["name"] for c in inspector.get_columns("commemorations")}
    order_cols = {c["name"] for c in inspector.get_columns("orders")}

    # Commemoration: add position, make starts_at/expires_at nullable (только если ещё нет)
    if "position" not in comm_cols:
        op.add_column("commemorations", sa.Column("position", sa.Integer(), nullable=True))
    op.alter_column("commemorations", "starts_at", nullable=True)
    op.alter_column("commemorations", "expires_at", nullable=True)

    # Order: add need_receipt and editable ordered_at (только если ещё нет)
    if "need_receipt" not in order_cols:
        op.add_column(
            "orders",
            sa.Column("need_receipt", sa.Boolean(), nullable=False, server_default="false"),
        )
    if "ordered_at" not in order_cols:
        op.add_column(
            "orders",
            sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    # Restore NOT NULL constraint by filling NULLs first
    op.execute(
        "UPDATE commemorations SET starts_at = ordered_at WHERE starts_at IS NULL"
    )
    op.execute(
        "UPDATE commemorations SET expires_at = ordered_at WHERE expires_at IS NULL"
    )
    op.alter_column("commemorations", "starts_at", nullable=False)
    op.alter_column("commemorations", "expires_at", nullable=False)
    op.drop_column("commemorations", "position")
    op.drop_column("orders", "need_receipt")
    op.drop_column("orders", "ordered_at")
