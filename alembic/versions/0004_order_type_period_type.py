"""Add order_type and period_type to orders for refill from source_raw

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('order_type', sa.String(20), nullable=True))
    op.add_column('orders', sa.Column('period_type', sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'period_type')
    op.drop_column('orders', 'order_type')
