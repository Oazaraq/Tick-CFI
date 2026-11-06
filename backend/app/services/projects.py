"""Projets : Kanban, déplacements (RG03, RG14, RG15), modification historisée, suppression logique (RG18)."""
from datetime import timedelta

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app import clock
from app.config import settings
from app.models import Action, KanbanStatus, PlanningItem, Project, Risk, User
from app.permissions import sees_all_projects
from app.services import labels, teams, users
from app.services.errors import ConfirmationRequired, Invalid
from app.services.events import Event, emit

OPEN = ("todo", "in_progress", "blocked")
CLOSED = ("done", "cancelled")
EMPTY_COUNTERS = {"actions_total": 0, "actions_done": 0, "actions_overdue": 0, "actions_open": 0,
                  "days_sold": 0, "days_consumed": 0}


def status_by_code(db: Session, code: str) -> KanbanStatus:
    status = db.scalar(select(KanbanStatus).where(KanbanStatus.code == code))
    if status is None:
        raise Invalid("Statut inconnu")
    return status


def get_project(db: Session, project_id: int, viewer: User) -> Project:
    return teams.visible_project(db, project_id, viewer)


def counters(db: Session, project_ids: list[int]) -> dict[int, dict]:
    """Compteurs d'actions de plusieurs projets en une requête (pas de N+1)."""
    if not project_ids:
        return {}
    late = and_(Action.due_date < clock.today(), Action.status.not_in(CLOSED))
    rows = db.execute(
        select(Action.project_id, func.count(), func.sum(case((Action.status == "done", 1), else_=0)),
               func.sum(case((late, 1), else_=0)), func.sum(case((Action.status.in_(OPEN), 1), else_=0)))
        .where(Action.deleted_at.is_(None), Action.project_id.in_(project_ids))
        .group_by(Action.project_id))
    result = {pid: {**EMPTY_COUNTERS, "actions_total": total, "actions_done": done or 0,
                    "actions_overdue": overdue or 0, "actions_open": open_ or 0}
              for pid, total, done, overdue, open_ in rows}
    effort = db.execute(select(PlanningItem.project_id, func.sum(PlanningItem.days_sold), func.sum(PlanningItem.days_consumed))
                        .where(PlanningItem.project_id.in_(project_ids)).group_by(PlanningItem.project_id))
    for pid, sold, consumed in effort:  # avenant 3 : j/h vendus et consommés, somme des phases
        result.setdefault(pid, dict(EMPTY_COUNTERS)).update(days_sold=sold or 0, days_consumed=consumed or 0)
    return result


def list_projects(db: Session, user: User, *, q=None, owner_id=None, member_id=None, priority=None, status=None,
                  blocked=False, has_overdue=False, mine=False, include_old_done=False,
                  active=False) -> list[tuple[Project, dict]]:
    query = (select(Project).join(Project.status).where(Project.deleted_at.is_(None), teams.visible_to(user))
             .options(contains_eager(Project.status), joinedload(Project.owner)))
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Project.title.ilike(like), Project.description.ilike(like)))
    if owner_id:
        query = query.where(Project.owner_id == owner_id)
    if member_id:
        query = query.where(Project.members.any(User.id == member_id))
    if priority:
        query = query.where(Project.priority == priority)
    if status:
        query = query.where(KanbanStatus.code == status)
    if blocked:
        query = query.where(KanbanStatus.code == "blocked")
    if active:  # tuile « Projets actifs » (RG20)
        query = query.where(KanbanStatus.is_active_counted.is_(True))
    if mine:
        query = query.where(or_(Project.owner_id == user.id, Project.members.any(User.id == user.id)))
    if not include_old_done:  # colonne « Terminé » : DONE_HIDE_DAYS derniers jours
        limit = clock.today() - timedelta(days=settings.done_hide_days)
        query = query.where(or_(KanbanStatus.code != "done", Project.end_date.is_(None), Project.end_date >= limit))
    projects = list(db.scalars(query.order_by(KanbanStatus.position, Project.position, Project.id)).unique())
    stats = counters(db, [p.id for p in projects])
    rows = [(p, stats.get(p.id, EMPTY_COUNTERS)) for p in projects]
    return [r for r in rows if r[1]["actions_overdue"]] if has_overdue else rows


def _members(db: Session, ids: list[int]) -> list[User]:
    found = list(db.scalars(select(User).where(User.id.in_(ids)))) if ids else []
    if len(found) != len(set(ids)):
        raise Invalid("Participant inconnu")
    return found


def _check_removable(db: Session, project: Project, removed: set[int]) -> None:
    """Compartimentage : qui porte encore une action ou un risque ouverts reste dans l'équipe (sinon il ne verrait plus son travail)."""
    if not removed:
        return
    busy = db.scalars(select(User).where(User.id.in_(removed), or_(
        User.id.in_(select(Action.assignee_id).where(Action.project_id == project.id, Action.deleted_at.is_(None),
                                                     Action.status.in_(OPEN))),
        User.id.in_(select(Risk.owner_id).where(Risk.project_id == project.id, Risk.status != "closed"))))).all()
    if busy:
        raise Invalid(f"Réaffectez d'abord les actions et risques ouverts de {_names(list(busy))} : "
                      "un membre qui porte du travail ouvert ne peut pas quitter l'équipe")


