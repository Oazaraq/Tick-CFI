from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Meeting, User
from app.permissions import Perm
from app.schemas import MeetingIn, MeetingItem, MeetingOut, MeetingValidate
from app.security import require
from app.services import meetings as svc
from app.services import projects as project_svc

router = APIRouter(tags=["meetings"])
DEMO_TRANSCRIPT = Path(__file__).resolve().parents[2] / "seed" / "transcript_demo.vtt"


def out(db: Session, meeting: Meeting, schema=MeetingOut):
    count = svc.actions_count(db, [meeting.id]).get(meeting.id, 0)
    return schema.model_validate(meeting).model_copy(update={"actions_count": count})


@router.get("/ai/provider")
def ai_provider(user: User = Depends(require(Perm.VIEW))) -> dict:
    """Fournisseur configuré, affiché avant l'envoi d'une transcription (DFB §4.6)."""
    return {"provider": settings.llm_provider}


@router.get("/ai/demo-transcript")
def demo_transcript(user: User = Depends(require(Perm.MEETING_MANAGE))) -> dict:
    """Transcription de démonstration (DFB B.8), chargeable depuis l'écran d'import."""
    return {"title": "Point d'avancement – Migration Réseau Site A", "filename": DEMO_TRANSCRIPT.name,
            "content": DEMO_TRANSCRIPT.read_text(encoding="utf-8")}


@router.get("/projects/{project_id}/meetings")
def list_meetings(project_id: int, user: User = Depends(require(Perm.VIEW)),
                  db: Session = Depends(get_db)) -> list[MeetingItem]:
    meetings = svc.list_meetings(db, project_svc.get_project(db, project_id, user).id)
    counts = svc.actions_count(db, [m.id for m in meetings])
    return [MeetingItem.model_validate(m).model_copy(update={"actions_count": counts.get(m.id, 0)}) for m in meetings]


@router.post("/projects/{project_id}/meetings", status_code=201)
def create_meeting(project_id: int, body: MeetingIn, background: BackgroundTasks,
                   user: User = Depends(require(Perm.MEETING_MANAGE)), db: Session = Depends(get_db)) -> MeetingOut:
    meeting = svc.create_meeting(db, user, project_svc.get_project(db, project_id, user), body)
    background.add_task(svc.analyze, meeting.id)  # le front interroge GET /meetings/{id} tant que « processing »
    return out(db, meeting)


@router.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: int, user: User = Depends(require(Perm.VIEW)), db: Session = Depends(get_db)) -> MeetingOut:
    return out(db, svc.get_meeting(db, meeting_id, user))


@router.post("/meetings/{meeting_id}/retry")
def retry(meeting_id: int, background: BackgroundTasks, user: User = Depends(require(Perm.MEETING_MANAGE)),
          db: Session = Depends(get_db)) -> MeetingOut:
    meeting = svc.retry(db, svc.get_meeting(db, meeting_id, user))
    background.add_task(svc.analyze, meeting.id)
    return out(db, meeting)


@router.post("/meetings/{meeting_id}/validate")
def validate(meeting_id: int, body: MeetingValidate, user: User = Depends(require(Perm.MEETING_MANAGE)),
             db: Session = Depends(get_db)) -> MeetingOut:
    return out(db, svc.validate(db, user, svc.get_meeting(db, meeting_id, user), body))


@router.delete("/meetings/{meeting_id}", status_code=204)
def delete(meeting_id: int, user: User = Depends(require(Perm.MEETING_MANAGE)), db: Session = Depends(get_db)):
    svc.delete(db, user, svc.get_meeting(db, meeting_id, user))


@router.post("/meetings/{meeting_id}/reject")
def reject(meeting_id: int, user: User = Depends(require(Perm.MEETING_MANAGE)), db: Session = Depends(get_db)) -> MeetingOut:
    return out(db, svc.reject(db, svc.get_meeting(db, meeting_id, user)))
