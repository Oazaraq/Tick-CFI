from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.permissions import Perm, can, ensure
from app.schemas import LoginIn, MeOut, MeUpdate, PasswordForgotIn, PasswordResetIn
from app.security import clear_session, current_user, set_session
from app.services import notifications, throttle, users

router = APIRouter(prefix="/auth", tags=["auth"])


def me_out(user: User) -> MeOut:
    """Profil + permissions calculées par permissions.py : l'interface masque, le serveur refuse."""
    return MeOut.model_validate(user).model_copy(update={
        "permissions": [p.value for p in Perm if can(user, p)],
        "due_soon_days": settings.due_soon_days, "done_hide_days": settings.done_hide_days})


def _too_many(seconds: int) -> HTTPException:
    return HTTPException(429, f"Trop de tentatives : réessayez dans {max(1, round(seconds / 60))} minute(s).")


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> MeOut:
    """Connexion par email ou identifiant ; 5 échecs par compte et par quart d'heure au maximum."""
    key = body.email.strip().lower()
    if wait := throttle.LOGIN.wait_seconds(key):
        raise _too_many(wait)
    user = users.authenticate(db, body.email, body.password)
    if user is None:
        throttle.LOGIN.hit(key)
        raise HTTPException(401, "Identifiants incorrects")
    throttle.LOGIN.reset(key)
    set_session(response, user)
    return me_out(user)


@router.post("/password/forgot", status_code=202)
def forgot_password(body: PasswordForgotIn, db: Session = Depends(get_db)) -> dict:
    """Toujours la même réponse : on ne révèle pas si un compte existe."""
    key = body.email.strip().lower()
    if not throttle.FORGOT.wait_seconds(key):
        throttle.FORGOT.hit(key)
        user = db.scalar(select(User).where(User.email == key))
        if user is not None and user.is_active:
            notifications.send_password_link(user, users.password_link(user), invitation=False)
    return {"detail": f"Si un compte correspond à cette adresse, un email avec un lien vient de lui être envoyé "
                      f"(valable {settings.password_link_hours} heures)."}


@router.post("/password/reset")
def reset_password(body: PasswordResetIn, response: Response, db: Session = Depends(get_db)) -> MeOut:
    """Nouveau mot de passe par lien signé ; ouvre directement la session."""
    user = users.reset_with_token(db, body.token, body.password)
    throttle.LOGIN.reset(user.email)
    set_session(response, user)
    return me_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response, _: User = Depends(current_user)) -> None:
    clear_session(response)


@router.get("/me")
def me(user: User = Depends(current_user)) -> MeOut:
    return me_out(user)


@router.patch("/me")
def update_me(body: MeUpdate, response: Response, user: User = Depends(current_user),
              db: Session = Depends(get_db)) -> MeOut:
    ensure(user, Perm.SELF_SETTINGS)
    users.update_self(db, user, body)
    set_session(response, user)  # nouveau cookie si le mot de passe a changé
    return me_out(user)
