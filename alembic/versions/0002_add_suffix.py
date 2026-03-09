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
    # suffix: "со чадом", "со чады" — postfix preserved from source text
    op.add_column('commemorations', sa.Column('suffix', sa.String(100), nullable=True))

    # prefix: extend from VARCHAR(50) to VARCHAR(100) to fit double prefixes
    # e.g. "иер. уб." or "нпр. т.б."
    op.alter_column(
        'commemorations', 'prefix',
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
