"""Modèle de données complet (DFB Partie 2 + avenant 1), créé en une seule migration au lot 1."""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Horodatage stocké en UTC sans fuseau (portable SQLite/PostgreSQL), relu en UTC explicite."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None else None


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class User(Timestamped, Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True)
    notifications_enabled: Mapped[bool] = mapped_column(default=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class KanbanStatus(Base):
    __tablename__ = "kanban_status"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    label: Mapped[str] = mapped_column(String(60))
    position: Mapped[int]
    is_active_counted: Mapped[bool]


project_member = Table(
    "project_member",
    Base.metadata,
    Column("project_id", ForeignKey("project.id"), primary_key=True),
    Column("user_id", ForeignKey("user.id"), primary_key=True),
)


class Project(Timestamped, Base):
    __tablename__ = "project"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    status_id: Mapped[int] = mapped_column(ForeignKey("kanban_status.id"), index=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    start_date: Mapped[date | None]
    due_date: Mapped[date | None]
    end_date: Mapped[date | None]
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    blocked_since: Mapped[datetime | None] = mapped_column(UTCDateTime)
    position: Mapped[int] = mapped_column(default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)

    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    status: Mapped[KanbanStatus] = relationship()
    members: Mapped[list[User]] = relationship(secondary=project_member)

    @property
    def status_code(self) -> str:
        return self.status.code

    @property
    def status_label(self) -> str:
        return self.status.label


class Meeting(Base):
    __tablename__ = "meeting"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    meeting_date: Mapped[date]
    participants: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str] = mapped_column(Text)
    summary: Mapped[dict | None] = mapped_column(JSON)
    candidates: Mapped[list | None] = mapped_column(JSON)  # actions proposées par l'IA, en attente de validation
    provider: Mapped[str | None] = mapped_column(String(20))  # fournisseur IA de la dernière analyse
    status: Mapped[str] = mapped_column(String(20), default="processing")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Action(Timestamped, Base):
    __tablename__ = "action"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    due_date: Mapped[date | None] = mapped_column(index=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="todo", index=True)
    origin: Mapped[str] = mapped_column(String(10), default="manual")
    sourcing: Mapped[str] = mapped_column(String(10), default="internal", server_default="internal")  # avenant 3
    subcontractor: Mapped[str | None] = mapped_column(String(200))
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meeting.id"))
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    overdue_notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    assignee: Mapped[User | None] = relationship()
    project: Mapped[Project] = relationship()

    @property
    def project_title(self) -> str:
        return self.project.title


class Risk(Timestamped, Base):
    __tablename__ = "risk"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    mitigation: Mapped[str | None] = mapped_column(Text)
    probability: Mapped[str] = mapped_column(String(10))
    impact: Mapped[str] = mapped_column(String(10))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    status: Mapped[str] = mapped_column(String(20), default="open")

    owner: Mapped[User | None] = relationship()
    project: Mapped[Project] = relationship()


class DocumentLink(Base):
    __tablename__ = "document_link"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    label: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(1000))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    author: Mapped[User] = relationship()
    project: Mapped[Project] = relationship()


class Comment(Base):
    __tablename__ = "comment"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    edited_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    author: Mapped[User] = relationship()
    project: Mapped[Project] = relationship()


class HistoryEvent(Base):
    """Journal en ajout seul (RG08) : aucune route ni fonction de modification."""

    __tablename__ = "history_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int]
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    author: Mapped[User | None] = relationship()


class EmailLog(Base):
    __tablename__ = "email_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(300))
    event_type: Mapped[str] = mapped_column(String(50))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id"))
    status: Mapped[str] = mapped_column(String(10))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)



class ProjectFile(Base):
    """Fichier « en dur » (avenant 3), stocké dans le volume sous un nom aléatoire ; purgé après la livraison."""
    __tablename__ = "project_file"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))  # nom d'origine, nettoyé
    stored_name: Mapped[str] = mapped_column(String(64), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    uploader: Mapped[User | None] = relationship()

class ProjectChecklist(Base):
    """Check-list de lancement d'un projet : états des points du modèle, points ajoutés, calculateur (JSON).
    Le modèle lui-même vit dans le code (services/checklists.py) ; `revision` protège des écritures concurrentes."""
    __tablename__ = "project_checklist"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), unique=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(default=0)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    editor: Mapped[User | None] = relationship()


planning_dependency = Table(
    "planning_dependency",
    Base.metadata,
    Column("predecessor_id", ForeignKey("planning_item.id", ondelete="CASCADE"), primary_key=True),
    Column("successor_id", ForeignKey("planning_item.id", ondelete="CASCADE"), primary_key=True),
)


class PlanningItem(Timestamped, Base):
    """Avenants 1 et 3 : phases et jalons du Gantt, charge en j/h et dépendances."""

    __tablename__ = "planning_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), index=True)
    label: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10), default="phase")
    start_date: Mapped[date]
    end_date: Mapped[date]
    position: Mapped[int] = mapped_column(default=0)
    category: Mapped[str | None] = mapped_column(String(30))
    days_sold: Mapped[float | None]
    days_consumed: Mapped[float | None]

    project: Mapped[Project] = relationship()
    predecessors: Mapped[list["PlanningItem"]] = relationship(
        secondary=planning_dependency, back_populates="successors",
        primaryjoin=lambda: PlanningItem.id == planning_dependency.c.successor_id,
        secondaryjoin=lambda: PlanningItem.id == planning_dependency.c.predecessor_id)
    successors: Mapped[list["PlanningItem"]] = relationship(
        secondary=planning_dependency, back_populates="predecessors",
        primaryjoin=lambda: PlanningItem.id == planning_dependency.c.predecessor_id,
        secondaryjoin=lambda: PlanningItem.id == planning_dependency.c.successor_id)

    @property
    def predecessor_ids(self) -> list[int]:
        return sorted(p.id for p in self.predecessors)
