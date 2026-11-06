"""Lot 4 : alertes email (S12 à S14, réaffectation), journal des emails, fichiers « en dur » et purge."""
from datetime import timedelta

from app import clock
from app.config import settings
from app.jobs import overdue_job
from app.models import Project, ProjectFile
from app.services import files, notifications

PDF = b"%PDF-1.4\n% test\n"


def to(outbox, user):
    return [m for m in outbox if m["To"] == user.email]


def test_s02_s12_project_emails_skip_the_author(make_user, login, new_project, outbox):
    pm, owner, member = make_user(), make_user(first="Alice"), make_user(role="contributor", first="Marie")
    project = new_project(login(pm), owner, member_ids=[member.id])
    assert [m["Subject"] for m in to(outbox, owner)] == ["[Projet Migration Réseau Site A] Nouveau projet"]
    assert not to(outbox, pm)                                                  # RG10 : jamais l'auteur
    outbox.clear()
    r = login(owner).post(f"/api/projects/{project['id']}/move", json={"status_code": "in_progress", "position": 0})
    assert r.status_code == 200
    assert not to(outbox, owner) and len(to(outbox, member)) == 1            # S12
    body = to(outbox, member)[0].get_body(("plain",)).get_content()
    assert "Avant-vente\n   ↓\nEn cours" in body and "Par : Alice Moreau" in body
    assert f"{settings.app_base_url}/projects/{project['id']}" in body


def test_s06_s13_action_emails_and_personal_switch(make_user, login, new_project, outbox, db):
    pm, olivier, quiet = make_user(), make_user(first="Olivier", last="Zimmer"), make_user(role="contributor")
    client = login(pm)
    project = new_project(client, pm, member_ids=[olivier.id, quiet.id])
    outbox.clear()
    client.post(f"/api/projects/{project['id']}/actions", json={"title": "Préparer planning", "assignee_id": olivier.id,
                                                              "due_date": "2026-11-06", "priority": "high"})
    mail = to(outbox, olivier)[0]
    assert mail["Subject"] == "[Projet Migration Réseau Site A] Nouvelle action : Préparer planning"
    assert "Échéance : 06/11/2026" in mail.get_body(("plain",)).get_content()
    assert "<br>" in mail.get_body(("html",)).get_content()
    assert login(quiet).patch("/api/auth/me", json={"notifications_enabled": False}).json()["notifications_enabled"] is False
    outbox.clear()
    client.post(f"/api/projects/{project['id']}/actions", json={"title": "Commander matériel", "assignee_id": quiet.id})
    assert outbox == []                                                       # S13 : rien d'envoyé…
    logs = login(make_user(role="admin")).get("/api/email-logs").json()
    assert not [e for e in logs if e["recipient_email"] == quiet.email and "Commander" in e["subject"]]  # … ni consigné


def test_reassignment_notifies_the_new_assignee(make_user, login, new_project, outbox):
    pm, eric, marie = make_user(), make_user(first="Eric"), make_user(first="Marie")
    client = login(pm)
    project = new_project(client, pm, member_ids=[eric.id, marie.id])
    action = client.post(f"/api/projects/{project['id']}/actions", json={"title": "Câbler", "assignee_id": eric.id}).json()
    outbox.clear()
    client.patch(f"/api/actions/{action['id']}", json={"assignee_id": marie.id})
    assert [m["Subject"] for m in outbox] == ["[Projet Migration Réseau Site A] Action réaffectée : Câbler"]
    assert outbox[0]["To"] == marie.email
    outbox.clear()
    client.patch(f"/api/actions/{action['id']}", json={"title": "Câbler la baie"})
    assert outbox == []                                                       # autres modifications : pas d'email


def test_inactive_and_duplicate_recipients_are_skipped(make_user, login, new_project, outbox):
    pm, owner, gone = make_user(), make_user(first="Alice"), make_user(first="Paul", active=False)
    new_project(login(pm), owner, member_ids=[owner.id, gone.id])
    assert [m["To"] for m in outbox] == [owner.email]


def test_failed_sending_is_logged_without_breaking_the_operation(make_user, login, new_project, monkeypatch):
    def down(_message):
        raise ConnectionRefusedError("SMTP injoignable")

    monkeypatch.setattr(notifications, "transport", down)
    admin, owner = make_user(role="admin"), make_user(first="Alice")
    project = new_project(login(admin), owner)
    assert project["id"]
    logs = login(admin).get("/api/email-logs", params={"status": "failed"}).json()
    assert [(e["recipient_email"], e["status"]) for e in logs] == [(owner.email, "failed")]
    assert "SMTP injoignable" in logs[0]["error"]
    assert login(owner).get("/api/email-logs").status_code == 403


def test_test_recipient_receives_everything(make_user, login, new_project, outbox, monkeypatch):
    monkeypatch.setattr(settings, "smtp_test_recipient", "recette@test.local")
    pm, owner = make_user(), make_user(first="Alice")
    new_project(login(pm), owner)
    assert outbox[0]["To"] == "recette@test.local"
    assert f"Destinataire réel : {owner.email}" in outbox[0].get_body(("plain",)).get_content()


