from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.permissions import Perm
from app.routers.actions import out as action_out
from app.schemas import BlockedProject, DashboardOut
from app.security import require
from app.services import dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(mine: bool = False, user: User = Depends(require(Perm.VIEW)),
                  db: Session = Depends(get_db)) -> DashboardOut:
    d = dashboard.build(db, user, mine)

    def zone(z: dict, convert) -> dict:
        return {"total": z["total"], "items": [convert(x) for x in z["items"]]}

    return DashboardOut(tiles=d["tiles"], no_due_date=d["no_due_date"], charts=d["charts"],
                        due_soon=zone(d["due_soon"], action_out),
                        blocked_projects=zone(d["blocked_projects"], BlockedProject.model_validate),
                        unassigned=zone(d["unassigned"], action_out),
                        inactive_assignee=zone(d["inactive_assignee"], action_out))
