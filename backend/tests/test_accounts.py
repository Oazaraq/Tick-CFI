"""Mise en service : identifiant administrateur, comptes initiaux, mot de passe oublié, liens, limitation."""
import re
import time

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import users
from tests.conftest import PASSWORD

CSRF = {"X-Requested-With": "tickson"}


def token_from(mail) -> str:
    return re.search(r"#token=([\w.\-]+)", mail.get_body(("plain",)).get_content())[1]


def test_forgot_password_sends_a_single_use_link(make_user, outbox):
    user = make_user()
    client = TestClient(app, headers=CSRF)
    r = client.post("/api/auth/password/forgot", json={"email": user.email.upper()})
    assert r.status_code == 202 and "Si un compte correspond" in r.json()["detail"]
    assert [m["Subject"] for m in outbox] == ["Tick’ : réinitialisation de votre mot de passe"]
    assert client.post("/api/auth/password/forgot", json={"email": "inconnu@test.local"}).json() == r.json()
    assert len(outbox) == 1                                                  # aucun indice sur l'existence du compte
    token = token_from(outbox[0])
    r = client.post("/api/auth/password/reset", json={"token": token, "password": "nouveau-mdp-1"})
    assert r.status_code == 200 and client.get("/api/auth/me").json()["id"] == user.id   # session ouverte
    assert TestClient(app).post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).status_code == 401
    again = client.post("/api/auth/password/reset", json={"token": token, "password": "encore-un-mdp"})
    assert again.status_code == 422 and "expiré" in again.json()["detail"]   # usage unique


def test_expired_or_forged_links_are_refused(make_user, monkeypatch):
    user = make_user()
    real = time.time
    with monkeypatch.context() as patch:
        patch.setattr(time, "time", lambda: real() - (settings.password_link_hours + 1) * 3600)
        old = users.password_link(user).split("#token=")[1]
    client = TestClient(app, headers=CSRF)
    for token in (old, users.password_link(user).split("#token=")[1][:-3] + "abc"):
        assert client.post("/api/auth/password/reset", json={"token": token, "password": "nouveau-mdp-1"}).status_code == 422


def test_account_created_without_password_gets_an_activation_link(make_user, login, outbox):
    admin = login(make_user(role="admin"))
    r = admin.post("/api/users", json={"email": "Nouveau@Test.local", "first_name": "Nina", "last_name": "Roux",
                                       "role": "contributor"})
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["email"] == "nouveau@test.local" and "#token=" in created["activation_url"]
    assert [(m["To"], m["Subject"]) for m in outbox] == [("nouveau@test.local", "Tick’ : votre compte est prêt")]
    token = created["activation_url"].split("#token=")[1]
    client = TestClient(app, headers=CSRF)
    assert client.post("/api/auth/password/reset", json={"token": token, "password": "mon-mdp-nina"}).status_code == 200
    assert TestClient(app).post("/api/auth/login", json={"email": "nouveau@test.local", "password": "mon-mdp-nina"}).status_code == 200


def test_admin_password_link(make_user, login):
    admin, someone = login(make_user(role="admin")), make_user()
    link = admin.post(f"/api/users/{someone.id}/password-link").json()
    assert link["emailed"] is True and link["valid_hours"] == settings.password_link_hours
    assert login(someone).post(f"/api/users/{someone.id}/password-link").status_code == 403


def test_identifier_admin_and_initial_users(db, monkeypatch, outbox):
    """Base neuve : administrateur à identifiant (sans email) et comptes initiaux créés une seule fois."""
    monkeypatch.setattr(settings, "admin_email", "Atlas")
    monkeypatch.setattr(settings, "admin_password", "un-mot-de-passe-solide!")
    monkeypatch.setattr(settings, "admin_first_name", "Atlas")
    monkeypatch.setattr(settings, "admin_last_name", "Admin")
    monkeypatch.setattr(settings, "initial_users", [
        {"email": "PMartin@exemple.fr", "first_name": "Paul", "last_name": "Martin", "role": "project_manager"}])
    users.ensure_admin(db)
    assert [u.email for u in users.bootstrap_users(db)] == ["pmartin@exemple.fr"]
    assert users.bootstrap_users(db) == []                                   # idempotent
    client = TestClient(app, headers=CSRF)
    me = client.post("/api/auth/login", json={"email": "atlas", "password": "un-mot-de-passe-solide!"}).json()
    assert (me["first_name"], me["role"]) == ("Atlas", "admin")
    admin_id = me["id"]
    link = client.post(f"/api/users/{admin_id}/password-link").json()
    assert link["emailed"] is False                                          # un identifiant n'a pas de boîte
    assert outbox == []


def test_login_is_throttled_after_five_failures(make_user):
    user = make_user()
    client = TestClient(app)
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": user.email, "password": "faux"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 429 and "Trop de tentatives" in r.json()["detail"]


def test_forgot_password_is_throttled(make_user, outbox):
    user = make_user()
    client = TestClient(app)
    for _ in range(5):
        assert client.post("/api/auth/password/forgot", json={"email": user.email}).status_code == 202
    assert len(outbox) == 3
