"""Avenant 2 : quatre statuts (Avant-vente, En cours, Bloqué, Livré) ; les projets existants sont reclassés.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

status = sa.table("kanban_status", sa.column("id", sa.Integer), sa.column("code", sa.String),
                  sa.column("label", sa.String), sa.column("position", sa.Integer),
                  sa.column("is_active_counted", sa.Boolean))
project = sa.table("project", sa.column("status_id", sa.Integer))

NEW = [("presale", "Avant-vente", False), ("in_progress", "En cours", True),
       ("blocked", "Bloqué", True), ("done", "Livré", False)]
OLD = [("idea", "Idée", False), ("to_launch", "À lancer", True), ("study", "En étude", True),
       ("in_progress", "En cours", True), ("blocked", "Bloqué", True),
       ("validation", "En cours de validation", True), ("done", "Terminé", False)]
MERGED = {"to_launch": "presale", "study": "presale", "validation": "in_progress"}


def _apply(conn, statuses) -> None:
    existing = {code for (code,) in conn.execute(sa.select(status.c.code))}
    for position, (code, label, counted) in enumerate(statuses):
        values = {"label": label, "position": position, "is_active_counted": counted}
        if code in existing:
            conn.execute(status.update().where(status.c.code == code).values(**values))
        else:
            conn.execute(status.insert().values(code=code, **values))


def upgrade() -> None:
    conn = op.get_bind()
    # « Idée » devient « Avant-vente » en gardant son id : ses projets suivent sans mise à jour
    conn.execute(status.update().where(status.c.code == "idea").values(code="presale"))
    ids = {code: id_ for id_, code in conn.execute(sa.select(status.c.id, status.c.code))}
    for old, new in MERGED.items():
        if old in ids:
            conn.execute(project.update().where(project.c.status_id == ids[old]).values(status_id=ids[new]))
            conn.execute(status.delete().where(status.c.id == ids[old]))
    _apply(conn, NEW)


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(status.update().where(status.c.code == "presale").values(code="idea"))
    _apply(conn, OLD)
