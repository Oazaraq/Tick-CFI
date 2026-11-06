"""Lot 3 : comptes-rendus par IA (DFB B, scénarios S15 à S18)."""
from datetime import date

import pytest

from app.ai import date_resolver, provider as ai
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.local_provider import LocalProvider
from app.ai.mock_provider import MockProvider
from app.models import Meeting
from app.services import meetings
from app.services.meeting_input import to_text

MONDAY = date(2026, 11, 2)
B7 = ("Olivier prépare le planning pour vendredi. Eric, tu commandes le matériel demain ? "
      "Il faudra valider l'architecture. Marie réalisera la recette avant le 20/11. "
      "On a parlé du budget, rien à faire.")


@pytest.mark.parametrize("text, meeting_day, expected", [
    ("vendredi", MONDAY, date(2026, 11, 6)),
    ("Lundi", MONDAY, date(2026, 11, 9)),                       # strictement après la réunion
    ("vendredi", date(2026, 11, 6), date(2026, 11, 13)),        # réunion un vendredi : +7 jours
    ("aujourd'hui", MONDAY, MONDAY),
    ("demain", MONDAY, date(2026, 11, 3)),
    ("Après-demain", MONDAY, date(2026, 11, 4)),
    ("apres demain", MONDAY, date(2026, 11, 4)),
    ("la semaine prochaine", MONDAY, date(2026, 11, 9)),
    ("en fin de semaine", MONDAY, date(2026, 11, 6)),
    ("fin de semaine", date(2026, 11, 6), date(2026, 11, 13)),  # à partir du vendredi : le suivant
    ("fin de semaine", date(2026, 11, 7), date(2026, 11, 13)),
    ("fin de mois", MONDAY, date(2026, 11, 30)),
    ("20/11", MONDAY, date(2026, 11, 20)),
    ("15/01", MONDAY, date(2027, 1, 15)),                       # déjà passée : année suivante
    ("15/01/2026", MONDAY, date(2026, 1, 15)),
    ("31/02", MONDAY, None),
    ("plus tard", MONDAY, None),
    (None, MONDAY, None),
])
def test_date_resolver(text, meeting_day, expected):
    assert date_resolver.resolve(text, meeting_day) == expected


def test_vtt_keeps_speakers_and_drops_timestamps():
    vtt = ("WEBVTT\n\nabc-1/1-0\n00:00:01.000 --> 00:00:03.000\n<v Olivier Zimmer>Bonjour</v>\n\n"
           "abc-2/1-0\n00:00:03.500 --> 00:00:05.000\n<v Olivier Zimmer>à tous &amp; merci.</v>\n\n"
           "00:00:06.000 --> 00:00:08.000\n<v Eric Moreau>Je commande le matériel.</v>\n")
    assert to_text(vtt, "reunion.vtt") == "Olivier Zimmer : Bonjour à tous & merci.\nEric Moreau : Je commande le matériel."
    assert to_text("  texte collé \r\n") == "texte collé"


def test_mock_provider_reference_examples():
    """DFB B.7 : titres, responsables entendus et échéances dites."""
    actions = MockProvider().extract(B7, MONDAY, [])["actions"]
    assert [(a["title"], a["assignee_name"], a["due_date_text"]) for a in actions] == [
        ("Préparer planning", "Olivier", "vendredi"),
        ("Commander matériel", "Eric", "demain"),
        ("Valider architecture", None, None),
        ("Réaliser recette", "Marie", "20/11"),
    ]


def test_assignee_resolution_project_first_then_active_users(make_user):
    marie_team, marie_other = make_user(first="Marie", last="Durand"), make_user(first="Marie", last="Lefèvre")
    eric = make_user(first="Éric", last="Moreau")
    team, everyone = [marie_team, eric], [marie_team, marie_other, eric]
    assert meetings.resolve_assignee("Marie", [team, everyone]) == marie_team   # le projet d'abord
    assert meetings.resolve_assignee("marie", [[eric], everyone]) is None        # S18 : deux Marie, ambigu
    assert meetings.resolve_assignee("eric", [team, everyone]) == eric           # sans accents ni casse
    assert meetings.resolve_assignee("Marie Lefevre", [team, everyone]) == marie_other
    assert meetings.resolve_assignee("Paul", [team, everyone]) is None


def _setup(make_user, login, new_project):
    pm = make_user(first="Olivier", last="Zimmer")
    eric, marie = make_user(role="contributor", first="Eric"), make_user(role="contributor", first="Marie", last="Durand")
    client = login(pm)
    project = new_project(client, pm, member_ids=[eric.id, marie.id])
    return client, project, pm, eric, marie


