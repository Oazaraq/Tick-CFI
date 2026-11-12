"""Charge : ingénieurs par demi-journée, gestion de projet à l'heure (1 j = 7,5 h) ; reporting par projet et catégorie."""
D = "2026-11-12"


def _phase(client, project_id, label, category, sold=None, consumed=None):
    return client.post(f"/api/projects/{project_id}/planning", json={
        "label": label, "kind": "phase", "start_date": D, "category": category, "days_sold": sold, "days_consumed": consumed})


def test_engineers_by_half_day_project_management_by_hour(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    r = _phase(client, p["id"], "Intégration", "infrastructure", 1.3)
    assert r.status_code == 422 and "demi-journées" in r.json()["detail"]
    assert _phase(client, p["id"], "Intégration", "infrastructure", 1.5, 0.5).status_code == 201
    item = _phase(client, p["id"], "Suivi", "project_management", 1, 0.25 / 7.5).json()  # 15 minutes
    assert item["days_consumed"] == 0.0333
    moved = client.patch(f"/api/planning/{item['id']}", json={"category": "infrastructure"})
    assert moved.status_code == 422  # 0,0333 j n'est pas une demi-journée


def test_effort_report_by_project_and_category(make_user, login, new_project):
    pm, member = make_user(), make_user("contributor", "Marie", "Durand")
    outsider, admin = make_user("contributor", "Paul", "Martin"), make_user("admin", "Ada", "Admin")
    client = login(pm)
    p = new_project(client, pm, title="Joinville", member_ids=[member.id])
    _phase(client, p["id"], "Mise à niveau", "infrastructure", 2, 1)
    _phase(client, p["id"], "Bascule", "infrastructure", 2, 2.5)
    _phase(client, p["id"], "Suivi", "project_management", 1, 0.2)
    client.post(f"/api/projects/{p['id']}/planning", json={"label": "Lancement", "kind": "milestone", "start_date": D})
    rows = login(member).get("/api/reporting/effort").json()
    assert [(r["category"], r["sold"], r["consumed"]) for r in rows] == [  # par projet, puis par libellé de catégorie
        ("project_management", 1, 0.2), ("infrastructure", 4, 3.5)]
    assert rows[1]["title"] == "Joinville" and rows[1]["status_label"] == "Avant-vente"
    assert rows[1]["category_label"] == "Ingénierie infrastructure" and rows[1]["owner"]["id"] == pm.id
    assert login(outsider).get("/api/reporting/effort").json() == []
    assert len(login(admin).get("/api/reporting/effort").json()) == 2
