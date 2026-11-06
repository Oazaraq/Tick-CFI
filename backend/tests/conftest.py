import itertools
import os
import tempfile
from pathlib import Path

# Base de test isolée, posée avant tout import de l'application (jamais la base réelle)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["FILES_DIR"] = tempfile.mkdtemp()
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["SMTP_TEST_RECIPIENT"] = ""

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.services.users import hash_password  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
PASSWORD = "password123"
_HASH = hash_password(PASSWORD)  # un seul hachage argon2 pour tous les comptes de test
_seq = itertools.count()


def alembic_config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def schema():
    command.upgrade(alembic_config(), "head")  # les tests passent par les vraies migrations


@pytest.fixture(autouse=True)
def outbox(monkeypatch):
    """Emails envoyés pendant le test : capturés, sans SMTP, et de façon synchrone."""
    from app.services import notifications
    sent = []
    monkeypatch.setattr(notifications, "transport", sent.append)
    monkeypatch.setattr(notifications, "run_async", lambda fn, *args: fn(*args))
    return sent


@pytest.fixture(autouse=True)
def reset_throttles():
    """Compteurs de tentatives remis à zéro : chaque test part d'un état propre."""
    from app.services import throttle
    throttle.LOGIN.reset()
    throttle.FORGOT.reset()


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name != "kanban_status":
                conn.execute(table.delete())
    for stored in Path(os.environ["FILES_DIR"]).glob("*"):  # fichiers déposés pendant le test
        stored.unlink()


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def make_user(db):
    def make(role="project_manager", first="Eric", last="Moreau", active=True) -> User:
        user = User(email=f"user{next(_seq)}@test.local", first_name=first, last_name=last, role=role,
                    password_hash=_HASH, is_active=active)
        db.add(user)
        db.commit()
        return user
    return make


@pytest.fixture
def login():
    def as_user(user: User) -> TestClient:
        client = TestClient(app, headers={"X-Requested-With": "tickson"})  # en-tête CSRF, comme le front
        assert client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).status_code == 200
        return client
    return as_user


@pytest.fixture
def new_project():
    def create(client: TestClient, owner: User, **fields) -> dict:
        r = client.post("/api/projects", json={"title": "Migration Réseau Site A", "owner_id": owner.id, **fields})
        assert r.status_code == 201, r.text
        return r.json()
    return create
