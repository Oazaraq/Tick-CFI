"""Horloge métier : la « date du jour » s'entend à Paris (RG05)."""
from datetime import date, datetime, timezone

from app.config import APP_TZ


def today() -> date:
    return datetime.now(APP_TZ).date()


def now() -> datetime:
    return datetime.now(timezone.utc)
