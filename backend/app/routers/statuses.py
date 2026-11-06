from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import KanbanStatus, User
from app.permissions import Perm
from app.schemas import StatusOut
from app.security import require

router = APIRouter(tags=["statuses"])


@router.get("/statuses")
def list_statuses(_: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[StatusOut]:
    return list(db.scalars(select(KanbanStatus).order_by(KanbanStatus.position)))
