"""Check-list de lancement par projet

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-10 17:40:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('project_checklist',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], name=op.f('fk_project_checklist_project_id_project')),
    sa.ForeignKeyConstraint(['updated_by'], ['user.id'], name=op.f('fk_project_checklist_updated_by_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_project_checklist')),
    sa.UniqueConstraint('project_id', name=op.f('uq_project_checklist_project_id'))
    )


def downgrade() -> None:
    op.drop_table('project_checklist')
