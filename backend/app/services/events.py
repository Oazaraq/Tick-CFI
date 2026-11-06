"""Événements métier. L'historique est toujours écrit (RG07) ; d'autres abonnés s'y branchent (emails au lot 3)."""
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.services import history


@dataclass
class Event:
    type: str
    project_id: int
    entity_type: str
    entity_id: int
    author_id: int | None
    details: list[dict] = field(default_factory=lambda: [{}])  # une entrée d'historique par élément
    meta: dict = field(default_factory=dict)  # contexte non historisé (ex. nouveau responsable)


_subscribers: list[Callable[[Session, Event], None]] = []


def subscribe(handler: Callable[[Session, Event], None]) -> Callable[[Session, Event], None]:
    _subscribers.append(handler)
    return handler


def emit(db: Session, event: Event) -> None:
    history.record(db, event)
    for handler in _subscribers:
        handler(db, event)
