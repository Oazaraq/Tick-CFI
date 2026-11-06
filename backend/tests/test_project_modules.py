"""Modules de la fiche projet : risques (S10, RG11), commentaires (S11), liens, planning (avenant 1)."""
import pytest

from app.services import risks


@pytest.mark.parametrize(("p", "i", "score", "level"), [
    ("low", "low", 1, "low"), ("low", "medium", 2, "low"), ("medium", "low", 2, "low"),
    ("low", "high", 3, "medium"), ("high", "low", 3, "medium"), ("medium", "medium", 4, "medium"),
    ("medium", "high", 6, "high"), ("high", "medium", 6, "high"), ("high", "high", 9, "high"),
])
def test_rg11_criticity(p, i, score, level):
    assert risks.criticity(p, i) == (score, level)


def test_s10_risk_high_probability_medium_impact(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    url = f"/api/projects/{p['id']}/risks"
    r = client.post(url, json={"title": "Retard fournisseur", "probability": "high", "impact": "medium"})
    assert r.status_code == 201 and (r.json()["score"], r.json()["criticity"]) == (6, "high")
    client.patch(f"/api/risks/{r.json()['id']}", json={"status": "watched", "owner_id": pm.id})
    types = [h["event_type"] for h in client.get(f"/api/projects/{p['id']}/history").json()]
    assert "risk_created" in types and types.count("risk_updated") == 2
    reader = login(make_user("reader"))
    assert reader.post(url, json={"title": "X", "probability": "low", "impact": "low"}).status_code == 403


def test_s11_only_author_edits_or_deletes_comment(make_user, login, new_project):
    pm, member = make_user(), make_user("contributor")
    client = login(pm)
    p = new_project(client, pm, member_ids=[member.id])
    c = client.post(f"/api/projects/{p['id']}/comments", json={"body": "Premier jet"}).json()
    edited = client.patch(f"/api/comments/{c['id']}", json={"body": "Version corrigée"}).json()
    assert edited["edited_at"] and edited["body"] == "Version corrigée"
    other = login(member)
    assert other.patch(f"/api/comments/{c['id']}", json={"body": "Pirate"}).status_code == 403
    assert other.delete(f"/api/comments/{c['id']}").status_code == 403
    assert login(make_user("reader")).post(f"/api/projects/{p['id']}/comments", json={"body": "X"}).status_code == 403
    assert client.delete(f"/api/comments/{c['id']}").status_code == 204
    types = {h["event_type"] for h in client.get(f"/api/projects/{p['id']}/history").json()}
    assert {"comment_added", "comment_edited", "comment_deleted"} <= types


def test_links_only_http_and_historised(make_user, login, new_project):
    pm, member = make_user(), make_user("contributor")
    p = new_project(login(pm), pm, member_ids=[member.id])
    client = login(member)
    url = f"/api/projects/{p['id']}/links"
    assert client.post(url, json={"label": "Piège", "url": "javascript:alert(1)"}).status_code == 422
    link = client.post(url, json={"label": "Cahier des charges", "url": "https://intranet.example/cdc"}).json()
    assert [x["label"] for x in client.get(url).json()] == ["Cahier des charges"]
    assert client.delete(f"/api/links/{link['id']}").status_code == 204
    types = {h["event_type"] for h in client.get(f"/api/projects/{p['id']}/history").json()}
    assert {"document_added", "document_removed"} <= types


def test_planning_phases_and_milestones(make_user, login, new_project):
    pm = make_user()
    client = login(pm)
    p = new_project(client, pm)
    url = f"/api/projects/{p['id']}/planning"
    phase = client.post(url, json={"label": "Déploiement", "start_date": "2026-11-09", "end_date": "2026-11-20"}).json()
    milestone = client.post(url, json={"label": "Mise en service", "kind": "milestone",
                                       "start_date": "2026-11-23", "end_date": "2026-12-31"}).json()
    assert milestone["end_date"] == "2026-11-23"  # un jalon n'a qu'une date
    assert client.post(url, json={"label": "X", "start_date": "2026-11-10", "end_date": "2026-11-01"}).status_code == 422
    assert client.patch(f"/api/planning/{phase['id']}", json={"end_date": "2026-11-27"}).json()["end_date"] == "2026-11-27"
    assert [i["label"] for i in client.get(url).json()] == ["Déploiement", "Mise en service"]
    assert login(make_user("contributor")).post(url, json={"label": "Y", "start_date": "2026-11-10"}).status_code == 403
    assert client.delete(f"/api/planning/{milestone['id']}").status_code == 204
    types = {h["event_type"] for h in client.get(f"/api/projects/{p['id']}/history").json()}
    assert {"planning_item_created", "planning_item_updated", "planning_item_deleted"} <= types
