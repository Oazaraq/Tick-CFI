"""Actions d'un projet : RG05 (retard), RG16 (clôture), RG17 (responsable actif), RG18 (suppression logique)."""
from datetime import date, timedelta

from sqlalchemy import case, select
from sqlalchemy.orm import Session, aliased, contains_eager, joinedload

from app import clock
from app.models import Action, Project, User
from app.services import labels, teams, users
from app.services.changes import apply_changes
from app.services.errors import Invalid, NotFound
from app.services.events import Event, emit

CLOSED = ("done", "cancelled")


def is_overdue(action: Action, today: date | None = None) -> bool:
    """RG05 : échéance strictement passée (date de Paris) et action ni terminée ni annulée."""
    today = today or clock.today()
    return action.due_date is not None and action.due_date < today and action.status not in CLOSED


def get_action(db: Session, action_id: int, viewer: User) -> Action:
    action = db.get(Action, action_id)
    if action is None or action.deleted_at is not None or teams.hidden(db, action.project_id, viewer):
        raise NotFound("Action introuvable")
    return action


def list_for_project(db: Session, project_id: int) -> list[Action]:
    return list(db.scalars(
        select(Action).where(Action.project_id == project_id, Action.deleted_at.is_(None))
        .options(joinedload(Action.assignee)).order_by(Action.due_date.is_(None), Action.due_date, Action.id)))


_PRIORITY_RANK = case({"critical": 0, "high": 1, "medium": 2, "low": 3}, value=Action.priority, else_=4)


def search(db: Session, user: User, *, assignee_id=None, status=None, priority=None, project_id=None,
           overdue=False, unassigned=False, due_within_days=None, hide_closed=False, inactive_assignee=False,
           no_due_date=False, my_projects=False) -> list[Action]:
    """Liste transverse (Mes actions, « Voir tout » du dashboard), triée selon DFB §4.7 :
    échéance croissante (retards d'abord), puis priorité décroissante, sans échéance en dernier."""
    today = clock.today()
    q = (select(Action).join(Action.project).where(Action.deleted_at.is_(None), Project.deleted_at.is_(None),
                                                   teams.visible_to(user))
         .options(contains_eager(Action.project), joinedload(Action.assignee)))
    if hide_closed or overdue or unassigned or inactive_assignee or no_due_date or due_within_days is not None:
        q = q.where(Action.status.not_in(CLOSED))  # les alertes ne portent que sur les actions ouvertes
    if assignee_id:
        q = q.where(Action.assignee_id == assignee_id)
    if status:
        q = q.where(Action.status == status)
    if priority:
        q = q.where(Action.priority == priority)
    if project_id:
        q = q.where(Action.project_id == project_id)
    if overdue:
        q = q.where(Action.due_date < today)
    if due_within_days is not None:
        q = q.where(Action.due_date >= today, Action.due_date < today + timedelta(days=due_within_days))
    if unassigned:
        q = q.where(Action.assignee_id.is_(None))
    if no_due_date:
        q = q.where(Action.due_date.is_(None))
    if inactive_assignee:
        assignee = aliased(User)
        q = q.join(assignee, Action.assignee_id == assignee.id).where(assignee.is_active.is_(False))
    if my_projects:
        q = q.where(teams.my_projects(user))
    return list(db.scalars(q.order_by(Action.due_date.is_(None), Action.due_date, _PRIORITY_RANK, Action.id)).unique())


def _set_status(action: Action, new: str) -> None:
    """RG16 : closed_at à la clôture ; à la réouverture, closed_at et overdue_notified_at sont vidés."""
    old = action.status
    action.status = new
    if new in CLOSED and old not in CLOSED:
        action.closed_at = clock.now()
    elif new not in CLOSED and old in CLOSED:
        action.closed_at = action.overdue_notified_at = None


def _meta(action: Action) -> dict:
    return {"assignee_id": action.assignee_id}


def create_action(db: Session, actor: User | None, project: Project, data, origin: str = "manual",
                  meeting_id: int | None = None, commit: bool = True) -> Action:
    title = data.title.strip()
    if not title:
        raise Invalid("Le titre est obligatoire")
    teams.require_member(project, data.assignee_id, "Le responsable de l'action")
    action = Action(project_id=project.id, title=title, description=data.description, due_date=data.due_date,
                    priority=data.priority, origin=origin, meeting_id=meeting_id, sourcing=data.sourcing,
                    subcontractor=(data.subcontractor or "").strip() or None if data.sourcing == "external" else None,
                    assignee=users.assignable(db, data.assignee_id) if data.assignee_id else None)
    _set_status(action, data.status)
    db.add(action)
    db.flush()
    emit(db, Event("action_created", project.id, "action", action.id, actor.id if actor else None,
                   [{"label": action.title}], _meta(action)))
    if commit:  # sinon l'appelant valide un lot d'actions en une seule transaction (validation d'une réunion)
        db.commit()
    return action


def update_action(db: Session, actor: User, action: Action, data) -> Action:
    sent = data.model_fields_set
    changes = apply_changes(action, data, ("title", "description", "priority", "due_date", "sourcing", "subcontractor"),
                            required=("title", "priority", "sourcing"))
    if action.sourcing == "internal":
        action.subcontractor = None  # le sous-traitant n'a de sens que pour une action externe
    if any(c["field"] == "due_date" for c in changes) and (action.due_date is None or action.due_date >= clock.today()):
        action.overdue_notified_at = None  # A.4 : échéance repoussée, l'alerte pourra repartir
    if "assignee_id" in sent and data.assignee_id != action.assignee_id:
        teams.require_member(action.project, data.assignee_id, "Le responsable de l'action")
        assignee = users.assignable(db, data.assignee_id) if data.assignee_id else None
        changes.append({"field": "assignee", "old": action.assignee.full_name if action.assignee else "",
                        "new": assignee.full_name if assignee else ""})
        action.assignee = assignee
    status_detail = None
    if "status" in sent and data.status and data.status != action.status:
        status_detail = {"field": "status", "old": labels.ACTION_STATUS[action.status],
                         "new": labels.ACTION_STATUS[data.status], "label": action.title}
        _set_status(action, data.status)
    db.flush()
    if changes:
        emit(db, Event("action_updated", action.project_id, "action", action.id, actor.id,
                       [{**c, "label": action.title} for c in changes], _meta(action)))
    if status_detail:
        emit(db, Event("action_status_changed", action.project_id, "action", action.id, actor.id,
                       [status_detail], _meta(action)))
    db.commit()
    return action


def delete_action(db: Session, actor: User, action: Action) -> None:
    action.deleted_at = clock.now()
    emit(db, Event("action_deleted", action.project_id, "action", action.id, actor.id, [{"label": action.title}]))
    db.commit()
