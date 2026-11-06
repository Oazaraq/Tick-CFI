"""Actions : S06, RG05, RG12, RG16, RG17, RG18."""
from datetime import date, timedelta

import pytest

from app import clock
from app.models import Action
from app.services import actions


def test_s06_create_action_updates_counter_and_history(make_user, login, new_project):
    pm, olivier = make_user(), make_user("contributor", "Olivier", "Zimmer")
    client = login(pm)
    p = new_project(client, pm, member_ids=[olivier.id])
    r = client.post(f"/api/projects/{p['id']}/actions", json={
        "title": "Préparer planning", "assignee_id": olivier.id, "due_date": "2026-11-06", "priority": "high"})
    assert r.status_code == 201 and r.json()["assignee"]["id"] == olivier.id
    assert [a["title"] for a in client.get(f"/api/projects/{p['id']}/actions").json()] == ["Préparer planning"]
    assert client.get(f"/api/projects/{p['id']}").json()["actions_total"] == 1
    event = client.get(f"/api/projects/{p['id']}/history", params={"event_type": "action_created"}).json()[0]
    assert event["detail"] == {"label": "Préparer planning"}


@pytest.mark.parametrize(("delta", "status", "late"), [
    (0, "todo", False), (-1, "todo", True), (-1, "blocked", True), (-1, "done", False),
    (-1, "cancelled", False), (3, "in_progress", False),
])
def test_rg05_overdue(delta, status, late):
    today = date(2026, 11, 4)
    assert actions.is_overdue(Action(due_date=today + timedelta(days=delta), status=status), today) is late


def test_rg05_no_due_date_is_never_late():
    assert not actions.is_overdue(Action(due_date=None, status="todo"), date(2026, 11, 4))


def test_rg16_close_then_reopen(make_user, login, new_project, db):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    a = client.post(f"/api/projects/{p['id']}/actions", json={"title": "T"}).json()
    action = db.get(Action, a["id"])
    action.overdue_notified_at = clock.now()
    db.commit()
    assert client.patch(f"/api/actions/{a['id']}", json={"status": "done"}).json()["closed_at"]
    assert client.patch(f"/api/actions/{a['id']}", json={"status": "todo"}).json()["closed_at"] is None
    db.refresh(action)
    assert action.overdue_notified_at is None
    types = [h["event_type"] for h in client.get(f"/api/projects/{p['id']}/history").json()]
    assert types.count("action_status_changed") == 2


def test_due_date_pushed_back_rearms_overdue_alert(make_user, login, new_project, db):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    a = client.post(f"/api/projects/{p['id']}/actions", json={"title": "T", "due_date": "2026-01-01"}).json()
    action = db.get(Action, a["id"])
    action.overdue_notified_at = clock.now()
    db.commit()
    client.patch(f"/api/actions/{a['id']}", json={"due_date": (clock.today() + timedelta(days=5)).isoformat()})
    db.refresh(action)
    assert action.overdue_notified_at is None


def test_rg17_inactive_cannot_be_assigned_but_keeps_actions(make_user, login, new_project, db):
    pm, bob = make_user(), make_user("contributor", "Bob", "Martin")
    client = login(pm)
    p = new_project(client, pm, member_ids=[bob.id])
    a = client.post(f"/api/projects/{p['id']}/actions", json={"title": "T", "assignee_id": bob.id}).json()
    bob.is_active = False
    db.commit()
    assert client.post(f"/api/projects/{p['id']}/actions", json={"title": "U", "assignee_id": bob.id}).status_code == 422
    kept = client.patch(f"/api/actions/{a['id']}", json={"title": "T2", "assignee_id": bob.id}).json()
    assert kept["assignee"]["id"] == bob.id and kept["title"] == "T2"


def test_rg12_rights_on_actions(make_user, login, new_project):
    pm, reader, member = make_user(), make_user("reader"), make_user("contributor")
    p = new_project(login(pm), pm, member_ids=[reader.id, member.id])
    url = f"/api/projects/{p['id']}/actions"
    assert login(reader).post(url, json={"title": "T"}).status_code == 403
    contributor = login(member)
    a = contributor.post(url, json={"title": "T"}).json()
    assert contributor.patch(f"/api/actions/{a['id']}", json={"status": "in_progress"}).status_code == 200
    assert contributor.delete(f"/api/actions/{a['id']}").status_code == 403


def test_reassignment_is_historised(make_user, login, new_project):
    pm, marie = make_user(), make_user("contributor", "Marie", "Durand")
    client = login(pm)
    p = new_project(client, pm, member_ids=[marie.id])
    a = client.post(f"/api/projects/{p['id']}/actions", json={"title": "T"}).json()
    client.patch(f"/api/actions/{a['id']}", json={"assignee_id": marie.id})
    event = client.get(f"/api/projects/{p['id']}/history", params={"event_type": "action_updated"}).json()[0]
    assert event["detail"] == {"field": "assignee", "old": "", "new": "Marie Durand", "label": "T"}


def test_rg18_deleted_action_leaves_lists_and_counters(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    a = client.post(f"/api/projects/{p['id']}/actions", json={"title": "T"}).json()
    assert client.delete(f"/api/actions/{a['id']}").status_code == 204
    assert client.get(f"/api/projects/{p['id']}/actions").json() == []
    assert client.get(f"/api/projects/{p['id']}").json()["actions_total"] == 0
    assert client.patch(f"/api/actions/{a['id']}", json={"title": "X"}).status_code == 404
    types = [h["event_type"] for h in client.get(f"/api/projects/{p['id']}/history").json()]
    assert "action_deleted" in types
