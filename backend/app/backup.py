"""Sauvegarde et restauration (lot 5) : base SQLite copiée de façon cohérente, application en marche ou non,
et fichiers déposés. Une archive .tar.gz contient `tickson.db` et le dossier `files/`.

    python -m app.backup create [dossier]   → <dossier>/tickson-AAAAMMJJ-HHMMSS.tar.gz (défaut : /backups)
    python -m app.backup restore <archive>  → remplace la base et les fichiers (backend arrêté : `make restore`)
"""
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from app.config import APP_TZ, settings


def database_path() -> Path:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        raise SystemExit("Sauvegarde prévue pour SQLite uniquement (DATABASE_URL=sqlite:///…)")
    return Path(settings.database_url[len(prefix):])


def _copy_database(source: Path, target: Path) -> None:
    """API de sauvegarde de SQLite : copie cohérente même pendant des écritures (mode WAL compris)."""
    src, dst = sqlite3.connect(source), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()


def create(folder: str = "/backups") -> Path:
    target_dir = Path(folder)
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / f"tickson-{datetime.now(APP_TZ):%Y%m%d-%H%M%S}.tar.gz"
    files_dir = Path(settings.files_dir)
    with tempfile.TemporaryDirectory() as work:
        snapshot = Path(work) / "tickson.db"
        _copy_database(database_path(), snapshot)
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(snapshot, arcname="tickson.db")
            tar.add(files_dir if files_dir.exists() else work, arcname="files", recursive=files_dir.exists())
    return archive


def restore(archive: str) -> None:
    with tempfile.TemporaryDirectory() as work, tarfile.open(archive, "r:gz") as tar:
        tar.extractall(work, filter="data")  # refuse les chemins absolus ou sortant du dossier
        snapshot, files = Path(work) / "tickson.db", Path(work) / "files"
        if not snapshot.is_file():
            raise SystemExit("Archive invalide : tickson.db absent")
        _copy_database(snapshot, database_path())  # écrase la base en place
        target = Path(settings.files_dir)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(files, target) if files.is_dir() else target.mkdir(parents=True)


if __name__ == "__main__":
    command, *args = sys.argv[1:] or ["create"]
    if command == "create":
        print(f"Sauvegarde créée : {create(*args)}")
    elif command == "restore" and args:
        restore(args[0])
        print(f"Restauration terminée depuis {args[0]}")
    else:
        raise SystemExit(__doc__)
