"""Check-list de lancement par projet : ce que l'avant-vente doit avoir sécurisé avant l'intervention.

Le modèle (5 groupes, 15 points) vit ici : le faire évoluer met à jour toutes les check-lists. Chaque projet ne
stocke que ses états (statut, note), ses points ajoutés et son calculateur d'énergie. Chaque enregistrement est
historisé point par point, sans email.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.models import Project, ProjectChecklist, User
from app.services.errors import Conflict, Invalid
from app.services.events import Event, emit
from app.services.labels import clip


def _it(id_: str, point: str, question: str, owner: str, blocking: bool) -> dict:
    return {"id": id_, "point": point, "question": question, "owner": owner, "blocking": blocking}


TEMPLATE = [
    {"code": "SITE", "title": "Site et baie", "items": [
        _it("SITE-01", "Matériel sur site", "Matériel livré, complet et stocké sur site, ou date de livraison confirmée "
                                              "avant l'intervention", "CFI", True),
        _it("SITE-02", "Accès salle", "Date, horaires, badge et contact sur place confirmés", "Client", True),
        _it("SITE-03", "Place en baie", "U libres réservés, rails fournis et compatibles avec la baie (profondeur, "
                                         "montants)", "Avant-vente", True)]},
    {"code": "ENE", "title": "Énergie et climatisation", "calc": True,
     "note": "1 W dissipé = 3,412 BTU/h. Le calculateur donne la charge ajoutée.", "items": [
        _it("ENE-01", "Électricité", "Onduleur avec marge suffisante, prises du bon type disponibles sur deux voies A/B",
            "Avant-vente", True),
        _it("ENE-02", "Climatisation", "Capacité de la salle suffisante pour la charge ajoutée", "Avant-vente", False)]},
    {"code": "RES", "title": "Réseau", "items": [
        _it("RES-01", "Ports switches", "Ports libres du bon type (RJ45, SFP+…) réservés pour chaque équipement et sa "
                                         "carte de gestion", "Avant-vente", True),
        _it("RES-02", "Câbles et transceivers", "Cordons, jarretières et modules en bon nombre et bonne longueur, "
                                                 "commandés ou sur site", "CFI", True),
        _it("RES-03", "Adressage et VLAN", "Plan IP, VLAN et nommage reçus et validés par le client", "Client", True),
        _it("RES-04", "Accès et comptes", "Comptes administrateur et accès distant disponibles pour la préparation",
            "Client", False)]},
    {"code": "COM", "title": "Commande et licences", "items": [
        _it("COM-01", "Commande", "Bon de commande reçu et validé", "CFI", True),
        _it("COM-02", "Licences", "Licences reçues, clés récupérées et activables", "CFI", True),
        _it("COM-03", "Support", "Contrats de support enregistrés sur les bons numéros de série", "CFI", False)]},
    {"code": "PLA", "title": "Planning et recette", "items": [
        _it("PLA-01", "Intervention planifiée", "Date, durée et fenêtre de coupure validées par le client, intervenant "
                                                 "CFI affecté", "CFI", True),
        _it("PLA-02", "Sauvegarde de l'existant", "Sauvegarde récente vérifiée avant toute bascule (sans objet si pas "
                                                   "de migration)", "Client", False),
        _it("PLA-03", "Recette", "Critères de recette et PV d'intervention partagés avec le client", "CFI", False)]},
]
SECTIONS = {s["code"] for s in TEMPLATE}
STATUS_LABELS = {"": "—", "ok": "OK", "ko": "KO", "tbc": "À confirmer", "na": "N/A"}
META_LABELS = {"client": "Client", "kickoff_date": "Date du kickoff", "participants": "Participants",
               "order_ref": "Commande / BOM"}
EMPTY = {"meta": {}, "states": {}, "custom": [], "calc": [{"name": "", "qty": 1, "watts": None, "units": None}]}


def _find(db: Session, project: Project) -> ProjectChecklist | None:
    return db.scalar(select(ProjectChecklist).where(ProjectChecklist.project_id == project.id))


def out(db: Session, project: Project) -> dict:
    found = _find(db, project)
    data = found.data if found else EMPTY
    return {**EMPTY, **data, "sections": TEMPLATE, "revision": found.revision if found else 0,
            "updated_at": found.updated_at if found else None, "updated_by": found.editor if found else None}


def _labels(data: dict) -> dict[str, str]:
    items = [i for s in TEMPLATE for i in s["items"]] + list(data.get("custom", []))
    return {i["id"]: i["point"] if i["id"].startswith("X-") else f"{i['id']} · {i['point']}" for i in items}


def _changes(old: dict, new: dict) -> dict[str, list[dict]]:
    """Différences lisibles, par type d'événement d'historique (valeurs figées au moment de l'écriture)."""
    found: dict[str, list[dict]] = {}
    add = lambda kind, detail: found.setdefault(kind, []).append(detail)  # noqa: E731
    before, after = _labels(old), _labels(new)
    for item_id in after.keys() - before.keys():
        add("checklist_item_added", {"label": after[item_id]})
    for item_id in before.keys() - after.keys():
        add("checklist_item_removed", {"label": before[item_id]})
    for item_id, label in after.items():
        was, now = old.get("states", {}).get(item_id, {}), new["states"].get(item_id, {})
        if was.get("status", "") != now.get("status", ""):
            add("checklist_status_changed", {"label": label, "old": STATUS_LABELS[was.get("status", "")],
                                             "new": STATUS_LABELS[now.get("status", "")]})
        if (was.get("note") or "") != (now.get("note") or ""):
            add("checklist_note_updated", {"label": label})
    for key, name in META_LABELS.items():
        was, now = old.get("meta", {}).get(key) or "", new["meta"].get(key) or ""
        if was != now:
            add("checklist_info_updated", {"label": name, "old": clip(str(was), 80) or "—", "new": clip(str(now), 80) or "—"})
    return found


def save(db: Session, actor: User, project: Project, data) -> None:
    found = _find(db, project)
    if data.revision != (found.revision if found else 0):
        who = found.editor.full_name if found and found.editor else "un autre utilisateur"
        raise Conflict(f"La check-list vient d'être modifiée par {who} : elle a été rechargée, refaites votre dernier "
                       "changement")
    for item in data.custom:
        if item.section not in SECTIONS:
            raise Invalid(f"Groupe inconnu : {item.section}")
    if len({i.id for i in data.custom}) != len(data.custom):
        raise Invalid("Deux points ajoutés portent le même identifiant")
    new = data.model_dump(mode="json", exclude={"revision"})
    known = _labels(new)
    new["states"] = {k: v for k, v in new["states"].items() if k in known}  # états d'un point retiré : abandonnés
    for kind, details in _changes(found.data if found else EMPTY, new).items():
        emit(db, Event(kind, project.id, "checklist", project.id, actor.id, details))
    if found is None:
        found = ProjectChecklist(project_id=project.id, revision=0)
        db.add(found)
    found.data, found.revision = new, found.revision + 1
    found.updated_by, found.updated_at = actor.id, clock.now()
    db.commit()
