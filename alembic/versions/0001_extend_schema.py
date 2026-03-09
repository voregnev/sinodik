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


def upgrade() -> None:
    # Commemoration: add position, make starts_at/expires_at nullable
    op.add_column('commemorations', sa.Column('position', sa.Integer(), nullable=True))
    op.alter_column('commemorations', 'starts_at', nullable=True)
    op.alter_column('commemorations', 'expires_at', nullable=True)

    # Order: add need_receipt and editable ordered_at
    op.add_column('orders', sa.Column(
        'need_receipt', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('orders', sa.Column(
        'ordered_at', sa.DateTime(timezone=True), nullable=True
    ))


def downgrade() -> None:
    # Restore NOT NULL constraint by filling NULLs first
    op.execute(
        "UPDATE commemorations SET starts_at = ordered_at WHERE starts_at IS NULL"
    )
    op.execute(
        "UPDATE commemorations SET expires_at = ordered_at WHERE expires_at IS NULL"
    )
    op.alter_column('commemorations', 'starts_at', nullable=False)
    op.alter_column('commemorations', 'expires_at', nullable=False)
    op.drop_column('commemorations', 'position')
    op.drop_column('orders', 'need_receipt')
    op.drop_column('orders', 'ordered_at')
