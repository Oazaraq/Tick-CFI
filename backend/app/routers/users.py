from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.permissions import Perm, ensure
from app.config import settings
from app.schemas import PasswordLinkOut, UserCreate, UserOut, UserUpdate
from app.security import require
from app.services import notifications, users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(include_inactive: bool = False, user: User = Depends(require(Perm.VIEW)),
               db: Session = Depends(get_db)) -> list[UserOut]:
    if include_inactive:
        ensure(user, Perm.USER_MANAGE)
    return users.list_users(db, include_inactive)


class UserCreated(UserOut):
    activation_url: str | None = None  # compte créé sans mot de passe : lien à transmettre si l'email n'arrive pas


@router.post("", status_code=201)
def create_user(body: UserCreate, _: User = Depends(require(Perm.USER_MANAGE)), db: Session = Depends(get_db)) -> UserCreated:
    user = users.create_user(db, body)
    out = UserCreated.model_validate(user)
    if not body.password:
        out.activation_url = users.password_link(user)
        notifications.send_password_link(user, out.activation_url, invitation=True)
    return out


@router.post("/{user_id}/password-link")
def password_link(user_id: int, _: User = Depends(require(Perm.USER_MANAGE)), db: Session = Depends(get_db)) -> PasswordLinkOut:
    """Lien de réinitialisation, envoyé par email et affiché à l'administrateur (à transmettre autrement si besoin)."""
    user = users.get_user(db, user_id)
    url = users.password_link(user)
    return PasswordLinkOut(url=url, valid_hours=settings.password_link_hours,
                           emailed=notifications.send_password_link(user, url, invitation=False))


@router.patch("/{user_id}")
def update_user(user_id: int, body: UserUpdate, _: User = Depends(require(Perm.USER_MANAGE)),
                db: Session = Depends(get_db)) -> UserOut:
    return users.update_user(db, users.get_user(db, user_id), body)
