from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project, User
from app.permissions import Perm
from app.schemas import HistoryOut, ProjectCard, ProjectCreate, ProjectMove, ProjectOut, ProjectUpdate
from app.security import require
from app.services import history as history_svc
from app.services import projects as svc

router = APIRouter(prefix="/projects", tags=["projects"])


def detail(db: Session, project: Project) -> ProjectOut:
    stats = svc.counters(db, [project.id]).get(project.id, svc.EMPTY_COUNTERS)
    return ProjectOut.model_validate(project).model_copy(update=stats)


@router.get("")
def list_projects(q: str | None = None, owner_id: int | None = None, member_id: int | None = None,
                  priority: str | None = None, status: str | None = None, blocked: bool = False,
                  has_overdue: bool = False, mine: bool = False, include_old_done: bool = False, active: bool = False,
                  user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[ProjectCard]:
    rows = svc.list_projects(db, user, q=q, owner_id=owner_id, member_id=member_id, priority=priority, status=status,
                             blocked=blocked, has_overdue=has_overdue, mine=mine, include_old_done=include_old_done,
                             active=active)
    return [ProjectCard.model_validate(p).model_copy(update=stats) for p, stats in rows]


@router.post("", status_code=201)
def create_project(body: ProjectCreate, user: User = Depends(require(Perm.PROJECT_WRITE)),
                   db: Session = Depends(get_db)) -> ProjectOut:
    return detail(db, svc.create_project(db, user, body))


@router.get("/{project_id}")
def get_project(project_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> ProjectOut:
    return detail(db, svc.get_project(db, project_id, user))


@router.patch("/{project_id}")
def update_project(project_id: int, body: ProjectUpdate, user: User = Depends(require(Perm.PROJECT_WRITE)),
                   db: Session = Depends(get_db)) -> ProjectOut:
    return detail(db, svc.update_project(db, user, svc.get_project(db, project_id, user), body))


@router.post("/{project_id}/move")
def move_project(project_id: int, body: ProjectMove, user: User = Depends(require(Perm.PROJECT_WRITE)),
                 db: Session = Depends(get_db)) -> ProjectOut:
    return detail(db, svc.move_project(db, user, svc.get_project(db, project_id, user), body))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, user: User = Depends(require(Perm.PROJECT_DELETE)),
                   db: Session = Depends(get_db)) -> None:
    svc.delete_project(db, user, svc.get_project(db, project_id, user))


@router.get("/{project_id}/history")
def project_history(project_id: int, event_type: str | None = None, author_id: int | None = None,
                    date_from: date | None = Query(None, alias="from"), date_to: date | None = Query(None, alias="to"),
                    user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[HistoryOut]:
    project = svc.get_project(db, project_id, user)
    return history_svc.list_history(db, project.id, event_type, author_id, date_from, date_to)
