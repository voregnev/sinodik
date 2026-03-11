"""Add suffix column; extend prefix to 100 chars for double prefixes

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    comm_cols = {c["name"]: c for c in inspector.get_columns("commemorations")}

    # suffix: только если колонки ещё нет (в свежей БД она уже есть из 0001)
    if "suffix" not in comm_cols:
        op.add_column("commemorations", sa.Column("suffix", sa.String(100), nullable=True))

    # prefix: расширяем до 100 символов только если сейчас 50
    if "prefix" in comm_cols:
        pref_type = comm_cols["prefix"]["type"]
        if getattr(pref_type, "length", None) == 50:
            op.alter_column(
                "commemorations", "prefix",
                existing_type=sa.String(50),
                type_=sa.String(100),
                nullable=True,
            )


def downgrade() -> None:
    op.alter_column(
        'commemorations', 'prefix',
        existing_type=sa.String(100),
        type_=sa.String(50),
        nullable=True,
    )
    op.drop_column('commemorations', 'suffix')
