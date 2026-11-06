from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PlanningItem, User
from app.permissions import Perm
from app.schemas import CategoryOut, EffortOut, PlanningIn, PlanningOut, PlanningUpdate
from app.security import require
from app.services import labels
from app.services import planning as svc
from app.services import projects as project_svc

router = APIRouter(tags=["planning"])


def out(item: PlanningItem) -> PlanningOut:
    return PlanningOut.model_validate(item).model_copy(update={"dependency_issues": svc.dependency_issues(item)})


@router.get("/effort-categories")
def list_categories(user: User = Depends(require(Perm.VIEW))) -> list[CategoryOut]:
    return [CategoryOut(code=code, label=label) for code, label in labels.CATEGORY.items()]


@router.get("/projects/{project_id}/planning")
def list_items(project_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[PlanningOut]:
    return [out(i) for i in svc.list_items(db, project_svc.get_project(db, project_id, user).id)]


@router.get("/projects/{project_id}/effort")
def project_effort(project_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> EffortOut:
    return EffortOut(**svc.effort(db, project_svc.get_project(db, project_id, user).id))


@router.post("/projects/{project_id}/planning", status_code=201)
def create_item(project_id: int, body: PlanningIn, user: User = Depends(require(Perm.PROJECT_WRITE)),
                db: Session = Depends(get_db)) -> PlanningOut:
    return out(svc.create_item(db, user, project_svc.get_project(db, project_id, user), body))


@router.patch("/planning/{item_id}")
def update_item(item_id: int, body: PlanningUpdate, user: User = Depends(require(Perm.PROJECT_WRITE)),
                db: Session = Depends(get_db)) -> PlanningOut:
    return out(svc.update_item(db, user, svc.get_item(db, item_id, user), body))


@router.delete("/planning/{item_id}", status_code=204)
def delete_item(item_id: int, user: User = Depends(require(Perm.PROJECT_WRITE)), db: Session = Depends(get_db)) -> None:
    svc.delete_item(db, user, svc.get_item(db, item_id, user))
