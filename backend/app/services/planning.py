"""Avenants 1 et 3 : phases et jalons du planning (Gantt), charge en j/h par phase, dépendances.

Un jalon n'a qu'une date et ne porte pas de charge. Les dépendances ne recalculent aucune date :
elles signalent seulement un ordre non respecté.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import PlanningItem, Project, User
from app.services import labels, teams
from app.services.changes import apply_changes
from app.services.errors import Invalid, NotFound
from app.services.events import Event, emit

FIELDS = ("label", "kind", "start_date", "end_date", "category", "days_sold", "days_consumed")


def get_item(db: Session, item_id: int, viewer: User) -> PlanningItem:
    item = db.get(PlanningItem, item_id)
    if item is None or teams.hidden(db, item.project_id, viewer):
        raise NotFound("Élément de planning introuvable")
    return item


def list_items(db: Session, project_id: int) -> list[PlanningItem]:
    return list(db.scalars(select(PlanningItem).where(PlanningItem.project_id == project_id)
                           .options(selectinload(PlanningItem.predecessors))
                           .order_by(PlanningItem.start_date, PlanningItem.position, PlanningItem.id)))


def dependency_issues(item: PlanningItem) -> list[int]:
    """Prédécesseurs qui finissent après le début de l'élément (le même jour est admis)."""
    return sorted(p.id for p in item.predecessors if item.start_date < p.end_date)


def _normalize(item: PlanningItem) -> None:
    if item.kind == "milestone":
        item.end_date = item.start_date
        item.category = item.days_sold = item.days_consumed = None
    if item.end_date < item.start_date:
        raise Invalid("La fin doit être postérieure ou égale au début")
    if item.category is not None and item.category not in labels.CATEGORY:
        raise Invalid("Catégorie de charge inconnue")
    for field in ("days_sold", "days_consumed"):  # heures converties en jours : 4 décimales suffisent
        if getattr(item, field) is not None:
            setattr(item, field, round(getattr(item, field), 4))


def _check_units(item: PlanningItem) -> None:
    """Ingénieurs vendus à la journée ou à la demi-journée ; la gestion de projet se saisit à l'heure (1 j = 7,5 h)."""
    if item.category == labels.HOURLY_CATEGORY:
        return
    for value in (item.days_sold, item.days_consumed):
        if value is not None and abs(value * 2 - round(value * 2)) > 1e-6:
            raise Invalid("Hors gestion de projet, la charge se compte en journées ou demi-journées (multiple de 0,5 j)")


def _predecessors(db: Session, item: PlanningItem, ids: list[int]) -> list[PlanningItem]:
    if item.id is not None and item.id in ids:
        raise Invalid("Un élément ne peut pas dépendre de lui-même")
    found = list(db.scalars(select(PlanningItem).where(PlanningItem.id.in_(ids)))) if ids else []
    if len(found) != len(set(ids)) or any(p.project_id != item.project_id for p in found):
        raise Invalid("Prédécesseur inconnu ou d'un autre projet")
    if item.id is not None:  # un élément neuf ne peut pas fermer un cycle
        items = list_items(db, item.project_id)
        graph = {i.id: [p.id for p in i.predecessors] for i in items}
        names = {i.id: i.label for i in items}
        for start in ids:
            stack, seen = [start], set()
            while stack:
                node = stack.pop()
                if node == item.id:
                    raise Invalid(f"Dépendance circulaire : « {names[start]} » dépend déjà, directement ou non, "
                                  f"de « {item.label} »")
                if node not in seen:
                    seen.add(node)
                    stack.extend(graph.get(node, []))
    return found


def _names(items: list[PlanningItem]) -> str:
    return ", ".join(sorted(i.label for i in items))


def create_item(db: Session, actor: User, project: Project, data) -> PlanningItem:
    label = data.label.strip()
    if not label:
        raise Invalid("Le libellé est obligatoire")
    count = db.scalar(select(func.count()).select_from(PlanningItem).where(PlanningItem.project_id == project.id))
    item = PlanningItem(project_id=project.id, label=label, kind=data.kind, start_date=data.start_date,
                        end_date=data.end_date or data.start_date, position=count, category=data.category or None,
                        days_sold=data.days_sold, days_consumed=data.days_consumed)
    _normalize(item)
    _check_units(item)
    item.predecessors = _predecessors(db, item, data.predecessor_ids)
    db.add(item)
    db.flush()
    emit(db, Event("planning_item_created", project.id, "planning_item", item.id, actor.id, [{"label": label}]))
    db.commit()
    return item


def update_item(db: Session, actor: User, item: PlanningItem, data) -> PlanningItem:
    kind = data.kind if "kind" in data.model_fields_set and data.kind else item.kind
    fields = FIELDS if kind == "phase" else ("label", "kind", "start_date")  # un jalon : une seule date, aucune charge
    changes = apply_changes(item, data, fields, required=("label", "kind", "start_date", "end_date"))
    _normalize(item)
    if {"category", "days_sold", "days_consumed"} & data.model_fields_set:  # une saisie ancienne reste modifiable
        _check_units(item)
    if data.predecessor_ids is not None and "predecessor_ids" in data.model_fields_set:
        new = _predecessors(db, item, data.predecessor_ids)
        if {p.id for p in new} != {p.id for p in item.predecessors}:
            changes.append({"field": "predecessors", "old": _names(item.predecessors), "new": _names(new)})
            item.predecessors = new
    if changes:
        emit(db, Event("planning_item_updated", item.project_id, "planning_item", item.id, actor.id,
                       [{**c, "label": item.label} for c in changes]))
    db.commit()
    return item


def delete_item(db: Session, actor: User, item: PlanningItem) -> None:
    emit(db, Event("planning_item_deleted", item.project_id, "planning_item", item.id, actor.id, [{"label": item.label}]))
    db.delete(item)  # ses liens de dépendance partent avec lui
    db.commit()


def effort(db: Session, project_id: int) -> dict:
    """Totaux vendus / consommés par catégorie, dans l'ordre des catégories."""
    rows = db.execute(select(PlanningItem.category, func.sum(PlanningItem.days_sold), func.sum(PlanningItem.days_consumed))
                      .where(PlanningItem.project_id == project_id, PlanningItem.category.is_not(None))
                      .group_by(PlanningItem.category))
    sums = {code: (sold or 0, consumed or 0) for code, sold, consumed in rows}
    lines = [{"code": code, "label": label, "sold": sums[code][0], "consumed": sums[code][1]}
             for code, label in labels.CATEGORY.items() if code in sums]
    totals = db.execute(select(func.sum(PlanningItem.days_sold), func.sum(PlanningItem.days_consumed))
                        .where(PlanningItem.project_id == project_id)).one()
    return {"categories": lines, "sold": totals[0] or 0, "consumed": totals[1] or 0}
