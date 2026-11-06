"""Fichiers « en dur » des projets (avenant 3) : stockés dans le volume, supprimés N jours après la livraison.

Pas d'antivirus en V1 (décision RSSI attendue) : liste fermée d'extensions, contrôle de la signature du
contenu, taille limitée, nom de stockage aléatoire, téléchargement toujours en pièce jointe.
"""
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.config import settings
from app.models import KanbanStatus, Project, ProjectFile, User
from app.services import teams
from app.services.errors import Invalid, NotFound
from app.services.events import Event, emit

_ZIP, _OLE = b"PK\x03\x04", b"\xd0\xcf\x11\xe0"
_OFFICE = "application/vnd.openxmlformats-officedocument."
_ODF = "application/vnd.oasis.opendocument."
ALLOWED: dict[str, tuple[str, tuple[bytes, ...] | None]] = {  # extension → (type servi, signatures acceptées)
    "pdf": ("application/pdf", (b"%PDF",)),
    "docx": (_OFFICE + "wordprocessingml.document", (_ZIP,)),
    "xlsx": (_OFFICE + "spreadsheetml.sheet", (_ZIP,)),
    "pptx": (_OFFICE + "presentationml.presentation", (_ZIP,)),
    "doc": ("application/msword", (_OLE,)),
    "xls": ("application/vnd.ms-excel", (_OLE,)),
    "ppt": ("application/vnd.ms-powerpoint", (_OLE,)),
    "odt": (_ODF + "text", (_ZIP,)),
    "ods": (_ODF + "spreadsheet", (_ZIP,)),
    "odp": (_ODF + "presentation", (_ZIP,)),
    "png": ("image/png", (b"\x89PNG",)),
    "jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    "jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    "txt": ("text/plain; charset=utf-8", None),
    "csv": ("text/csv; charset=utf-8", None),
}


def storage() -> Path:
    path = Path(settings.files_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_name(name: str) -> str:
    """Nom affiché : sans chemin ni caractère réservé."""
    name = Path((name or "").replace("\\", "/")).name
    name = "".join(c for c in name if c.isprintable() and c not in '<>:"/\\|?*').strip(" .")
    return name[-200:] or "fichier"


def purge_date(project: Project) -> date | None:
    if project.status.code == "done" and project.end_date:
        return project.end_date + timedelta(days=settings.files_purge_days)
    return None


def list_files(db: Session, project_id: int) -> list[ProjectFile]:
    return list(db.scalars(select(ProjectFile).where(ProjectFile.project_id == project_id)
                           .order_by(ProjectFile.created_at.desc(), ProjectFile.id.desc())))


def get_file(db: Session, file_id: int, viewer: User) -> ProjectFile:
    found = db.get(ProjectFile, file_id)
    if found is None or teams.hidden(db, found.project_id, viewer):
        raise NotFound("Fichier introuvable")
    return found


def add_file(db: Session, actor: User, project: Project, filename: str, data: bytes) -> ProjectFile:
    name = safe_name(filename)
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in ALLOWED:
        raise Invalid("Type de fichier non accepté : PDF, Word, Excel, PowerPoint, OpenDocument, image, texte ou CSV")
    if not data:
        raise Invalid("Le fichier est vide")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise Invalid(f"Fichier trop volumineux : {settings.max_upload_mb} Mo au maximum")
    media_type, signatures = ALLOWED[extension]
    if signatures is not None and not data.startswith(signatures) or signatures is None and b"\x00" in data[:8192]:
        raise Invalid("Le contenu du fichier ne correspond pas à son extension")
    stored = f"{uuid4().hex}.{extension}"
    path = storage() / stored
    path.write_bytes(data)
    try:
        item = ProjectFile(project_id=project.id, filename=name, stored_name=stored, content_type=media_type,
                           size=len(data), uploaded_by=actor.id)
        db.add(item)
        db.flush()
        emit(db, Event("file_added", project.id, "document", item.id, actor.id, [{"label": name}]))
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return item


def path_of(item: ProjectFile) -> Path:
    return storage() / item.stored_name


def delete_file(db: Session, actor: User, item: ProjectFile) -> None:
    path = path_of(item)  # avant la validation, qui expire l'objet supprimé
    emit(db, Event("file_deleted", item.project_id, "document", item.id, actor.id, [{"label": item.filename}]))
    db.delete(item)
    db.commit()
    path.unlink(missing_ok=True)


def purge(db: Session) -> int:
    """Supprime définitivement les fichiers des projets livrés depuis FILES_PURGE_DAYS jours ; renvoie leur nombre."""
    limit = clock.today() - timedelta(days=settings.files_purge_days)
    rows = db.execute(select(ProjectFile, Project).join(Project, ProjectFile.project_id == Project.id)
                      .join(KanbanStatus, Project.status_id == KanbanStatus.id)
                      .where(KanbanStatus.code == "done", Project.end_date <= limit)).all()
    by_project: dict[int, list[ProjectFile]] = {}
    for item, project in rows:
        by_project.setdefault(project.id, []).append(item)
    paths = [path_of(item) for item, _ in rows]
    for project_id, items in by_project.items():
        emit(db, Event("files_purged", project_id, "document", project_id, None, [{"count": len(items)}]))
        for item in items:
            db.delete(item)
    db.commit()
    for path in paths:
        path.unlink(missing_ok=True)
    return len(rows)
