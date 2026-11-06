"""Statuts Kanban initiaux (DFB Partie 2). Le code métier ne référence que `code`, jamais `label`.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

STATUSES = [
    ("idea", "Idée", False),
    ("to_launch", "À lancer", True),
    ("study", "En étude", True),
    ("in_progress", "En cours", True),
    ("blocked", "Bloqué", True),
    ("validation", "En cours de validation", True),
    ("done", "Terminé", False),
]


def upgrade() -> None:
    table = sa.table("kanban_status", sa.column("code", sa.String), sa.column("label", sa.String),
                     sa.column("position", sa.Integer), sa.column("is_active_counted", sa.Boolean))
    op.bulk_insert(table, [{"code": c, "label": lbl, "position": i, "is_active_counted": counted}
                           for i, (c, lbl, counted) in enumerate(STATUSES)])


def downgrade() -> None:
    op.execute("DELETE FROM kanban_status")
