"""Historique en ajout seul (RG07, RG08) : aucune fonction de modification ni de suppression."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import APP_TZ
from app.models import HistoryEvent


def record(db: Session, event) -> None:
    """Une entrée par élément de `event.details` (ex. un champ modifié)."""
    for detail in event.details:
        db.add(HistoryEvent(project_id=event.project_id, event_type=event.type, entity_type=event.entity_type,
                            entity_id=event.entity_id, detail=detail, author_id=event.author_id))


def _paris_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=APP_TZ)


def list_history(db: Session, project_id: int, event_type: str | None = None, author_id: int | None = None,
                 date_from: date | None = None, date_to: date | None = None) -> list[HistoryEvent]:
    q = (select(HistoryEvent).where(HistoryEvent.project_id == project_id).options(joinedload(HistoryEvent.author))
         .order_by(HistoryEvent.created_at.desc(), HistoryEvent.id.desc()))
    if event_type:
        q = q.where(HistoryEvent.event_type == event_type)
    if author_id:
        q = q.where(HistoryEvent.author_id == author_id)
    if date_from:
        q = q.where(HistoryEvent.created_at >= _paris_midnight(date_from))
    if date_to:
        q = q.where(HistoryEvent.created_at < _paris_midnight(date_to + timedelta(days=1)))
    return list(db.scalars(q))
