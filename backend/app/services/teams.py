"""Équipe d'un projet (responsable + participants) et compartimentage : un projet n'est visible que de son
équipe et des administrateurs (permissions.sees_project) ; seuls ses membres peuvent porter une action ou un risque."""
from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from app.models import Project, User, project_member
from app.permissions import sees_all_projects, sees_project
from app.services.errors import Invalid, NotFound


def my_projects(user: User):
    """Projets dont l'utilisateur est responsable ou participant (clause SQL)."""
    member_of = select(project_member.c.project_id).where(project_member.c.user_id == user.id)
    return or_(Project.owner_id == user.id, Project.id.in_(member_of))


def visible_to(user: User):
    """Clause SQL des projets visibles par l'utilisateur."""
    return true() if sees_all_projects(user) else my_projects(user)


def hidden(db: Session, project_id: int, viewer: User) -> bool:
    """Projet absent, supprimé (RG18) ou hors de l'équipe du lecteur : tout ce qui en dépend est « introuvable »."""
    project = db.get(Project, project_id)
    return project is None or project.deleted_at is not None or not sees_project(viewer, project)


def visible_project(db: Session, project_id: int, viewer: User) -> Project:
    if hidden(db, project_id, viewer):
        raise NotFound("Projet introuvable")  # même réponse qu'un projet inexistant : son existence n'est pas révélée
    return db.get(Project, project_id)


def team_ids(project: Project) -> set[int]:
    owner_id = project.owner.id if project.owner is not None else project.owner_id  # owner_id n'est posé qu'au flush
    return {owner_id, *(m.id for m in project.members)}


def require_member(project: Project, user_id: int | None, who: str = "Le responsable") -> None:
    if user_id is not None and user_id not in team_ids(project):
        raise Invalid(f"{who} doit faire partie de l'équipe du projet : ajoutez-le d'abord comme participant")
