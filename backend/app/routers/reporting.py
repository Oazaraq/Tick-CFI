from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.permissions import Perm
from app.schemas import EffortReportRow
from app.security import require
from app.services import reporting as svc

router = APIRouter(tags=["reporting"])


@router.get("/reporting/effort")
def effort(user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[EffortReportRow]:
    """Jours vendus et consommés par projet et par catégorie (projets visibles, phases uniquement)."""
    return [EffortReportRow.model_validate(r) for r in svc.effort_rows(db, user)]
