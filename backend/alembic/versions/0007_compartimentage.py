"""Compartimentage strict (décision du 06/11/2026). Les personnes qui travaillent déjà sur un projet entrent dans son équipe,
pour ne pas perdre la vue sur leur travail : responsables d'actions et de risques, créateur du projet (hors administrateur).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-06 10:00:00
"""
from alembic import op


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO project_member (project_id, user_id)
        SELECT DISTINCT w.project_id, w.user_id FROM (
            SELECT project_id, assignee_id AS user_id FROM action WHERE deleted_at IS NULL AND assignee_id IS NOT NULL
            UNION SELECT project_id, owner_id FROM risk WHERE owner_id IS NOT NULL
            UNION SELECT h.project_id, h.author_id FROM history_event h JOIN "user" u ON u.id = h.author_id
                  WHERE h.event_type = 'project_created' AND u.role != 'admin'
        ) w JOIN project p ON p.id = w.project_id
        WHERE w.user_id != p.owner_id
          AND NOT EXISTS (SELECT 1 FROM project_member m WHERE m.project_id = w.project_id AND m.user_id = w.user_id)
    """)


def downgrade() -> None:
    pass  # ajout de participants : rien à défaire sans perdre des choix faits depuis
