"""Résolution des échéances dites en français (DFB B.6), à partir de la date de réunion."""
import calendar
import re
import unicodedata
from datetime import date, timedelta

WEEKDAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b")


def normalize(text: str) -> str:
    """Minuscules, sans accents, apostrophes et tirets remplacés par des espaces, espaces réduits."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"['’\-]", " ", text).split())


def _explicit(match: re.Match, meeting_date: date) -> date | None:
    day, month, year = int(match[1]), int(match[2]), match[3]
    try:
        if year:
            return date(int(year), month, day)
        found = date(meeting_date.year, month, day)
        return found if found >= meeting_date else date(meeting_date.year + 1, month, day)
    except ValueError:  # ex. 31/02
        return None


def resolve(text: str | None, meeting_date: date) -> date | None:
    """Expression d'échéance → date ; None si l'expression n'est pas reconnue (échéance vide)."""
    if not text:
        return None
    t = normalize(text)
    if match := _DATE.search(t):
        return _explicit(match, meeting_date)
    weekday = meeting_date.weekday()  # lundi = 0
    if "apres demain" in t:
        return meeting_date + timedelta(days=2)
    if "aujourd hui" in t:
        return meeting_date
    if "demain" in t:
        return meeting_date + timedelta(days=1)
    if "fin de semaine" in t or "fin de la semaine" in t:  # vendredi ; à partir du vendredi : le suivant
        return meeting_date + timedelta(days=4 - weekday + (7 if weekday >= 4 else 0))
    if "fin de mois" in t or "fin du mois" in t:
        return meeting_date.replace(day=calendar.monthrange(meeting_date.year, meeting_date.month)[1])
    if "semaine prochaine" in t:
        return meeting_date + timedelta(days=7 - weekday)
    for index, name in enumerate(WEEKDAYS):
        if re.search(rf"\b{name}\b", t):  # jour nommé strictement après la réunion
            return meeting_date + timedelta(days=(index - weekday) % 7 or 7)
    return None
