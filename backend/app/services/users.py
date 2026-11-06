"""Comptes et mots de passe ; RG17 (responsable actif) et RG19 (dernier administrateur) ;
liens d'activation et de réinitialisation du mot de passe (signés, à durée limitée, à usage unique)."""
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.permissions import Role
from app.services.errors import Invalid, NotFound

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("timing-equalizer")
_links = URLSafeTimedSerializer(settings.secret_key, salt="tickson-password-link")
LINK_INVALID = "Lien invalide ou expiré : demandez-en un nouveau."


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(_DUMMY_HASH, password)  # même durée de réponse : pas d'énumération des comptes
        return None
    if not verify_password(user.password_hash, password) or not user.is_active:
        return None
    return user


def list_users(db: Session, include_inactive: bool = False) -> list[User]:
    q = select(User).order_by(User.last_name, User.first_name)
    if not include_inactive:
        q = q.where(User.is_active.is_(True))
    return list(db.scalars(q))


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("Utilisateur introuvable")
    return user


def assignable(db: Session, user_id: int) -> User:
    """RG17 : seul un utilisateur actif peut être choisi comme responsable."""
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Invalid("Responsable inconnu ou inactif")
    return user


def fingerprint(user: User) -> str:
    """Change avec le mot de passe : invalide les autres sessions et les liens déjà utilisés."""
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]


def password_link(user: User) -> str:
    """Lien à usage unique : le jeton est dans le fragment (#), jamais envoyé aux serveurs ni journalisé."""
    token = _links.dumps({"uid": user.id, "fp": fingerprint(user)})
    return f"{settings.app_base_url.rstrip('/')}/reset-password#token={token}"


def reset_with_token(db: Session, token: str, password: str) -> User:
    try:
        data = _links.loads(token, max_age=settings.password_link_hours * 3600)
    except BadSignature:  # signature fausse ou lien expiré
        raise Invalid(LINK_INVALID) from None
    user = db.get(User, data.get("uid")) if isinstance(data, dict) else None
    if user is None or not user.is_active or fingerprint(user) != data.get("fp"):
        raise Invalid(LINK_INVALID)
    user.password_hash = hash_password(password)
    db.commit()
    return user


def create_user(db: Session, data) -> User:
    """Sans mot de passe, le compte reçoit un lien pour le définir (voir le routeur)."""
    email = data.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise Invalid("Cet email est déjà utilisé")
    password = data.password or secrets.token_urlsafe(32)  # inconnu de tous en attendant le lien
    user = User(email=email, first_name=data.first_name.strip(), last_name=data.last_name.strip(),
                role=data.role, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user


def _active_admins(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == Role.ADMIN.value, User.is_active.is_(True)))


def update_user(db: Session, user: User, data) -> User:
    sent = data.model_fields_set
    demoted = "role" in sent and data.role is not None and data.role != Role.ADMIN
    deactivated = "is_active" in sent and data.is_active is False
    if user.role == Role.ADMIN and user.is_active and (demoted or deactivated) and _active_admins(db) <= 1:
        raise Invalid("Le dernier administrateur actif ne peut être ni désactivé ni rétrogradé")
    if "role" in sent and data.role:
        user.role = data.role
    if "is_active" in sent and data.is_active is not None:
        user.is_active = data.is_active
    if "password" in sent and data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    return user


def update_self(db: Session, user: User, data) -> User:
    if data.notifications_enabled is not None:
        user.notifications_enabled = data.notifications_enabled
    if data.new_password:
        if not verify_password(user.password_hash, data.current_password or ""):
            raise Invalid("Mot de passe actuel incorrect")
        user.password_hash = hash_password(data.new_password)
    db.commit()
    return user


def ensure_admin(db: Session) -> None:
    """Q7 : premier administrateur créé au démarrage si la base ne contient aucun compte."""
    if db.scalar(select(func.count()).select_from(User)) == 0:
        db.add(User(email=settings.admin_email.strip().lower(), first_name=settings.admin_first_name,
                    last_name=settings.admin_last_name, role=Role.ADMIN.value,
                    password_hash=hash_password(settings.admin_password)))
        db.commit()


def bootstrap_users(db: Session) -> list[User]:
    """INITIAL_USERS : comptes créés au démarrage s'ils n'existent pas ; renvoie les comptes créés."""
    from app.schemas import UserCreate
    created = []
    for entry in settings.initial_users:
        data = UserCreate.model_validate({**entry, "password": None})
        if not db.scalar(select(User.id).where(User.email == data.email.strip().lower())):
            created.append(create_user(db, data))
    return created
