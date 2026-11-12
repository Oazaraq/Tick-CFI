"""Libellés français des valeurs métier (historique, puis emails au lot 3)."""
PRIORITY = {"low": "Basse", "medium": "Moyenne", "high": "Haute", "critical": "Critique"}
ACTION_STATUS = {"todo": "À faire", "in_progress": "En cours", "blocked": "Bloquée", "done": "Terminée", "cancelled": "Annulée"}
PROBABILITY = {"low": "Faible", "medium": "Moyenne", "high": "Élevée"}
IMPACT = {"low": "Faible", "medium": "Moyen", "high": "Élevé"}
RISK_STATUS = {"open": "Ouvert", "watched": "Surveillé", "mitigated": "Atténué", "closed": "Clos", "occurred": "Survenu"}
KIND = {"phase": "Phase", "milestone": "Jalon"}
SOURCING = {"internal": "Interne", "external": "Externe"}
# Avenant 3 : catégories de charge des projets d'infrastructure (l'ordre est celui des listes)
HOURS_PER_DAY = 7.5  # une journée de chef de projet
HOURLY_CATEGORY = "project_management"  # seule catégorie saisie à l'heure ; les ingénieurs se vendent par demi-journée

CATEGORY = {
    "infrastructure": "Ingénierie infrastructure",
    "network": "Ingénierie réseau",
    "security": "Ingénierie cybersécurité",
    "storage": "Ingénierie stockage",
    "backup": "Ingénierie sauvegarde",
    "cloud": "Ingénierie cloud",
    "workplace": "Poste de travail",
    "project_management": "Gestion de projet",
    "governance": "Gouvernance et conseil",
    "training": "Formation et transfert de compétences",
    "other": "Autre",
}
_BY_FIELD = {"priority": PRIORITY, "probability": PROBABILITY, "impact": IMPACT, "kind": KIND,
             "sourcing": SOURCING, "category": CATEGORY}
_DATE_FIELDS = ("start_date", "due_date", "end_date")


def fmt_date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def clip(text: str, size: int = 120) -> str:
    return text if len(text) <= size else text[: size - 1] + "…"


def fmt(field: str, value, mapping: dict | None = None) -> str:
    """Valeur affichable d'un champ, figée dans l'historique au moment du changement."""
    if value is None or value == "":
        return ""
    table = mapping or _BY_FIELD.get(field)
    if table:
        return table.get(value, value)
    if field in _DATE_FIELDS:
        return fmt_date(value)
    if field in ("days_sold", "days_consumed"):
        return f"{value:g} j".replace(".", ",")
    return clip(str(value))