def _names(people: list[User]) -> str:
    return ", ".join(sorted(u.full_name for u in people))


def _check_dates(start, due) -> None:
    if start and due and due < start:
        raise Invalid("La date de fin prévue doit être postérieure à la date de début")


def _set_status(project: Project, new: KanbanStatus, reason: str | None) -> None:
    """RG03 (motif et date de blocage) et RG15 (date de fin réelle)."""
    old = project.status.code if project.status else None
    if new.code == "blocked":
        if not (reason or "").strip():
            raise Invalid("Le motif de blocage est obligatoire")
        project.blocked_reason, project.blocked_since = reason.strip(), clock.now()
    elif old == "blocked":
        project.blocked_reason = project.blocked_since = None
    if new.code == "done":
        project.end_date = clock.today()
    elif old == "done":
        project.end_date = None
    project.status = new


def _place(db: Session, project: Project, status_id: int, position: int | None) -> None:
    """Range la carte dans sa colonne (fin de colonne par défaut) et renumérote la colonne (Q17)."""
    siblings = list(db.scalars(select(Project).where(Project.status_id == status_id, Project.deleted_at.is_(None),
                                                     Project.id != project.id).order_by(Project.position, Project.id)))
    index = len(siblings) if position is None else max(0, min(position, len(siblings)))
    siblings.insert(index, project)
    for i, item in enumerate(siblings):
        item.position = i


def create_project(db: Session, actor: User, data) -> Project:
    _check_dates(data.start_date, data.due_date)
    title = data.title.strip()
    if not title:
        raise Invalid("Le titre est obligatoire")
    project = Project(title=title, description=data.description, owner=users.assignable(db, data.owner_id),
                      priority=data.priority, start_date=data.start_date, due_date=data.due_date,
                      members=_members(db, data.member_ids))
    if not sees_all_projects(actor) and actor.id not in teams.team_ids(project):
        project.members.append(actor)  # le créateur garde la vue sur le projet qu'il vient de créer
    status = status_by_code(db, data.status_code)
    _set_status(project, status, data.blocked_reason)
    _place(db, project, status.id, None)
    db.add(project)
    db.flush()
    emit(db, Event("project_created", project.id, "project", project.id, actor.id, [{"label": project.title}]))
    db.commit()
    return project


def update_project(db: Session, actor: User, project: Project, data) -> Project:
    """Champs et participants ; le statut passe uniquement par move_project."""
    sent = data.model_fields_set
    changes = []
    old_team = teams.team_ids(project)
    for field in ("title", "description", "priority", "start_date", "due_date"):
        if field not in sent:
            continue
        new = getattr(data, field)
        if field == "title":
            new = (new or "").strip()
        if field in ("title", "priority") and not new:
            raise Invalid("Le titre et la priorité sont obligatoires")
        old = getattr(project, field)
        if new != old:
            setattr(project, field, new)
            changes.append({"field": field, "old": labels.fmt(field, old), "new": labels.fmt(field, new)})
    if "owner_id" in sent and data.owner_id != project.owner_id:
        if data.owner_id is None:
            raise Invalid("Le responsable est obligatoire")
        owner = users.assignable(db, data.owner_id)
        changes.append({"field": "owner", "old": project.owner.full_name, "new": owner.full_name})
        project.owner = owner
    if "member_ids" in sent:
        members = _members(db, data.member_ids or [])
        if {u.id for u in members} != {u.id for u in project.members}:
            changes.append({"field": "members", "old": _names(project.members), "new": _names(members)})
            project.members = members
    _check_dates(project.start_date, project.due_date)
    _check_removable(db, project, old_team - teams.team_ids(project))
    if changes:
        emit(db, Event("project_updated", project.id, "project", project.id, actor.id, changes))
    db.commit()
    return project


def move_project(db: Session, actor: User, project: Project, data) -> Project:
    new, old = status_by_code(db, data.status_code), project.status
    if new.id != old.id:
        if new.code == "done":  # RG14
            open_count = db.scalar(select(func.count()).select_from(Action).where(
                Action.project_id == project.id, Action.deleted_at.is_(None), Action.status.in_(OPEN)))
            if open_count and not data.confirm:
                raise ConfirmationRequired(f"{open_count} action(s) ouverte(s)", code="open_actions", count=open_count)
        _set_status(project, new, data.blocked_reason)
        detail = {"field": "status", "old": old.label, "new": new.label}
        if new.code == "blocked":
            detail["reason"] = project.blocked_reason
        emit(db, Event("project_status_changed", project.id, "project", project.id, actor.id, [detail]))
    _place(db, project, new.id, data.position)  # réordonner dans une colonne n'est pas historisé
    db.commit()
    return project


def delete_project(db: Session, actor: User, project: Project) -> None:
    project.deleted_at = clock.now()
    emit(db, Event("project_deleted", project.id, "project", project.id, actor.id, [{"label": project.title}]))
    db.commit()
