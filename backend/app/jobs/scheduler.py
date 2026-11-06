"""Tâches planifiées (APScheduler, dans le processus du backend : un seul worker uvicorn).

Au démarrage (redémarrage du conteneur, réveil en mode serverless), les passages manqués sont rattrapés :
les deux tâches sont idempotentes.
"""
import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import APP_TZ, settings
from app.db import SessionLocal
from app.jobs import overdue_job
from app.services import files

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def purge_files() -> int:
    with SessionLocal() as db:
        return files.purge(db)


def catch_up() -> None:
    try:
        if datetime.now(APP_TZ).hour >= settings.overdue_job_hour:
            overdue_job.run()
        purge_files()
    except Exception:
        log.exception("Rattrapage des tâches planifiées")


def start() -> None:
    global _scheduler
    if not settings.scheduler_enabled or _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=APP_TZ, job_defaults={"coalesce": True, "misfire_grace_time": 3600})
    _scheduler.add_job(overdue_job.run, CronTrigger(hour=settings.overdue_job_hour, minute=0, timezone=APP_TZ), id="overdue")
    _scheduler.add_job(purge_files, CronTrigger(hour=3, minute=30, timezone=APP_TZ), id="purge_files")
    _scheduler.start()
    threading.Thread(target=catch_up, name="catch-up", daemon=True).start()


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
