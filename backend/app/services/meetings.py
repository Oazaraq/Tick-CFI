"""Réunions et comptes-rendus par IA (DFB B) : import, analyse en tâche de fond, validation humaine.

Rien n'est créé avant la validation (B.9) ; la transcription brute est conservée.
"""
import logging
import unicodedata

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.ai import date_resolver
from app.ai.provider import LLMError, analyze as run_analysis, get_provider
from app.db import SessionLocal
from app.models import Action, Meeting, Project, User
from app.services import actions as action_svc, teams
from app.services import meeting_input
from app.services.errors import Invalid, NotFound
from app.services.events import Event, emit

log = logging.getLogger(__name__)
INTERRUPTED = "Analyse interrompue par un redémarrage du serveur : relancez-la."


def get_meeting(db: Session, meeting_id: int, viewer: User) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None or teams.hidden(db, meeting.project_id, viewer):
        raise NotFound("Réunion introuvable")
    return meeting


def list_meetings(db: Session, project_id: int) -> list[Meeting]:
    return list(db.scalars(select(Meeting).where(Meeting.project_id == project_id)
                           .order_by(Meeting.meeting_date.desc(), Meeting.id.desc())))


def actions_count(db: Session, meeting_ids: list[int]) -> dict[int, int]:
    rows = db.execute(select(Action.meeting_id, func.count()).where(
        Action.meeting_id.in_(meeting_ids), Action.deleted_at.is_(None)).group_by(Action.meeting_id))
    return dict(rows.all())


def create_meeting(db: Session, actor: User, project: Project, data) -> Meeting:
    transcript = meeting_input.to_text(data.transcript, data.filename)
    if not transcript:
        raise Invalid("La transcription est vide")
    meeting = Meeting(project_id=project.id, title=data.title.strip(), meeting_date=data.meeting_date,
                      participants=", ".join(p.strip() for p in data.participants if p.strip()) or None,
                      transcript=transcript, status="processing", created_by=actor.id)
    db.add(meeting)
    db.commit()
    return meeting


def retry(db: Session, meeting: Meeting) -> Meeting:
    if meeting.status != "failed":
        raise Invalid("Seule une analyse en échec peut être relancée")
    meeting.status, meeting.error_message = "processing", None
    db.commit()
    return meeting


def analyze(meeting_id: int) -> None:
    """Tâche de fond. Aucune session n'est ouverte pendant l'appel IA (qui peut durer plusieurs minutes)."""
    with SessionLocal() as db:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None or meeting.status != "processing":
            return
        transcript, meeting_date = meeting.transcript, meeting.meeting_date
        participants = [p.strip() for p in (meeting.participants or "").split(",") if p.strip()]
    provider = get_provider()
    result, error = None, None
    try:
        result = run_analysis(provider, transcript, meeting_date, participants)
    except LLMError as exc:
        error = str(exc)
    except Exception:  # imprévu : une réunion ne doit jamais rester « en cours » indéfiniment
        log.exception("Analyse de la réunion %s", meeting_id)
        error = "Erreur inattendue pendant l'analyse : relancez-la ou contactez l'administrateur."
    with SessionLocal() as db:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None or meeting.status != "processing":
            return
        meeting.provider = provider.name
        if error:
            meeting.status, meeting.error_message = "failed", error
        else:
            meeting.summary = result["summary"]
            meeting.candidates = resolve_candidates(db, meeting, result["actions"])
            meeting.status, meeting.error_message = "to_validate", None
        db.commit()


def recover_interrupted(db: Session) -> None:
    """Au démarrage : une analyse « en cours » a été coupée par l'arrêt du serveur."""
    db.execute(update(Meeting).where(Meeting.status == "processing").values(status="failed", error_message=INTERRUPTED))
    db.commit()


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def resolve_assignee(name: str | None, pools: list[list[User]]) -> User | None:
    """Q20 : comparaison exacte (prénom, nom ou « prénom nom »), pool après pool.
    Exactement un résultat : assigné ; plusieurs : ambigu, « non identifié » (S18)."""
    key = _norm(name or "")
    if not key:
        return None
    for pool in pools:
        found = {u.id: u for u in pool if key in (_norm(u.first_name), _norm(u.last_name), _norm(u.full_name))}
        if found:
            return next(iter(found.values())) if len(found) == 1 else None
    return None


def resolve_candidates(db: Session, meeting: Meeting, candidates: list[dict]) -> list[dict]:
    project = db.get(Project, meeting.project_id)
    team = [u for u in [project.owner, *project.members] if u.is_active]  # compartimentage : l'équipe seule
    resolved = []
    for c in candidates:
        assignee = resolve_assignee(c.get("assignee_name"), [team])
        due = date_resolver.resolve(c.get("due_date_text"), meeting.meeting_date)
        resolved.append({**c, "assignee_id": assignee.id if assignee else None,
                         "due_date": due.isoformat() if due else None})
    return resolved


def validate(db: Session, actor: User, meeting: Meeting, data) -> Meeting:
    """S16 : seules les actions retenues sont créées (origine IA, lien vers la réunion), en une transaction."""
    if meeting.status != "to_validate":
        raise Invalid("Cette réunion n'est pas en attente de validation")
    project = db.get(Project, meeting.project_id)
    created = [action_svc.create_action(db, actor, project, a, origin="ai", meeting_id=meeting.id, commit=False)
               for a in data.actions]
    meeting.summary = data.summary.model_dump()
    meeting.status = "validated"
    emit(db, Event("meeting_imported", project.id, "meeting", meeting.id, actor.id, [{"label": meeting.title}]))
    if created:
        emit(db, Event("actions_created_by_ai", project.id, "meeting", meeting.id, actor.id,
                       [{"label": meeting.title, "count": len(created)}]))
    db.commit()
    return meeting


def reject(db: Session, meeting: Meeting) -> Meeting:
    """« Tout rejeter » : aucune action créée ; la réunion et sa transcription restent consultables."""
    if meeting.status not in ("to_validate", "failed"):
        raise Invalid("Cette réunion ne peut plus être rejetée")
    meeting.status = "rejected"
    db.commit()
    return meeting


def delete(db: Session, actor: User, meeting: Meeting) -> None:
    """Suppression d'une réunion rejetée ou en échec (aucune action n'en dépend) ; tracée dans l'historique."""
    if meeting.status not in ("rejected", "failed"):
        raise Invalid("Seule une réunion rejetée ou en échec peut être supprimée")
    emit(db, Event("meeting_deleted", meeting.project_id, "meeting", meeting.id, actor.id, [{"label": meeting.title}]))
    db.delete(meeting)
    db.commit()