def _import(client, project, transcript=B7):
    r = client.post(f"/api/projects/{project['id']}/meetings", json={
        "title": "Point hebdo", "meeting_date": "2026-11-02", "participants": ["Olivier Zimmer"],
        "transcript": transcript})
    assert r.status_code == 201, r.text
    return client.get(f"/api/meetings/{r.json()['id']}").json()  # analyse faite en tâche de fond


def test_s15_extraction_creates_nothing_before_validation(make_user, login, new_project):
    client, project, pm, eric, marie = _setup(make_user, login, new_project)
    meeting = _import(client, project)
    assert meeting["status"] == "to_validate" and meeting["provider"] == "mock"
    first = meeting["candidates"][0]
    assert (first["title"], first["assignee_id"], first["due_date"]) == ("Préparer planning", pm.id, "2026-11-06")
    assert [c["assignee_id"] for c in meeting["candidates"]] == [pm.id, eric.id, None, marie.id]
    assert client.get(f"/api/projects/{project['id']}/actions").json() == []


def test_s16_only_selected_actions_are_created(make_user, login, new_project):
    client, project, pm, eric, _ = _setup(make_user, login, new_project)
    meeting = _import(client, project)
    summary = {**meeting["summary"], "decisions": ["Bascule le 21/11"]}
    kept = [{"title": "Préparer le planning détaillé", "assignee_id": pm.id, "due_date": "2026-11-06"},
            {"title": "Commander matériel", "assignee_id": eric.id, "priority": "high"}]
    r = client.post(f"/api/meetings/{meeting['id']}/validate", json={"summary": summary, "actions": kept})
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["actions_count"], r.json()["summary"]["decisions"]) == ("validated", 2, ["Bascule le 21/11"])
    actions = client.get(f"/api/projects/{project['id']}/actions").json()
    assert sorted(a["title"] for a in actions) == ["Commander matériel", "Préparer le planning détaillé"]
    assert {(a["origin"], a["meeting_id"]) for a in actions} == {("ai", meeting["id"])}
    listed = client.get(f"/api/projects/{project['id']}/meetings").json()
    assert [(m["title"], m["actions_count"]) for m in listed] == [("Point hebdo", 2)]
    types = {h["event_type"]: h["detail"] for h in client.get(f"/api/projects/{project['id']}/history").json()}
    assert types["actions_created_by_ai"] == {"label": "Point hebdo", "count": 2} and "meeting_imported" in types
    assert client.post(f"/api/meetings/{meeting['id']}/validate", json={"summary": summary}).status_code == 422


def test_validation_is_all_or_nothing(make_user, login, new_project):
    client, project, *_ = _setup(make_user, login, new_project)
    inactive = make_user(first="Paul", active=False)
    meeting = _import(client, project)
    body = {"summary": meeting["summary"], "actions": [{"title": "OK"}, {"title": "KO", "assignee_id": inactive.id}]}
    assert client.post(f"/api/meetings/{meeting['id']}/validate", json=body).status_code == 422
    assert client.get(f"/api/projects/{project['id']}/actions").json() == []
    assert client.get(f"/api/meetings/{meeting['id']}").json()["status"] == "to_validate"


def test_s17_failure_then_retry(make_user, login, new_project, monkeypatch):
    client, project, *_ = _setup(make_user, login, new_project)

    class Down:
        name = "anthropic"

        def extract(self, *args):
            raise ai.LLMError("API Anthropic : pas de réponse en 120 s.")

    monkeypatch.setattr(meetings, "get_provider", lambda: Down())
    meeting = _import(client, project)
    assert (meeting["status"], meeting["error_message"]) == ("failed", "API Anthropic : pas de réponse en 120 s.")
    monkeypatch.setattr(meetings, "get_provider", MockProvider)
    assert client.post(f"/api/meetings/{meeting['id']}/retry").json()["status"] == "processing"
    again = client.get(f"/api/meetings/{meeting['id']}").json()
    assert again["status"] == "to_validate" and len(again["candidates"]) == 4 and again["error_message"] is None
    assert client.post(f"/api/meetings/{meeting['id']}/retry").status_code == 422


def test_reject_creates_nothing(make_user, login, new_project):
    client, project, *_ = _setup(make_user, login, new_project)
    meeting = _import(client, project)
    assert client.post(f"/api/meetings/{meeting['id']}/reject").json()["status"] == "rejected"
    assert client.get(f"/api/projects/{project['id']}/actions").json() == []


