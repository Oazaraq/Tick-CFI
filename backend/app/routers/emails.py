from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.permissions import Perm
from app.schemas import EmailLogOut
from app.security import require
from app.services import notifications

router = APIRouter(tags=["emails"])


@router.get("/email-logs")
def email_logs(status: Literal["sent", "failed"] | None = None, _: User = Depends(require(Perm.EMAIL_LOG_VIEW)),
               db: Session = Depends(get_db)) -> list[EmailLogOut]:
    """Journal des emails (300 derniers), pour l'administrateur."""
    return [EmailLogOut.model_validate(e) for e in notifications.list_logs(db, status)]
