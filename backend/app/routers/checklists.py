from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.permissions import Perm
from app.schemas import ChecklistIn, ChecklistOut
from app.security import require
from app.services import checklists as svc
from app.services import projects as project_svc

router = APIRouter(tags=["checklists"])


@router.get("/projects/{project_id}/checklist")
def get_checklist(project_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> ChecklistOut:
    return ChecklistOut.model_validate(svc.out(db, project_svc.get_project(db, project_id, user)))


@router.put("/projects/{project_id}/checklist")
def save_checklist(project_id: int, body: ChecklistIn, user: User = Depends(require(Perm.CHECKLIST_WRITE)),
                   db: Session = Depends(get_db)) -> ChecklistOut:
    project = project_svc.get_project(db, project_id, user)
    svc.save(db, user, project, body)
    return ChecklistOut.model_validate(svc.out(db, project))
