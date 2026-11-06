"""Compartimentage strict (décision du 06/11/2026). Un projet n'est visible que de son équipe (responsable et participants) ;
seul l'administrateur voit tous les projets. Le travail ne peut être confié qu'à un membre de l'équipe."""

SUB_PATHS = ("", "/actions", "/risks", "/comments", "/links", "/planning", "/files", "/meetings", "/history")


def _project_with_work(make_user, login, new_project):
    pm, member = make_user(), make_user("contributor", "Marie", "Durand")
    outsider, admin = make_user("contributor", "Paul", "Martin"), make_user("admin", "Ada", "Admin")
    client = login(pm)
    p = new_project(client, pm, member_ids=[member.id], status_code="in_progress")
    action = client.post(f"/api/projects/{p['id']}/actions", json={"title": "Câbler", "assignee_id": member.id}).json()
    return client, p, action, pm, member, outsider, admin


def test_outsider_sees_nothing_member_and_admin_do(make_user, login, new_project):
    _, p, action, _, member, outsider, admin = _project_with_work(make_user, login, new_project)
    other = login(outsider)
    assert other.get("/api/projects").json() == []
    for path in SUB_PATHS:
        assert other.get(f"/api/projects/{p['id']}{path}").status_code == 404, path  # existence non révélée
    assert other.patch(f"/api/actions/{action['id']}", json={"status": "done"}).status_code == 404
    assert other.get("/api/actions").json() == []
    tiles = other.get("/api/dashboard").json()["tiles"]
    assert (tiles["active_projects"], tiles["open_actions"]) == (0, 0)
    for user in (member, admin):
        viewer = login(user)
        assert viewer.get(f"/api/projects/{p['id']}").status_code == 200
        assert [a["title"] for a in viewer.get("/api/actions").json()] == ["Câbler"]


def test_work_goes_to_team_members_only(make_user, login, new_project):
    client, p, action, _, _, outsider, _ = _project_with_work(make_user, login, new_project)
    r = client.post(f"/api/projects/{p['id']}/actions", json={"title": "X", "assignee_id": outsider.id})
    assert r.status_code == 422 and "équipe" in r.json()["detail"]
    assert client.patch(f"/api/actions/{action['id']}", json={"assignee_id": outsider.id}).status_code == 422
    risk = {"title": "Retard", "probability": "low", "impact": "low", "owner_id": outsider.id}
    assert client.post(f"/api/projects/{p['id']}/risks", json=risk).status_code == 422


def test_member_with_open_work_stays_in_the_team(make_user, login, new_project):
    client, p, action, pm, member, _, _ = _project_with_work(make_user, login, new_project)
    r = client.patch(f"/api/projects/{p['id']}", json={"member_ids": []})
    assert r.status_code == 422 and "Marie Durand" in r.json()["detail"]
    client.patch(f"/api/actions/{action['id']}", json={"status": "done"})
    assert client.patch(f"/api/projects/{p['id']}", json={"member_ids": []}).status_code == 200
    assert login(member).get(f"/api/projects/{p['id']}").status_code == 404


def test_creator_keeps_sight_of_the_project_he_creates(make_user, login, new_project):
    pm, owner = make_user(), make_user("project_manager", "Lea", "Durand")
    p = new_project(login(pm), owner)
    assert [m["id"] for m in p["members"]] == [pm.id]
    admin = make_user("admin")
    assert new_project(login(admin), owner)["members"] == []  # l'administrateur voit déjà tout
