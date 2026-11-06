from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.permissions import Perm
from app.schemas import LinkIn, LinkOut
from app.security import require
from app.services import links as svc
from app.services import projects as project_svc

router = APIRouter(tags=["links"])


@router.get("/projects/{project_id}/links")
def list_links(project_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> list[LinkOut]:
    return svc.list_links(db, project_svc.get_project(db, project_id, user).id)


@router.post("/projects/{project_id}/links", status_code=201)
def add_link(project_id: int, body: LinkIn, user: User = Depends(require(Perm.LINK_WRITE)),
             db: Session = Depends(get_db)) -> LinkOut:
    return svc.add_link(db, user, project_svc.get_project(db, project_id, user), body)


@router.delete("/links/{link_id}", status_code=204)
def remove_link(link_id: int, user: User = Depends(require(Perm.LINK_WRITE)), db: Session = Depends(get_db)) -> None:
    svc.remove_link(db, user, svc.get_link(db, link_id, user))
