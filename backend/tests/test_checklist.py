"""Check-list de lancement par projet : modèle commun, états par projet, droits, compartimentage, historique."""


def _setup(make_user, login, new_project):
    pm, member = make_user(), make_user("contributor", "Marie", "Durand")
    client = login(pm)
    p = new_project(client, pm, member_ids=[member.id])
    return client, p, pm, member


def test_default_checklist_follows_the_template(make_user, login, new_project):
    client, p, *_ = _setup(make_user, login, new_project)
    c = client.get(f"/api/projects/{p['id']}/checklist").json()
    assert c["revision"] == 0 and c["updated_by"] is None
    assert [s["code"] for s in c["sections"]] == ["SITE", "ENE", "RES", "COM", "PLA"]
    assert sum(len(s["items"]) for s in c["sections"]) == 15


def test_save_is_historised_and_protected_against_concurrent_writes(make_user, login, new_project, outbox):
    client, p, pm, member = _setup(make_user, login, new_project)
    url = f"/api/projects/{p['id']}/checklist"
    outbox.clear()
    body = {"revision": 0, "meta": {"client": "Valophis Habitat", "kickoff_date": "2026-11-12"},
            "states": {"SITE-01": {"status": "ok"}, "RES-03": {"status": "ko", "note": "Plan IP attendu"}},
            "custom": [{"id": "X-1", "section": "RES", "point": "Firewall", "owner": "Client", "blocking": True}],
            "calc": [{"name": "Serveur", "qty": 2, "watts": 450, "units": 2}]}
    c = login(member).put(url, json=body).json()
    assert c["revision"] == 1 and c["states"]["RES-03"]["note"] == "Plan IP attendu"
    assert c["updated_by"]["first_name"] == "Marie" and c["custom"][0]["point"] == "Firewall"
    stale = login(pm).put(url, json={**body, "states": {}})
    assert stale.status_code == 409 and "Marie Durand" in stale.json()["detail"]
    history = client.get(f"/api/projects/{p['id']}/history").json()
    texts = {(h["event_type"], h["detail"].get("label"), h["detail"].get("new")) for h in history}
    assert ("checklist_status_changed", "SITE-01 · Matériel sur site", "OK") in texts
    assert ("checklist_status_changed", "RES-03 · Adressage et VLAN", "KO") in texts
    assert ("checklist_item_added", "Firewall", None) in texts
    assert ("checklist_info_updated", "Client", "Valophis Habitat") in texts
    assert outbox == []  # pas d'email pour la check-list


def test_rights_and_compartmentalization(make_user, login, new_project):
    pm, reader, outsider = make_user(), make_user("reader"), make_user("contributor", "Paul", "Martin")
    p = new_project(login(pm), pm, member_ids=[reader.id])
    url = f"/api/projects/{p['id']}/checklist"
    r = login(reader)
    assert r.get(url).status_code == 200
    assert r.put(url, json={"revision": 0}).status_code == 403
    assert login(outsider).get(url).status_code == 404


def test_invalid_content_is_refused(make_user, login, new_project):
    client, p, *_ = _setup(make_user, login, new_project)
    url = f"/api/projects/{p['id']}/checklist"
    assert client.put(url, json={"revision": 0, "states": {"SITE-01": {"status": "peut-être"}}}).status_code == 422
    bad_section = {"revision": 0, "custom": [{"id": "X-1", "section": "ZZZ", "point": "Autre"}]}
    assert client.put(url, json=bad_section).status_code == 422
    c = client.put(url, json={"revision": 0, "states": {"INCONNU": {"status": "ok"}}}).json()
    assert c["states"] == {}  # état d'un point inexistant : ignoré
