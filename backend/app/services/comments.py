"""Commentaires du projet (Q16). Seul l'auteur modifie ou supprime le sien : vérifié par permissions.py."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import clock
from app.models import Comment, Project, User
from app.services import labels, teams
from app.services.errors import Invalid, NotFound
from app.services.events import Event, emit


def get_comment(db: Session, comment_id: int, viewer: User) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None or teams.hidden(db, comment.project_id, viewer):
        raise NotFound("Commentaire introuvable")
    return comment


def list_comments(db: Session, project_id: int) -> list[Comment]:
    return list(db.scalars(select(Comment).where(Comment.project_id == project_id)
                           .options(joinedload(Comment.author)).order_by(Comment.created_at, Comment.id)))


def _body(text: str) -> str:
    body = (text or "").strip()
    if not body:
        raise Invalid("Le commentaire est vide")
    return body


def add_comment(db: Session, actor: User, project: Project, text: str) -> Comment:
    comment = Comment(project_id=project.id, author=actor, body=_body(text))
    db.add(comment)
    db.flush()
    emit(db, Event("comment_added", project.id, "comment", comment.id, actor.id, [{"label": labels.clip(comment.body, 80)}]))
    db.commit()
    return comment


def edit_comment(db: Session, actor: User, comment: Comment, text: str) -> Comment:
    body = _body(text)
    if body != comment.body:
        detail = {"field": "body", "old": labels.clip(comment.body, 80), "new": labels.clip(body, 80)}
        comment.body, comment.edited_at = body, clock.now()
        emit(db, Event("comment_edited", comment.project_id, "comment", comment.id, actor.id, [detail]))
    db.commit()
    return comment


def delete_comment(db: Session, actor: User, comment: Comment) -> None:
    emit(db, Event("comment_deleted", comment.project_id, "comment", comment.id, actor.id,
                   [{"label": labels.clip(comment.body, 80)}]))
    db.delete(comment)
    db.commit()
