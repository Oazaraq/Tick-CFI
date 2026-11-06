from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.permissions import Perm, ensure
from app.schemas import CommentIn, CommentOut
from app.security import current_user, require
from app.services import comments as svc
from app.services import projects as project_svc

router = APIRouter(tags=["comments"])


@router.get("/projects/{project_id}/comments")
def list_comments(project_id: int, user: User = Depends(require(Perm.VIEW)),
                  db: Session = Depends(get_db)) -> list[CommentOut]:
    return svc.list_comments(db, project_svc.get_project(db, project_id, user).id)


@router.post("/projects/{project_id}/comments", status_code=201)
def add_comment(project_id: int, body: CommentIn, user: User = Depends(require(Perm.COMMENT_WRITE)),
                db: Session = Depends(get_db)) -> CommentOut:
    return svc.add_comment(db, user, project_svc.get_project(db, project_id, user), body.body)


@router.patch("/comments/{comment_id}")
def edit_comment(comment_id: int, body: CommentIn, user: User = Depends(current_user),
                 db: Session = Depends(get_db)) -> CommentOut:
    comment = svc.get_comment(db, comment_id, user)
    ensure(user, Perm.COMMENT_EDIT_OWN, comment)
    return svc.edit_comment(db, user, comment, body.body)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    comment = svc.get_comment(db, comment_id, user)
    ensure(user, Perm.COMMENT_EDIT_OWN, comment)
    svc.delete_comment(db, user, comment)
