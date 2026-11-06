"""Dashboard (DFB §4.8) : 5 tuiles, 4 zones d'alerte limitées à 10 éléments, actions sans échéance (RG13),
et graphiques de l'état du jour (avenant 3)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import clock
from app.config import settings
from app.models import Action, KanbanStatus, PlanningItem, Project, User
from app.services import actions as action_svc
from app.services.teams import my_projects, visible_to
from app.services.projects import OPEN

ZONE_SIZE = 10


def _zone(items: list) -> dict:
    return {"total": len(items), "items": items[:ZONE_SIZE]}


PRIORITIES = ("critical", "high", "medium", "low")
CHART_SIZE = 8  # projets affichés dans les graphiques par projet


def charts(db: Session, scope) -> dict:
    """État du jour, dans le périmètre choisi (tous les projets ou les miens)."""
    statuses = db.scalars(select(KanbanStatus).order_by(KanbanStatus.position)).all()
    by_status = dict(db.execute(select(Project.status_id, func.count()).where(Project.id.in_(scope))
                                .group_by(Project.status_id)).all())
    open_actions = (Action.deleted_at.is_(None), Action.status.in_(OPEN), Action.project_id.in_(scope))
    by_priority = dict(db.execute(select(Action.priority, func.count()).where(*open_actions).group_by(Action.priority)).all())
    late = func.count(Action.id)
    overdue = db.execute(select(Project.id, Project.title, late).join(Action, Action.project_id == Project.id)
                         .where(*open_actions, Action.due_date < clock.today())
                         .group_by(Project.id, Project.title).order_by(late.desc(), Project.title).limit(CHART_SIZE)).all()
    sold, consumed = func.coalesce(func.sum(PlanningItem.days_sold), 0), func.coalesce(func.sum(PlanningItem.days_consumed), 0)
    effort = db.execute(select(Project.id, Project.title, sold, consumed)
                        .join(PlanningItem, PlanningItem.project_id == Project.id)
                        .join(KanbanStatus, Project.status_id == KanbanStatus.id)
                        .where(Project.id.in_(scope), KanbanStatus.code != "done")
                        .group_by(Project.id, Project.title).having(or_(sold > 0, consumed > 0))
                        .order_by(sold.desc(), Project.title)).all()
    return {
        "projects_by_status": [{"code": s.code, "label": s.label, "count": by_status.get(s.id, 0)} for s in statuses],
        "actions_by_priority": [{"code": p, "count": by_priority.get(p, 0)} for p in PRIORITIES],
        "overdue_by_project": [{"project_id": i, "title": t, "count": n} for i, t, n in overdue],
        "effort_by_project": [{"project_id": i, "title": t, "sold": float(s), "consumed": float(c)} for i, t, s, c in effort],
    }


def build(db: Session, user: User, mine: bool) -> dict:
    scope = select(Project.id).where(Project.deleted_at.is_(None), visible_to(user))  # RG18 + compartimentage
    if mine:
        scope = scope.where(my_projects(user))

    def count(query) -> int:
        return db.scalar(select(func.count()).select_from(query.subquery()))

    projects = select(Project.id).join(KanbanStatus, Project.status_id == KanbanStatus.id).where(Project.id.in_(scope))
    open_actions = select(Action.id).where(Action.deleted_at.is_(None), Action.status.in_(OPEN), Action.project_id.in_(scope))
    all_projects = select(Project.id).where(Project.deleted_at.is_(None), visible_to(user))
    tiles = {
        "active_projects": count(projects.where(KanbanStatus.is_active_counted.is_(True))),  # RG20
        "open_actions": count(open_actions),
        "overdue_actions": count(open_actions.where(Action.due_date < clock.today())),  # RG05
        "blocked_projects": count(projects.where(KanbanStatus.code == "blocked")),
        "my_actions": count(select(Action.id).where(Action.deleted_at.is_(None), Action.status.in_(OPEN),
                                                     Action.assignee_id == user.id, Action.project_id.in_(all_projects))),
    }
    blocked = list(db.scalars(select(Project).join(KanbanStatus, Project.status_id == KanbanStatus.id)
                              .where(Project.id.in_(scope), KanbanStatus.code == "blocked").order_by(Project.blocked_since)))

    def search(**filters) -> list[Action]:
        return action_svc.search(db, user, my_projects=mine, **filters)

    return {
        "tiles": tiles,
        "due_soon": _zone(search(due_within_days=settings.due_soon_days)),
        "blocked_projects": _zone(blocked),
        "unassigned": _zone(search(unassigned=True)),
        "inactive_assignee": _zone(search(inactive_assignee=True)),
        "no_due_date": len(search(no_due_date=True)),
        "charts": charts(db, scope),
    }
