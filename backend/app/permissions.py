"""SEUL endroit où les droits sont vérifiés (DFB §3.1).

V2 : la restriction par projet s'ajoutera dans `can()` grâce à `resource`, sans modifier les routers.
"""
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    CONTRIBUTOR = "contributor"
    READER = "reader"


class Perm(StrEnum):
    VIEW = "view"                          # consulter projets, actions, dashboard, historique
    PROJECT_WRITE = "project_write"        # créer / modifier / déplacer un projet, planning (avenant 1)
    PROJECT_DELETE = "project_delete"
    ACTION_WRITE = "action_write"          # créer / modifier une action, changer son statut
    ACTION_DELETE = "action_delete"
    RISK_WRITE = "risk_write"
    LINK_WRITE = "link_write"
    FILE_WRITE = "file_write"
    EMAIL_LOG_VIEW = "email_log_view"
    COMMENT_WRITE = "comment_write"
    COMMENT_EDIT_OWN = "comment_edit_own"  # resource = le commentaire
    MEETING_MANAGE = "meeting_manage"      # importer, relancer, valider, rejeter
    CHECKLIST_WRITE = "checklist_write"    # renseigner la check-list de lancement d'un projet
    USER_MANAGE = "user_manage"
    SELF_SETTINGS = "self_settings"        # interrupteur emails, mot de passe


_ALL = frozenset(Role)
_WRITERS = frozenset({Role.ADMIN, Role.PROJECT_MANAGER, Role.CONTRIBUTOR})
_MANAGERS = frozenset({Role.ADMIN, Role.PROJECT_MANAGER})

MATRIX: dict[Perm, frozenset[Role]] = {
    Perm.VIEW: _ALL,
    Perm.PROJECT_WRITE: _MANAGERS,
    Perm.PROJECT_DELETE: _MANAGERS,
    Perm.ACTION_WRITE: _WRITERS,
    Perm.ACTION_DELETE: _MANAGERS,
    Perm.RISK_WRITE: _WRITERS,
    Perm.LINK_WRITE: _WRITERS,
    Perm.FILE_WRITE: _WRITERS,
    Perm.EMAIL_LOG_VIEW: frozenset({Role.ADMIN}),
    Perm.COMMENT_WRITE: _WRITERS,
    Perm.COMMENT_EDIT_OWN: _WRITERS,
    Perm.MEETING_MANAGE: _MANAGERS,
    Perm.CHECKLIST_WRITE: _WRITERS,
    Perm.USER_MANAGE: frozenset({Role.ADMIN}),
    Perm.SELF_SETTINGS: _ALL,
}


class Forbidden(Exception):
    """Droit insuffisant : traduit en HTTP 403 (RG12)."""


def can(user: Any, perm: Perm, resource: Any = None) -> bool:
    """Vrai si `user` (actif) détient `perm`, éventuellement sur `resource`."""
    if user is None or not getattr(user, "is_active", False):
        return False
    if Role(user.role) not in MATRIX[perm]:
        return False
    if perm is Perm.COMMENT_EDIT_OWN:
        return resource is not None and resource.author_id == user.id
    return True


def sees_all_projects(user: Any) -> bool:
    """Compartimentage strict : seul l'administrateur voit tous les projets."""
    return user is not None and Role(user.role) is Role.ADMIN


def sees_project(user: Any, project: Any) -> bool:
    """Les autres ne voient que les projets dont ils sont responsable ou participant."""
    return sees_all_projects(user) or project.owner_id == user.id or any(m.id == user.id for m in project.members)


def ensure(user: Any, perm: Perm, resource: Any = None) -> None:
    if not can(user, perm, resource):
        raise Forbidden(perm)
