"""Reporting de charge : jours vendus et consommés par projet et par catégorie, sur les projets visibles."""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlanningItem, Project, User
from app.services import labels
from app.services.teams import visible_to

NO_CATEGORY = "Sans catégorie"


def effort_rows(db: Session, user: User) -> list[dict]:
    projects = {p.id: p for p in db.scalars(select(Project).where(Project.deleted_at.is_(None), visible_to(user)))}
    totals: dict[tuple[int, str | None], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for item in db.scalars(select(PlanningItem).where(PlanningItem.project_id.in_(projects), PlanningItem.kind == "phase")):
        if item.days_sold is None and item.days_consumed is None:
            continue
        total = totals[(item.project_id, item.category)]
        total[0] += item.days_sold or 0
        total[1] += item.days_consumed or 0
    rows = []
    for (project_id, category), (sold, consumed) in totals.items():
        p = projects[project_id]
        rows.append({"project_id": p.id, "title": p.title, "status_code": p.status.code, "status_label": p.status.label,
                     "owner": p.owner, "category": category,
                     "category_label": labels.CATEGORY.get(category, NO_CATEGORY) if category else NO_CATEGORY,
                     "sold": round(sold, 4), "consumed": round(consumed, 4)})
    return sorted(rows, key=lambda r: (r["title"].lower(), r["category_label"]))
