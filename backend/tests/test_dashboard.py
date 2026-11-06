"""Dashboard et listes d'actions : S08, S09, RG13, RG18, RG20."""
from datetime import timedelta

from app import clock


def iso(days: int) -> str:
    return (clock.today() + timedelta(days=days)).isoformat()


def test_s08_tiles_and_alert_zones(make_user, login, new_project, db):
    pm, bob = make_user(), make_user("contributor", "Bob", "Martin")
    client = login(pm)
    active = new_project(client, pm, title="Actif", status_code="in_progress", member_ids=[bob.id])
    new_project(client, pm, title="Bloqué", status_code="blocked", blocked_reason="Attente fournisseur")
    new_project(client, pm, title="Avant-vente")  # non compté dans les projets actifs (avenant 2)
    gone = new_project(client, pm, title="Supprimé", status_code="in_progress")
    url = f"/api/projects/{active['id']}/actions"
    client.post(url, json={"title": "En retard", "due_date": iso(-1), "assignee_id": pm.id})
    client.post(url, json={"title": "Bientôt", "due_date": iso(2), "assignee_id": bob.id})
    client.post(url, json={"title": "Sans responsable", "due_date": iso(30)})
    client.post(url, json={"title": "Sans échéance", "assignee_id": pm.id})
    done = client.post(url, json={"title": "Faite", "due_date": iso(-3)}).json()
    client.patch(f"/api/actions/{done['id']}", json={"status": "done"})
    client.post(f"/api/projects/{gone['id']}/actions", json={"title": "Fantôme", "due_date": iso(-1)})
    client.delete(f"/api/projects/{gone['id']}")  # RG18
    bob.is_active = False
    db.commit()

    d = client.get("/api/dashboard").json()
    assert d["tiles"] == {"active_projects": 2, "open_actions": 4, "overdue_actions": 1,
                          "blocked_projects": 1, "my_actions": 2}
    titles = lambda zone: [x["title"] for x in d[zone]["items"]]  # noqa: E731
    assert titles("due_soon") == ["Bientôt"]
    assert titles("blocked_projects") == ["Bloqué"]
    assert d["blocked_projects"]["items"][0]["blocked_reason"] == "Attente fournisseur"
    assert titles("unassigned") == ["Sans responsable"]
    assert titles("inactive_assignee") == ["Bientôt"]
    assert d["no_due_date"] == 1  # RG13
    overdue = client.get("/api/actions", params={"overdue": True}).json()
    assert [a["title"] for a in overdue] == ["En retard"]


def test_dashboard_scope_my_projects(make_user, login, new_project):
    """« Mes projets » ne change rien pour qui ne voit que son équipe : seul l'administrateur voit au-delà."""
    pm, marie = make_user("admin"), make_user(first="Marie", last="Durand")
    client = login(pm)
    new_project(client, pm, status_code="in_progress")
    new_project(client, marie, status_code="in_progress")
    assert client.get("/api/dashboard").json()["tiles"]["active_projects"] == 2
    assert client.get("/api/dashboard", params={"mine": True}).json()["tiles"]["active_projects"] == 1


def test_s09_my_actions_sorted_overdue_first_then_priority(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    url = f"/api/projects/{p['id']}/actions"
    for title, due, priority in [("Sans date", None, "critical"), ("Demain basse", iso(1), "low"),
                                 ("Demain critique", iso(1), "critical"), ("Hier", iso(-1), "low")]:
        client.post(url, json={"title": title, "due_date": due, "priority": priority, "assignee_id": pm.id})
    closed = client.post(url, json={"title": "Close", "assignee_id": pm.id}).json()
    client.patch(f"/api/actions/{closed['id']}", json={"status": "done"})
    mine = client.get("/api/actions/me", params={"hide_closed": True}).json()
    assert [a["title"] for a in mine] == ["Hier", "Demain critique", "Demain basse", "Sans date"]
    assert mine[0]["project_title"] == "Migration Réseau Site A" and mine[0]["is_overdue"]
    assert len(client.get("/api/actions/me").json()) == 5


def test_active_projects_filter(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    new_project(client, pm, title="Vente")
    new_project(client, pm, title="Chantier", status_code="in_progress")
    assert [c["title"] for c in client.get("/api/projects", params={"active": True}).json()] == ["Chantier"]


def test_charts_show_the_state_of_the_day(make_user, login, new_project):
    """Avenant 3 : graphiques de l'état du jour, dans le périmètre choisi."""
    pm, other = make_user("admin"), make_user(first="Alice")
    client = login(pm)
    late = new_project(client, pm, title="Réseau", status_code="in_progress")
    new_project(client, other, title="Hors périmètre", status_code="blocked", blocked_reason="Attente devis")
    yesterday = (clock.today() - timedelta(days=1)).isoformat()
    for title, priority in (("A", "high"), ("B", "high"), ("C", "low")):
        client.post(f"/api/projects/{late['id']}/actions", json={"title": title, "priority": priority, "due_date": yesterday})
    client.post(f"/api/projects/{late['id']}/planning", json={
        "label": "Étude", "kind": "phase", "start_date": "2026-11-02", "end_date": "2026-11-06",
        "category": "network", "days_sold": 5, "days_consumed": 6.5})
    charts = client.get("/api/dashboard").json()["charts"]
    assert {c["code"]: c["count"] for c in charts["projects_by_status"]} == {
        "presale": 0, "in_progress": 1, "blocked": 1, "done": 0}
    assert [(c["code"], c["count"]) for c in charts["actions_by_priority"]] == [
        ("critical", 0), ("high", 2), ("medium", 0), ("low", 1)]
    assert charts["overdue_by_project"] == [{"project_id": late["id"], "title": "Réseau", "count": 3}]
    assert charts["effort_by_project"] == [{"project_id": late["id"], "title": "Réseau", "sold": 5.0, "consumed": 6.5}]
    mine = client.get("/api/dashboard", params={"mine": True}).json()["charts"]
    assert {c["code"]: c["count"] for c in mine["projects_by_status"]}["blocked"] == 0