def test_rights_and_demo_transcript(make_user, login, new_project):
    client, project, pm, eric, marie = _setup(make_user, login, new_project)
    reader_user = make_user(role="reader")
    client.patch(f"/api/projects/{project['id']}", json={"member_ids": [eric.id, marie.id, reader_user.id]})
    contributor, reader = login(eric), login(reader_user)
    body = {"title": "X", "meeting_date": "2026-11-02", "transcript": "texte"}
    assert contributor.post(f"/api/projects/{project['id']}/meetings", json=body).status_code == 403
    assert reader.get(f"/api/projects/{project['id']}/meetings").status_code == 200
    assert reader.get("/api/ai/provider").json() == {"provider": "mock"}
    assert reader.get("/api/ai/demo-transcript").status_code == 403
    demo = client.get("/api/ai/demo-transcript").json()
    assert demo["content"].startswith("WEBVTT")
    meeting = client.post(f"/api/projects/{project['id']}/meetings", json={
        "title": demo["title"], "meeting_date": "2026-11-02", "transcript": demo["content"], "filename": demo["filename"]})
    detail = client.get(f"/api/meetings/{meeting.json()['id']}").json()
    assert "WEBVTT" not in detail["transcript"] and len(detail["candidates"]) >= 5


def test_invalid_json_is_retried_once():
    answers = iter(["désolé", '```json\n{"summary": {"context": "ok", "topics": [""]}, "actions": []}\n```'])
    assert ai.extract_json(lambda: next(answers))["summary"] == {
        "context": "ok", "topics": [], "decisions": [], "open_points": []}
    with pytest.raises(ai.LLMError):
        ai.extract_json(lambda: "pas de JSON")


def test_long_transcripts_are_split_and_merged(monkeypatch):
    calls = []

    class Echo:
        name = "mock"

        def extract(self, transcript, *_):
            calls.append(transcript)
            return {"summary": {"context": f"bloc {len(calls)}", "topics": [transcript.strip()]},
                    "actions": [{"title": f"Action {len(calls)}"}]}

    monkeypatch.setattr(ai.settings, "llm_chunk_chars", 12)
    result = ai.analyze(Echo(), "ligne un\nligne deux\nligne trois\n", MONDAY, [])
    assert len(calls) == 3
    assert result["summary"]["context"] == "bloc 1\n\nbloc 2\n\nbloc 3"
    assert [a["title"] for a in result["actions"]] == ["Action 1", "Action 2", "Action 3"]


def test_http_providers_build_requests_and_read_answers(monkeypatch):
    sent = []
    answer = '{"summary": {"context": "c"}, "actions": [{"title": "Préparer planning"}]}'

    def fake_post(url, body, headers, service):
        sent.append((url, body, headers))
        if "anthropic" in url:
            return {"content": [{"type": "text", "text": answer}]}
        return {"choices": [{"message": {"content": answer}}]}

    monkeypatch.setattr("app.ai.anthropic_provider.post_json", fake_post)
    monkeypatch.setattr("app.ai.local_provider.post_json", fake_post)
    monkeypatch.setattr(ai.settings, "anthropic_api_key", "")
    with pytest.raises(ai.LLMError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider().extract("t", MONDAY, [])
    monkeypatch.setattr(ai.settings, "anthropic_api_key", "sk-test")
    assert AnthropicProvider().extract("t", MONDAY, [])["actions"][0]["title"] == "Préparer planning"
    assert LocalProvider().extract("t", MONDAY, ["Eric"])["actions"][0]["title"] == "Préparer planning"
    (url_a, body_a, headers_a), (url_l, body_l, _) = sent
    assert url_a.endswith("/v1/messages") and headers_a["x-api-key"] == "sk-test" and "02/11/2026" in body_a["messages"][0]["content"]
    assert url_l == "http://ollama:11434/v1/chat/completions" and body_l["response_format"] == {"type": "json_object"}


def test_interrupted_analysis_is_marked_failed(make_user, login, new_project, db):
    client, project, pm, *_ = _setup(make_user, login, new_project)
    db.add(Meeting(project_id=project["id"], title="Coupée", meeting_date=MONDAY, transcript="t",
                   status="processing", created_by=pm.id))
    db.commit()
    meetings.recover_interrupted(db)
    listed = client.get(f"/api/projects/{project['id']}/meetings").json()
    assert listed[0]["status"] == "failed"


def test_rejected_meeting_can_be_deleted(make_user, login, new_project):
    client, project, *_ = _setup(make_user, login, new_project)
    meeting = _import(client, project)
    assert client.delete(f"/api/meetings/{meeting['id']}").status_code == 422
    client.post(f"/api/meetings/{meeting['id']}/reject")
    assert client.delete(f"/api/meetings/{meeting['id']}").status_code == 204
    assert client.get(f"/api/projects/{project['id']}/meetings").json() == []
