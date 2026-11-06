"""Alertes email (DFB partie A), abonnées au bus d'événements.

Les messages sont préparés pendant la transaction, puis envoyés en tâche de fond après sa validation
(rien ne part si l'opération échoue ; un échec d'envoi n'annule jamais l'opération). Chaque envoi est
consigné dans `email_log`.
"""
import html
import logging
import smtplib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

from sqlalchemy import event as sa_event, select
from sqlalchemy.orm import Session

from app.config import APP_TZ, settings
from app.db import SessionLocal
from app.models import Action, EmailLog, Project, User
from app.services import labels
from app.services.events import Event, subscribe

log = logging.getLogger(__name__)

SUBJECTS = {
    "project_created": "Nouveau projet",
    "project_updated": "Projet modifié",
    "project_status_changed": "Changement de statut",
    "action_created": "Nouvelle action : {label}",
    "action_status_changed": "Action « {label} » : changement de statut",
    "action_overdue": "Action en retard : {label}",
    "action_reassigned": "Action réaffectée : {label}",
    "comment_added": "Nouveau commentaire",
}
_TEAM_EVENTS = {"project_created", "project_updated", "project_status_changed", "comment_added"}
FIELDS = {"title": "Titre", "description": "Description", "owner": "Responsable", "members": "Participants",
          "priority": "Priorité", "start_date": "Date de début", "due_date": "Échéance", "end_date": "Fin réelle",
          "assignee": "Responsable", "sourcing": "Réalisation", "subcontractor": "Sous-traitant",
          "status": "Statut", "blocked_reason": "Motif de blocage"}


@dataclass
class Mail:
    to: str
    subject: str
    text: str
    html: str
    event_type: str
    project_id: int | None


def _recipients(db: Session, event: Event, project: Project, action: Action | None) -> list[User]:
    """A.1 + exclusions : auteur (RG10), inactifs, emails désactivés, doublons d'adresse."""
    if event.type in _TEAM_EVENTS:
        people = [project.owner, *project.members]
    else:  # actions : responsable de l'action (le nouveau, en cas de réaffectation) et du projet
        assignee_id = event.meta.get("assignee_id", action.assignee_id if action else None)
        people = [db.get(User, assignee_id) if assignee_id else None, project.owner]
    seen, chosen = set(), []
    for user in people:
        if (user and user.is_active and user.notifications_enabled and user.id != event.author_id
                and "@" in user.email and user.email.lower() not in seen):  # un identifiant n'a pas de boîte
            seen.add(user.email.lower())
            chosen.append(user)
    return chosen


def _change(detail: dict, entity_type: str) -> str:
    field = detail.get("field", "")
    name = "Fin prévue" if field == "due_date" and entity_type == "project" else FIELDS.get(field, field)
    return f"{name} : {detail.get('old') or '—'} → {detail.get('new') or '—'}"


def _body_lines(event: Event, action: Action | None, kind: str) -> list[str]:
    first = event.details[0] if event.details else {}
    label = first.get("label", "")
    if kind == "project_created":
        return [f"Le projet « {label} » a été créé."]
    if kind in ("project_status_changed", "action_status_changed"):
        what = "Le statut a changé :" if kind == "project_status_changed" else f"Le statut de l'action « {label} » a changé :"
        lines = [what, first.get("old", ""), "   ↓", first.get("new", "")]
        return lines + ([f"Motif : {first['reason']}"] if first.get("reason") else [])
    if kind == "project_updated":
        return ["Le projet a été modifié :", *(_change(d, "project") for d in event.details)]
    if kind == "comment_added":
        return ["Nouveau commentaire :", f"« {label} »"]
    if kind == "action_overdue":
        due = labels.fmt_date(action.due_date) if action else ""
        return [f"L'action « {label} » est en retard (échéance du {due})."]
    if kind == "action_reassigned":
        change = next(d for d in event.details if d.get("field") == "assignee")
        return [f"L'action « {label} » change de responsable :", f"{change.get('old') or 'Aucun'} → {change.get('new') or 'Aucun'}"]
    # action_created
    lines = [f"Nouvelle action : {label}"]
    if action:
        lines += [f"Responsable : {action.assignee.full_name if action.assignee else 'non affectée'}",
                  f"Échéance : {labels.fmt_date(action.due_date) or '—'}",
                  f"Priorité : {labels.PRIORITY.get(action.priority, action.priority)}"]
    return lines