def test_nothing_is_sent_when_the_transaction_fails(make_user, login, new_project, outbox):
    pm, eric = make_user(first="Olivier"), make_user(role="contributor", first="Eric")
    client = login(pm)
    project = new_project(client, pm, member_ids=[eric.id])
    meeting = client.post(f"/api/projects/{project['id']}/meetings", json={
        "title": "Point", "meeting_date": "2026-11-02", "transcript": "Eric, tu commandes le matériel demain ?"}).json()
    outbox.clear()
    gone = make_user(first="Paul", active=False)
    body = {"summary": {}, "actions": [{"title": "OK", "assignee_id": eric.id}, {"title": "KO", "assignee_id": gone.id}]}
    assert client.post(f"/api/meetings/{meeting['id']}/validate", json=body).status_code == 422
    assert outbox == []
    body["actions"].pop()
    client.post(f"/api/meetings/{meeting['id']}/validate", json=body)
    assert [m["Subject"] for m in outbox] == ["[Projet Migration Réseau Site A] Nouvelle action : OK"]


def test_s14_overdue_alert_is_sent_once(make_user, login, new_project, outbox):
    pm, eric = make_user(), make_user(first="Eric")
    client = login(pm)
    project = new_project(client, pm, member_ids=[eric.id])
    yesterday, today = clock.today() - timedelta(days=1), clock.today()
    late = client.post(f"/api/projects/{project['id']}/actions", json={"title": "Commander", "assignee_id": eric.id,
                                                                     "due_date": yesterday.isoformat()}).json()
    client.post(f"/api/projects/{project['id']}/actions", json={"title": "Du jour", "assignee_id": eric.id,
                                                              "due_date": today.isoformat()})
    outbox.clear()
    assert overdue_job.run() == 1
    assert [m["Subject"] for m in to(outbox, eric)] == ["[Projet Migration Réseau Site A] Action en retard : Commander"]
    assert len(outbox) == 2                                                   # responsable de l'action et du projet
    assert overdue_job.run() == 0
    history = client.get(f"/api/projects/{project['id']}/history", params={"event_type": "action_overdue"}).json()
    assert [(h["detail"]["label"], h["author"]) for h in history] == [("Commander", None)]
    client.patch(f"/api/actions/{late['id']}", json={"due_date": (today + timedelta(days=3)).isoformat()})
    client.patch(f"/api/actions/{late['id']}", json={"due_date": yesterday.isoformat()})
    assert overdue_job.run() == 1                                             # nouveau passage en retard


def test_files_upload_download_and_delete(make_user, login, new_project):
    pm, reader = make_user(), make_user(role="reader")
    client = login(pm)
    project = new_project(client, pm, member_ids=[reader.id])
    url = f"/api/projects/{project['id']}/files"
    r = client.post(url, files={"file": ("../../Compte rendu.pdf", PDF, "application/pdf")})
    assert r.status_code == 201, r.text
    item = r.json()
    assert (item["filename"], item["size"], item["uploader"]["id"]) == ("Compte rendu.pdf", len(PDF), pm.id)
    viewer = login(reader)
    assert viewer.post(url, files={"file": ("a.pdf", PDF)}).status_code == 403
    download = viewer.get(f"/api/files/{item['id']}/download")
    assert download.content == PDF and download.headers["content-type"] == "application/pdf"
    assert "attachment" in download.headers["content-disposition"]
    assert client.get(url).json() == {"files": [item], "purge_on": None}
    for name, data in (("outil.exe", b"MZ"), ("faux.pdf", b"hello"), ("note.txt", b"\x00\x01"), ("vide.pdf", b"")):
        assert client.post(url, files={"file": (name, data)}).status_code == 422, name
    stored = files.storage() / next(iter(files.storage().iterdir())).name
    assert client.delete(f"/api/files/{item['id']}").status_code == 204
    assert not stored.exists() and client.get(url).json()["files"] == []
    events = [h["event_type"] for h in client.get(f"/api/projects/{project['id']}/history").json()]
    assert "file_added" in events and "file_deleted" in events


def test_files_size_limit(make_user, login, new_project, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    pm = make_user()
    client = login(pm)
    project = new_project(client, pm)
    big = PDF + b"0" * (1024 * 1024)
    r = client.post(f"/api/projects/{project['id']}/files", files={"file": ("gros.pdf", big)})
    assert r.status_code == 422 and "1 Mo" in r.json()["detail"]


def test_files_are_purged_30_days_after_delivery(make_user, login, new_project, db):
    pm = make_user()
    client = login(pm)
    old, recent, running = (new_project(client, pm, title=t) for t in ("Ancien", "Récent", "En cours"))
    for p in (old, recent, running):
        client.post(f"/api/projects/{p['id']}/files", files={"file": ("cr.pdf", PDF)})
    for p in (old, recent):
        client.post(f"/api/projects/{p['id']}/move", json={"status_code": "done", "position": 0, "confirm": True})
    db.get(Project, old["id"]).end_date = clock.today() - timedelta(days=30)
    db.get(Project, recent["id"]).end_date = clock.today() - timedelta(days=29)
    db.commit()
    assert client.get(f"/api/projects/{recent['id']}/files").json()["purge_on"] == (clock.today() + timedelta(days=1)).isoformat()
    assert files.purge(db) == 1
    remaining = {f.project_id for f in db.query(ProjectFile)}
    assert remaining == {recent["id"], running["id"]} and len(list(files.storage().iterdir())) == 2
    purged = client.get(f"/api/projects/{old['id']}/history", params={"event_type": "files_purged"}).json()
    assert purged[0]["detail"] == {"count": 1} and purged[0]["author"] is None
