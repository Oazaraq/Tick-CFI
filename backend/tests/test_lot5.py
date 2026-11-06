"""Lot 5 : durcissement (CSRF, cookie, S20) et sauvegarde / restauration."""
import sqlite3

from fastapi.testclient import TestClient

from app import backup
from app.config import settings
from app.main import app
from app.services import files
from tests.conftest import PASSWORD

PDF = b"%PDF-1.4\n"


def test_writes_with_a_session_require_the_csrf_header(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    forged = client.post("/api/projects", json={"title": "X", "owner_id": pm.id}, headers={"X-Requested-With": ""})
    assert forged.status_code == 403 and "CSRF" in forged.json()["detail"]
    assert client.get("/api/projects", headers={"X-Requested-With": ""}).status_code == 200  # lecture libre
    assert new_project(client, pm)["id"]                                                     # avec l'en-tête


def test_s20_anonymous_writes_get_401_not_403():
    assert TestClient(app).post("/api/projects", json={}).status_code == 401
    assert TestClient(app).post("/api/auth/logout").status_code == 401


def test_session_cookie_flags(make_user, monkeypatch):
    user = make_user()
    cookie = TestClient(app).post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "secure" not in cookie
    monkeypatch.setattr(settings, "cookie_secure", True)
    secure = TestClient(app).post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).headers["set-cookie"].lower()
    assert "; secure" in secure


def test_backup_then_restore_brings_back_data_and_files(make_user, login, new_project, tmp_path):
    pm = make_user()
    client = login(pm)
    project = new_project(client, pm)
    client.post(f"/api/projects/{project['id']}/files", files={"file": ("cr.pdf", PDF)})
    archive = backup.create(str(tmp_path))
    assert archive.name.startswith("tickson-") and archive.suffixes == [".tar", ".gz"]
    client.delete(f"/api/projects/{project['id']}")                       # changements après la sauvegarde
    for stored in files.storage().iterdir():
        stored.unlink()
    backup.restore(str(archive))
    with sqlite3.connect(backup.database_path()) as db:
        assert db.execute("SELECT deleted_at FROM project WHERE id = ?", (project["id"],)).fetchone() == (None,)
    assert [f.read_bytes() for f in files.storage().iterdir()] == [PDF]
