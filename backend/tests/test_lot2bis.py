"""Avenant 3 : réalisation interne / externe, j/h par phase, dépendances du planning."""


def test_action_sourcing_internal_by_default_external_with_subcontractor(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    url = f"/api/projects/{p['id']}/actions"
    assert client.post(url, json={"title": "Interne"}).json()["sourcing"] == "internal"
    a = client.post(url, json={"title": "Câblage", "sourcing": "external", "subcontractor": " Câblo SA "}).json()
    assert (a["sourcing"], a["subcontractor"]) == ("external", "Câblo SA")
    back = client.patch(f"/api/actions/{a['id']}", json={"sourcing": "internal"}).json()
    assert back["subcontractor"] is None  # pas de sous-traitant pour une action interne
    event = client.get(f"/api/projects/{p['id']}/history", params={"event_type": "action_updated"}).json()[0]
    assert (event["detail"]["field"], event["detail"]["new"]) == ("sourcing", "Interne")


def test_effort_per_phase_totals_on_card_and_by_category(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    url = f"/api/projects/{p['id']}/planning"
    client.post(url, json={"label": "Étude", "start_date": "2026-11-02", "end_date": "2026-11-06",
                           "category": "network", "days_sold": 5, "days_consumed": 2.5})
    client.post(url, json={"label": "Durcissement", "start_date": "2026-11-09", "end_date": "2026-11-13",
                           "category": "security", "days_sold": 3})
    milestone = client.post(url, json={"label": "Go", "kind": "milestone", "start_date": "2026-11-16",
                                       "category": "network", "days_sold": 99}).json()
    assert milestone["days_sold"] is None and milestone["category"] is None  # un jalon ne porte pas de charge
    assert client.post(url, json={"label": "X", "start_date": "2026-11-02", "category": "astrologie"}).status_code == 422
    assert client.post(url, json={"label": "X", "start_date": "2026-11-02", "days_sold": -1}).status_code == 422
    card = client.get("/api/projects").json()[0]
    assert (card["days_sold"], card["days_consumed"]) == (8, 2.5)
    effort = client.get(f"/api/projects/{p['id']}/effort").json()
    assert [(c["code"], c["sold"], c["consumed"]) for c in effort["categories"]] == [("network", 5, 2.5), ("security", 3, 0)]
    codes = [c["code"] for c in client.get("/api/effort-categories").json()]
    assert codes[:3] == ["infrastructure", "network", "security"] and codes[-1] == "other"


def test_dependencies_order_issues_and_cycles(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    url = f"/api/projects/{p['id']}/planning"
    a = client.post(url, json={"label": "A", "start_date": "2026-11-02", "end_date": "2026-11-10"}).json()
    b = client.post(url, json={"label": "B", "start_date": "2026-11-09", "end_date": "2026-11-20",
                               "predecessor_ids": [a["id"]]}).json()
    assert b["predecessor_ids"] == [a["id"]] and b["dependency_issues"] == [a["id"]]  # B commence avant la fin de A
    fixed = client.patch(f"/api/planning/{b['id']}", json={"start_date": "2026-11-10"}).json()
    assert fixed["dependency_issues"] == []  # le même jour est admis
    cycle = client.patch(f"/api/planning/{a['id']}", json={"predecessor_ids": [b["id"]]})
    assert cycle.status_code == 422 and "« B » dépend déjà" in cycle.json()["detail"]
    go = client.post(url, json={"label": "Go", "kind": "milestone", "start_date": "2026-11-25"}).json()
    moved = client.patch(f"/api/planning/{go['id']}", json={"label": "Go", "kind": "milestone", "start_date": "2026-11-27",
                                                             "end_date": None, "predecessor_ids": [b["id"]]})
    assert moved.status_code == 200 and moved.json()["end_date"] == "2026-11-27"  # un jalon n'exige pas de fin
    assert client.patch(f"/api/planning/{a['id']}", json={"predecessor_ids": [a["id"]]}).status_code == 422
    other = new_project(client, pm, title="Autre")
    foreign = client.post(f"/api/projects/{other['id']}/planning", json={"label": "Z", "start_date": "2026-11-02"}).json()
    assert client.patch(f"/api/planning/{b['id']}", json={"predecessor_ids": [foreign["id"]]}).status_code == 422
    assert client.delete(f"/api/planning/{a['id']}").status_code == 204
    assert client.get(url).json()[0]["predecessor_ids"] == []
    events = client.get(f"/api/projects/{p['id']}/history", params={"event_type": "planning_item_updated"}).json()
    assert "start_date" in {e["detail"]["field"] for e in events}
