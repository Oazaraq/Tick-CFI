"""Application d'un PATCH champ par champ, avec le détail historisable de ce qui a changé (RG07)."""
from app.services import labels
from app.services.errors import Invalid


def apply_changes(obj, data, fields: tuple[str, ...], required: tuple[str, ...] = (),
                  mappings: dict[str, dict] | None = None) -> list[dict]:
    changes = []
    for field in fields:
        if field not in data.model_fields_set:
            continue
        new = getattr(data, field)
        if isinstance(new, str):
            new = new.strip() or None
        if new is None and field in required:
            raise Invalid("Un champ obligatoire est vide")
        old = getattr(obj, field)
        if new != old:
            setattr(obj, field, new)
            mapping = (mappings or {}).get(field)
            changes.append({"field": field, "old": labels.fmt(field, old, mapping), "new": labels.fmt(field, new, mapping)})
    return changes


def person_change(field: str, old, new) -> dict:
    return {"field": field, "old": old.full_name if old else "", "new": new.full_name if new else ""}
