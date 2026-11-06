"""Tâche des retards (DFB A.4) : une alerte par passage en retard (RG05), historisée à l'envoi.

Exécution quotidienne à OVERDUE_JOB_HOUR (scheduler) ou manuelle : `make overdue`.
"""
from sqlalchemy import select

from app import clock
from app.db import SessionLocal
from app.models import Action, Project
from app.services import notifications
from app.services.events import Event, emit
from app.services.projects import OPEN


def run() -> int:
    """Signale les actions ouvertes dont l'échéance est passée (pas celle du jour) ; renvoie leur nombre."""
    with SessionLocal() as db:
        overdue = db.scalars(select(Action).join(Project, Action.project_id == Project.id).where(
            Action.deleted_at.is_(None), Project.deleted_at.is_(None), Action.status.in_(OPEN),
            Action.due_date < clock.today(), Action.overdue_notified_at.is_(None))).all()
        for action in overdue:
            emit(db, Event("action_overdue", action.project_id, "action", action.id, None,
                           [{"label": action.title}], {"assignee_id": action.assignee_id}))
            action.overdue_notified_at = clock.now()
        db.commit()
        return len(overdue)


if __name__ == "__main__":
    count = run()
    notifications.flush()
    print(f"Actions signalées en retard : {count}")
