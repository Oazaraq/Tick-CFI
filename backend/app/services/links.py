"""Documents sous forme de liens (Q16). Seuls http(s) sont acceptés : un lien « javascript: » serait une faille XSS."""
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import DocumentLink, Project, User
from app.services import teams
from app.services.errors import Invalid, NotFound
from app.services.events import Event, emit


def get_link(db: Session, link_id: int, viewer: User) -> DocumentLink:
    link = db.get(DocumentLink, link_id)
    if link is None or teams.hidden(db, link.project_id, viewer):
        raise NotFound("Lien introuvable")
    return link


def list_links(db: Session, project_id: int) -> list[DocumentLink]:
    return list(db.scalars(select(DocumentLink).where(DocumentLink.project_id == project_id)
                           .options(joinedload(DocumentLink.author)).order_by(DocumentLink.created_at, DocumentLink.id)))


def add_link(db: Session, actor: User, project: Project, data) -> DocumentLink:
    label, url = data.label.strip(), data.url.strip()
    parsed = urlparse(url)
    if not label or parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise Invalid("Libellé obligatoire et adresse commençant par http:// ou https://")
    link = DocumentLink(project_id=project.id, label=label, url=url, author=actor)
    db.add(link)
    db.flush()
    emit(db, Event("document_added", project.id, "document", link.id, actor.id, [{"label": label}]))
    db.commit()
    return link


def remove_link(db: Session, actor: User, link: DocumentLink) -> None:
    emit(db, Event("document_removed", link.project_id, "document", link.id, actor.id, [{"label": link.label}]))
    db.delete(link)
    db.commit()
