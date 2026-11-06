"""Session par cookie httpOnly signé (Q8) et dépendances FastAPI d'authentification."""
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.permissions import Perm, ensure
from app.services.users import fingerprint

COOKIE = "pilotage_session"
MAX_AGE = 7 * 24 * 3600
_signer = URLSafeTimedSerializer(settings.secret_key, salt="pilotage-session")


def set_session(response: Response, user: User) -> None:
    token = _signer.dumps({"uid": user.id, "fp": fingerprint(user)})
    response.set_cookie(COOKIE, token, max_age=MAX_AGE, httponly=True, samesite="lax", path="/",
                        secure=settings.cookie_secure)  # COOKIE_SECURE=true derrière HTTPS


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE)
    try:
        data = _signer.loads(token, max_age=MAX_AGE) if token else None
    except BadSignature:  # signature invalide ou expirée
        data = None
    user = db.get(User, data.get("uid")) if isinstance(data, dict) else None
    if user is None or not user.is_active or data.get("fp") != fingerprint(user):
        raise HTTPException(401, "Non connecté")
    return user


def require(perm: Perm):
    """Dépendance de route : utilisateur connecté détenant `perm` (décidé par permissions.py)."""
    def dependency(user: User = Depends(current_user)) -> User:
        ensure(user, perm)
        return user
    return dependency
