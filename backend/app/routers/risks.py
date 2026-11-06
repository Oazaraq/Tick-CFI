from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Risk, User
from app.permissions import Perm
from app.schemas import RiskIn, RiskOut, RiskUpdate
from app.security import require
from app.services import projects as project_svc
from app.services import risks as svc

router = APIRouter(tags=["risks"])


def out(risk: Risk) -> RiskOut:
    score, level = svc.criticity(risk.probability, risk.impact)
    return RiskOut.model_validate(risk).model_copy(update={"score": score, "criticity": level})


@router.get("/projects/{project_id}/risks")
def list_risks(project_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[RiskOut]:
    return [out(r) for r in svc.list_risks(db, project_svc.get_project(db, project_id, user).id)]


@router.post("/projects/{project_id}/risks", status_code=201)
def create_risk(project_id: int, body: RiskIn, user: User = Depends(require(Perm.RISK_WRITE)),
                db: Session = Depends(get_db)) -> RiskOut:
    return out(svc.create_risk(db, user, project_svc.get_project(db, project_id, user), body))


@router.patch("/risks/{risk_id}")
def update_risk(risk_id: int, body: RiskUpdate, user: User = Depends(require(Perm.RISK_WRITE)),
                db: Session = Depends(get_db)) -> RiskOut:
    return out(svc.update_risk(db, user, svc.get_risk(db, risk_id, user), body))
