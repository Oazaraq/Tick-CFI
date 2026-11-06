from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Action, User
from app.permissions import Perm
from app.schemas import ActionCreate, ActionOut, ActionUpdate
from app.security import require
from app.services import actions as svc
from app.services import projects as project_svc

router = APIRouter(tags=["actions"])


def out(action: Action) -> ActionOut:
    return ActionOut.model_validate(action).model_copy(update={"is_overdue": svc.is_overdue(action)})


@router.get("/actions")
def search_actions(assignee_id: int | None = None, status: str | None = None, priority: str | None = None,
                   project_id: int | None = None, overdue: bool = False, unassigned: bool = False,
                   due_within_days: int | None = None, hide_closed: bool = False, inactive_assignee: bool = False,
                   no_due_date: bool = False, my_projects: bool = False,
                   user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[ActionOut]:
    found = svc.search(db, user, assignee_id=assignee_id, status=status, priority=priority, project_id=project_id,
                       overdue=overdue, unassigned=unassigned, due_within_days=due_within_days, hide_closed=hide_closed,
                       inactive_assignee=inactive_assignee, no_due_date=no_due_date, my_projects=my_projects)
    return [out(a) for a in found]


@router.get("/actions/me")
def my_actions(status: str | None = None, priority: str | None = None, project_id: int | None = None,
               hide_closed: bool = False, user: User = Depends(require(Perm.VIEW)),
               db: Session = Depends(get_db)) -> list[ActionOut]:
    found = svc.search(db, user, assignee_id=user.id, status=status, priority=priority, project_id=project_id,
                       hide_closed=hide_closed)
    return [out(a) for a in found]


@router.get("/projects/{project_id}/actions")
def list_project_actions(project_id: int, user: User = Depends(require(Perm.VIEW)),
                         db: Session = Depends(get_db)) -> list[ActionOut]:
    project = project_svc.get_project(db, project_id, user)
    return [out(a) for a in svc.list_for_project(db, project.id)]


@router.post("/projects/{project_id}/actions", status_code=201)
def create_action(project_id: int, body: ActionCreate, user: User = Depends(require(Perm.ACTION_WRITE)),
                  db: Session = Depends(get_db)) -> ActionOut:
    return out(svc.create_action(db, user, project_svc.get_project(db, project_id, user), body))


@router.patch("/actions/{action_id}")
def update_action(action_id: int, body: ActionUpdate, user: User = Depends(require(Perm.ACTION_WRITE)),
                  db: Session = Depends(get_db)) -> ActionOut:
    return out(svc.update_action(db, user, svc.get_action(db, action_id, user), body))


@router.delete("/actions/{action_id}", status_code=204)
def delete_action(action_id: int, user: User = Depends(require(Perm.ACTION_DELETE)),
                  db: Session = Depends(get_db)) -> None:
    svc.delete_action(db, user, svc.get_action(db, action_id, user))
