"""Lot 4 : fichiers « en dur » des projets (avenant 3)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05 17:21:56.416128
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('project_file',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('stored_name', sa.String(length=64), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], name=op.f('fk_project_file_project_id_project')),
    sa.ForeignKeyConstraint(['uploaded_by'], ['user.id'], name=op.f('fk_project_file_uploaded_by_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_project_file')),
    sa.UniqueConstraint('stored_name', name=op.f('uq_project_file_stored_name'))
    )
    with op.batch_alter_table('project_file', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_file_project_id'), ['project_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('project_file', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_project_file_project_id'))

    op.drop_table('project_file')
