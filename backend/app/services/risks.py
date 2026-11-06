"""Registre des risques : criticité calculée et non stockée (RG11), historisation."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Project, Risk, User
from app.services import labels, teams, users
from app.services.changes import apply_changes, person_change
from app.services.errors import Invalid, NotFound
from app.services.events import Event, emit

LEVEL = {"low": 1, "medium": 2, "high": 3}


def criticity(probability: str, impact: str) -> tuple[int, str]:
    """RG11 : score = P × I (low 1, medium 2, high 3) ; 1–2 faible, 3–4 moyenne, 6–9 élevée."""
    score = LEVEL[probability] * LEVEL[impact]
    return score, "low" if score <= 2 else "medium" if score <= 4 else "high"


def get_risk(db: Session, risk_id: int, viewer: User) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None or teams.hidden(db, risk.project_id, viewer):
        raise NotFound("Risque introuvable")
    return risk


def list_risks(db: Session, project_id: int) -> list[Risk]:
    risks = db.scalars(select(Risk).where(Risk.project_id == project_id).options(joinedload(Risk.owner)))
    return sorted(risks, key=lambda r: (-criticity(r.probability, r.impact)[0], r.id))


def create_risk(db: Session, actor: User, project: Project, data) -> Risk:
    title = data.title.strip()
    if not title:
        raise Invalid("Le titre est obligatoire")
    teams.require_member(project, data.owner_id, "Le responsable du risque")
    risk = Risk(project_id=project.id, title=title, description=data.description, mitigation=data.mitigation,
                probability=data.probability, impact=data.impact, status=data.status,
                owner=users.assignable(db, data.owner_id) if data.owner_id else None)
    db.add(risk)
    db.flush()
    emit(db, Event("risk_created", project.id, "risk", risk.id, actor.id, [{"label": risk.title}]))
    db.commit()
    return risk


def update_risk(db: Session, actor: User, risk: Risk, data) -> Risk:
    changes = apply_changes(risk, data, ("title", "description", "mitigation", "probability", "impact", "status"),
                            required=("title", "probability", "impact", "status"),
                            mappings={"status": labels.RISK_STATUS})
    if "owner_id" in data.model_fields_set and data.owner_id != risk.owner_id:
        teams.require_member(risk.project, data.owner_id, "Le responsable du risque")
        owner = users.assignable(db, data.owner_id) if data.owner_id else None
        changes.append(person_change("owner", risk.owner, owner))
        risk.owner = owner
    if changes:
        emit(db, Event("risk_updated", risk.project_id, "risk", risk.id, actor.id,
                       [{**c, "label": risk.title} for c in changes]))
    db.commit()
    return risk
