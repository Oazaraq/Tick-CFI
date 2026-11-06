"""Lot 3 IA : actions candidates et fournisseur de la dernière analyse

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-04 23:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('meeting', schema=None) as batch_op:
        batch_op.add_column(sa.Column('candidates', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('provider', sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('meeting', schema=None) as batch_op:
        batch_op.drop_column('provider')
        batch_op.drop_column('candidates')
