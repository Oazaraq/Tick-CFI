"""Authentification, sessions, comptes : Q7, Q8, RG17, RG19, S20."""
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models import KanbanStatus, Project, User
from app.services import users
from tests.conftest import PASSWORD, alembic_config


def test_login_returns_profile_and_permissions(make_user, login):
    user = make_user()
    me = login(user).get("/api/auth/me").json()
    assert me["id"] == user.id and "project_write" in me["permissions"] and "user_manage" not in me["permissions"]


def test_wrong_password_gives_generic_message(make_user):
    r = TestClient(app).post("/api/auth/login", json={"email": make_user().email, "password": "faux"})
    assert r.status_code == 401 and r.json()["detail"] == "Identifiants incorrects"


def test_rg17_inactive_user_cannot_login(make_user):
    r = TestClient(app).post("/api/auth/login", json={"email": make_user(active=False).email, "password": PASSWORD})
    assert r.status_code == 401


def test_deactivation_revokes_open_session(make_user, login, db):
    user = make_user()
    client = login(user)
    user.is_active = False
    db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_s20_routes_require_a_session():
    client = TestClient(app)
    for path in ("/api/auth/me", "/api/projects", "/api/users", "/api/statuses"):
        assert client.get(path).status_code == 401
    assert client.get("/api/health").status_code == 200


def test_password_change_requires_current_and_revokes_other_sessions(make_user, login):
    user = make_user()
    first, second = login(user), login(user)
    assert first.patch("/api/auth/me", json={"current_password": "faux", "new_password": "nouveau-mdp"}).status_code == 422
    assert first.patch("/api/auth/me", json={"current_password": PASSWORD, "new_password": "nouveau-mdp"}).status_code == 200
    assert first.get("/api/auth/me").status_code == 200
    assert second.get("/api/auth/me").status_code == 401


def test_admin_creates_users_others_cannot(make_user, login):
    admin = login(make_user("admin"))
    body = {"email": "Marie.Durand@Test.local", "first_name": "Marie", "last_name": "Durand",
            "role": "contributor", "password": "password123"}
    r = admin.post("/api/users", json=body)
    assert r.status_code == 201 and r.json()["email"] == "marie.durand@test.local"
    assert admin.post("/api/users", json=body).status_code == 422
    assert login(make_user()).post("/api/users", json={**body, "email": "x@test.local"}).status_code == 403


def test_rg19_last_active_admin_is_protected(make_user, login):
    admin = make_user("admin")
    client = login(admin)
    assert client.patch(f"/api/users/{admin.id}", json={"is_active": False}).status_code == 422
    assert client.patch(f"/api/users/{admin.id}", json={"role": "reader"}).status_code == 422
    other = make_user("admin")
    assert client.patch(f"/api/users/{other.id}", json={"role": "reader"}).status_code == 200


def test_inactive_users_listed_for_admin_only(make_user, login):
    admin = make_user("admin")
    make_user(active=False)
    client = login(admin)
    assert len(client.get("/api/users").json()) == 1
    assert len(client.get("/api/users", params={"include_inactive": True}).json()) == 2
    assert login(make_user()).get("/api/users", params={"include_inactive": True}).status_code == 403


def test_q7_first_admin_created_once(db):
    users.ensure_admin(db)
    users.ensure_admin(db)
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_migrations_match_models_and_seed_statuses(db):
    command.check(alembic_config())
    rows = db.execute(select(KanbanStatus.code, KanbanStatus.label, KanbanStatus.is_active_counted)
                      .order_by(KanbanStatus.position)).all()
    assert [tuple(r) for r in rows] == [("presale", "Avant-vente", False), ("in_progress", "En cours", True),
                                        ("blocked", "Bloqué", True), ("done", "Livré", False)]


def test_migration_0003_reclassifies_existing_projects(db, make_user):
    """Avenant 2 : les projets de recette déjà créés ne doivent pas être perdus."""
    cfg = alembic_config()
    command.downgrade(cfg, "0002")
    owner = make_user()
    ids = dict(db.execute(select(KanbanStatus.code, KanbanStatus.id)).all())
    for code in ("idea", "to_launch", "study", "validation", "blocked", "done"):
        db.add(Project(title=code, owner_id=owner.id, status_id=ids[code]))
    db.commit()
    db.close()
    command.upgrade(cfg, "head")
    rows = dict(db.execute(select(Project.title, KanbanStatus.code).join(KanbanStatus, Project.status_id == KanbanStatus.id)).all())
    assert rows == {"idea": "presale", "to_launch": "presale", "study": "presale",
                    "validation": "in_progress", "blocked": "blocked", "done": "done"}
