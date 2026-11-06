"""Projets et Kanban : S01–S05, S07, RG03, RG14, RG15, RG18."""
from datetime import timedelta

from sqlalchemy import func, select

from app import clock
from app.models import HistoryEvent, Project


def test_s01_reader_cannot_create_project(make_user, login):
    reader = make_user("reader")
    client = login(reader)
    assert client.post("/api/projects", json={"title": "X", "owner_id": reader.id}).status_code == 403
    assert "project_write" not in client.get("/api/auth/me").json()["permissions"]


def test_s02_created_in_presale_with_history(make_user, login, new_project):
    pm, owner = make_user(), make_user("contributor", "Olivier", "Zimmer")
    client = login(pm)
    p = new_project(client, owner)
    assert p["status_code"] == "presale" and p["owner"]["id"] == owner.id
    history = client.get(f"/api/projects/{p['id']}/history").json()
    assert [(h["event_type"], h["author"]["id"]) for h in history] == [("project_created", pm.id)]


def test_s03_move_is_historised_with_labels_and_author(make_user, login, new_project):
    pm = make_user(first="Olivier", last="Zimmer")
    client = login(pm)
    p = new_project(client, pm, status_code="presale")
    r = client.post(f"/api/projects/{p['id']}/move", json={"status_code": "in_progress", "position": 0})
    assert r.status_code == 200 and r.json()["status_code"] == "in_progress"
    event = client.get(f"/api/projects/{p['id']}/history", params={"event_type": "project_status_changed"}).json()[0]
    assert event["detail"] == {"field": "status", "old": "Avant-vente", "new": "En cours"}
    assert event["author"]["first_name"] == "Olivier"


def test_s04_rg03_blocked_needs_reason_cleared_on_exit(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm, status_code="presale")
    url = f"/api/projects/{p['id']}/move"
    assert client.post(url, json={"status_code": "blocked"}).status_code == 422
    assert client.post(url, json={"status_code": "blocked", "blocked_reason": "  "}).status_code == 422
    blocked = client.post(url, json={"status_code": "blocked", "blocked_reason": "Attente fournisseur"}).json()
    assert blocked["blocked_reason"] == "Attente fournisseur" and blocked["blocked_since"]
    unblocked = client.post(url, json={"status_code": "in_progress"}).json()
    assert unblocked["blocked_reason"] is None and unblocked["blocked_since"] is None
    reasons = [h["detail"].get("reason") for h in client.get(f"/api/projects/{p['id']}/history").json()]
    assert "Attente fournisseur" in reasons


def test_s05_rg14_rg15_done_with_open_actions(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm, status_code="in_progress")
    for title in ("A", "B"):
        client.post(f"/api/projects/{p['id']}/actions", json={"title": title})
    url = f"/api/projects/{p['id']}/move"
    r = client.post(url, json={"status_code": "done"})
    assert r.status_code == 409 and r.json()["count"] == 2
    done = client.post(url, json={"status_code": "done", "confirm": True}).json()
    assert done["status_code"] == "done" and done["end_date"] == clock.today().isoformat()
    assert client.post(url, json={"status_code": "in_progress"}).json()["end_date"] is None


def test_done_without_open_actions_needs_no_confirmation(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    assert client.post(f"/api/projects/{p['id']}/move", json={"status_code": "done"}).status_code == 200


def test_due_date_cannot_precede_start(make_user, login):
    pm = make_user()
    r = login(pm).post("/api/projects", json={"title": "X", "owner_id": pm.id,
                                              "start_date": "2026-11-10", "due_date": "2026-11-01"})
    assert r.status_code == 422


def test_update_is_historised_field_by_field(make_user, login, new_project):
    pm, marie = make_user(), make_user("contributor", "Marie", "Durand")
    client = login(pm)
    p = new_project(client, pm)
    client.patch(f"/api/projects/{p['id']}", json={"priority": "high", "owner_id": marie.id, "member_ids": [pm.id]})
    events = client.get(f"/api/projects/{p['id']}/history", params={"event_type": "project_updated"}).json()
    details = {e["detail"]["field"]: e["detail"] for e in events}
    assert details["priority"]["new"] == "Haute" and details["owner"]["new"] == "Marie Durand"
    assert details["members"]["new"] == "Eric Moreau"


def test_reordering_inside_a_column(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    a, b = new_project(client, pm, title="A"), new_project(client, pm, title="B")
    client.post(f"/api/projects/{b['id']}/move", json={"status_code": "presale", "position": 0})
    assert [c["title"] for c in client.get("/api/projects").json()] == ["B", "A"]
    assert len(client.get(f"/api/projects/{a['id']}/history").json()) == 1  # pas d'historique pour l'ordre


def test_rg18_soft_delete_keeps_history(make_user, login, new_project, db):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    assert client.delete(f"/api/projects/{p['id']}").status_code == 204
    assert client.get("/api/projects").json() == []
    assert client.get(f"/api/projects/{p['id']}").status_code == 404
    count = db.scalar(select(func.count()).select_from(HistoryEvent).where(HistoryEvent.project_id == p["id"]))
    assert count == 2


def test_cards_counters_and_filters(make_user, login, new_project):
    pm, other = make_user("admin"), make_user(first="Marie", last="Durand")
    client = login(pm)
    mine = new_project(client, pm, title="Réseau")
    new_project(client, other, title="Autre")
    yesterday = (clock.today() - timedelta(days=1)).isoformat()
    client.post(f"/api/projects/{mine['id']}/actions", json={"title": "En retard", "due_date": yesterday})
    done = client.post(f"/api/projects/{mine['id']}/actions", json={"title": "Faite"}).json()
    client.patch(f"/api/actions/{done['id']}", json={"status": "done"})
    card = next(c for c in client.get("/api/projects").json() if c["id"] == mine["id"])
    assert (card["actions_total"], card["actions_done"], card["actions_overdue"], card["actions_open"]) == (2, 1, 1, 1)
    titles = lambda **params: [c["title"] for c in client.get("/api/projects", params=params).json()]  # noqa: E731
    assert titles(mine=True) == ["Réseau"]
    assert titles(has_overdue=True) == ["Réseau"]
    assert titles(q="autre") == ["Autre"]
    assert titles(owner_id=other.id) == ["Autre"]


def test_old_done_projects_hidden_by_default(make_user, login, new_project, db):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm, status_code="done")
    db.get(Project, p["id"]).end_date = clock.today() - timedelta(days=31)
    db.commit()
    assert client.get("/api/projects").json() == []
    assert len(client.get("/api/projects", params={"include_old_done": True}).json()) == 1


def test_s07_history_is_append_only(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    url = f"/api/projects/{p['id']}/history"
    event_id = client.get(url).json()[0]["id"]
    assert client.delete(url).status_code == 405
    assert client.put(url, json={}).status_code == 405
    for method in ("patch", "put", "delete"):
        assert getattr(client, method)(f"/api/history/{event_id}").status_code == 404