def build(db: Session, event: Event) -> list[Mail]:
    kind = event.type
    if kind == "action_updated":  # réaffectation (choix du CP) ; les autres modifications d'action ne sont pas notifiées
        if not any(d.get("field") == "assignee" for d in event.details):
            return []
        kind = "action_reassigned"
    if kind not in SUBJECTS:
        return []
    project = db.get(Project, event.project_id)
    action = db.get(Action, event.entity_id) if event.entity_type == "action" else None
    recipients = _recipients(db, event, project, action)
    if not recipients:
        return []
    label = (event.details[0] if event.details else {}).get("label", "")
    subject = labels.clip(f"[Projet {project.title}] {SUBJECTS[kind].format(label=label)}", 290)
    author = db.get(User, event.author_id).full_name if event.author_id else "Tick’ (tâche automatique)"
    when = datetime.now(APP_TZ).strftime("%d/%m/%Y %H:%M")
    url = f"{settings.app_base_url.rstrip('/')}/projects/{project.id}"
    lines = _body_lines(event, action, kind)
    mails = []
    for user in recipients:
        note = [f"(Destinataire réel : {user.email})"] if settings.smtp_test_recipient else []
        text = "\n".join([*lines, "", f"Par : {author}", f"Le : {when}", f"→ Ouvrir le projet : {url}", *note])
        body = "<br>".join(html.escape(line) for line in lines)
        footer = "<br>".join(html.escape(x) for x in (f"Par : {author}", f"Le : {when}", *note))
        page = (f'<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937">'
                f'<p>{body}</p><p style="color:#6b7280">{footer}</p>'
                f'<p><a href="{html.escape(url)}">Ouvrir le projet</a></p></div>')
        mails.append(Mail(user.email, subject, text, page, event.type, project.id))
    return mails


@subscribe
def queue(db: Session, event: Event) -> None:
    """Messages mis de côté jusqu'à la validation de la transaction."""
    try:
        mails = build(db, event)
    except Exception:  # une alerte ne doit jamais faire échouer l'opération métier
        log.exception("Préparation des emails (%s)", event.type)
        return
    db.info.setdefault("outbox", []).extend(mails)


def smtp_transport(message: EmailMessage) -> None:
    factory = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
    with factory(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_security == "starttls":
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


transport: Callable[[EmailMessage], None] = smtp_transport  # remplaçable (tests)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="emails")
run_async: Callable = _executor.submit  # en test : exécution immédiate


def deliver(mails: list[Mail]) -> None:
    with SessionLocal() as db:
        for mail in mails:
            message = EmailMessage()
            message["From"], message["Subject"] = settings.smtp_from, mail.subject
            message["To"] = settings.smtp_test_recipient or mail.to
            message.set_content(mail.text)
            message.add_alternative(mail.html, subtype="html")
            status, error = "sent", None
            try:
                transport(message)
            except Exception as exc:  # consigné, jamais propagé
                status, error = "failed", f"{type(exc).__name__} : {exc}"[:1000]
            db.add(EmailLog(recipient_email=mail.to, subject=mail.subject, event_type=mail.event_type,
                            project_id=mail.project_id, status=status, error=error))
            db.commit()


def flush(timeout: float = 60) -> None:
    """Attend la fin des envois en cours (commandes en ligne avant de rendre la main)."""
    _executor.submit(lambda: None).result(timeout=timeout)


@sa_event.listens_for(SessionLocal, "after_commit")
def _after_commit(session: Session) -> None:
    mails = session.info.pop("outbox", None)
    if mails:
        run_async(deliver, mails)


@sa_event.listens_for(SessionLocal, "after_rollback")
def _after_rollback(session: Session) -> None:
    session.info.pop("outbox", None)


def send_password_link(user: User, url: str, invitation: bool) -> bool:
    """Lien d'activation (nouveau compte) ou de réinitialisation ; faux si le compte n'a pas d'adresse email."""
    if "@" not in user.email:
        return False
    hours = settings.password_link_hours
    if invitation:
        subject = "Tick’ : votre compte est prêt"
        lines = [f"Bonjour {user.first_name},", "", "Un compte Tick’ vient d'être créé pour vous.",
                 "Choisissez votre mot de passe avec ce lien :"]
    else:
        subject = "Tick’ : réinitialisation de votre mot de passe"
        lines = [f"Bonjour {user.first_name},", "", "Pour choisir un nouveau mot de passe, ouvrez ce lien :"]
    after = [f"Le lien est valable {hours} heures et ne sert qu'une fois.",
             "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : votre mot de passe ne change pas."]
    text = "\n".join([*lines, url, "", *after])
    page = (f'<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937">'
            f'<p>{"<br>".join(html.escape(x) for x in lines)}</p>'
            f'<p><a href="{html.escape(url)}">Choisir mon mot de passe</a></p>'
            f'<p style="color:#6b7280">{"<br>".join(html.escape(x) for x in after)}</p></div>')
    run_async(deliver, [Mail(user.email, subject, text, page, "account_invitation" if invitation else "password_reset", None)])
    return True


def list_logs(db: Session, status: str | None = None, limit: int = 300) -> list[EmailLog]:
    query = select(EmailLog).order_by(EmailLog.created_at.desc(), EmailLog.id.desc()).limit(limit)
    return list(db.scalars(query.where(EmailLog.status == status) if status else query))
