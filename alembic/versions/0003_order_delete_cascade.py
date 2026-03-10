"""Order delete cascade: commemorations удаляются вместе с заказом

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-10

"""
from alembic import op


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL: заменить FK order_id с SET NULL на CASCADE
    op.drop_constraint(
        'commemorations_order_id_fkey',
        'commemorations',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'commemorations_order_id_fkey',
        'commemorations',
        'orders',
        ['order_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(
        'commemorations_order_id_fkey',
        'commemorations',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'commemorations_order_id_fkey',
        'commemorations',
        'orders',
        ['order_id'],
        ['id'],
        ondelete='SET NULL',
    )
