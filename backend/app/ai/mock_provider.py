"""Fournisseur de démonstration (DFB B.3) : règles simples et déterministes, sans appel externe.

Engagements repérés : « Olivier prépare… », « Eric, tu commandes… », « je rédige… » (l'intervenant)
et « il faudra valider… » (sans responsable). L'échéance est l'expression entendue, résolue ensuite en code.
"""
import re
from datetime import date

from app.ai.date_resolver import WEEKDAYS, normalize

# Verbes du premier groupe : radical sans accent → infinitif affiché dans le titre
_STEMS = {
    "prepar": "Préparer", "command": "Commander", "valid": "Valider", "realis": "Réaliser", "redig": "Rédiger",
    "verifi": "Vérifier", "organis": "Organiser", "planifi": "Planifier", "contact": "Contacter",
    "relanc": "Relancer", "install": "Installer", "test": "Tester", "cabl": "Câbler", "configur": "Configurer",
    "livr": "Livrer", "chiffr": "Chiffrer", "finalis": "Finaliser", "document": "Documenter", "migr": "Migrer",
    "sauvegard": "Sauvegarder", "remplac": "Remplacer", "demand": "Demander", "confirm": "Confirmer",
    "partag": "Partager", "lanc": "Lancer", "deploi": "Déployer", "deploy": "Déployer", "envoi": "Envoyer",
    "envoy": "Envoyer", "appel": "Appeler", "appell": "Appeler", "mett": "Mettre", "reserv": "Réserver",
}
VERBS = {stem + end: inf for stem, inf in _STEMS.items() for end in ("e", "es", "er", "era", "eras", "erai", "ez", "ons")}
VERBS |= {"enverra": "Envoyer", "enverras": "Envoyer", "met": "Mettre", "mets": "Mettre", "mettra": "Mettre"}

_NOT_NAMES = {"il", "elle", "on", "je", "tu", "nous", "vous", "ils", "elles", "le", "la", "les", "un", "une", "ce",
              "cette", "et", "mais", "donc", "alors", "puis", "ensuite", "oui", "non", "bon", "bien", "ok", "si"}
_OBLIGATION = {"faut", "faudra", "faudrait", "doit", "devra", "devrait"}
_DETERMINERS = {"le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "mon", "ma", "mes", "ton", "ta",
                "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs", "ce", "cet", "cette", "ces"}
_STOPS = {"pour", "avant", "demain", "apres demain", "aujourd", "hui", "ici", "fin", "semaine", "si", "quand",
          "rapidement", "urgent", "urgence", *WEEKDAYS}
_TRAILING = {"en", "de", "d", "du", "le", "la", "les", "l", "a", "au", "et"}
_DUE = {"apres demain": "après-demain", "aujourd hui": "aujourd'hui", "demain": "demain",
        "fin de la semaine": "fin de semaine", "fin de semaine": "fin de semaine", "fin du mois": "fin de mois",
        "fin de mois": "fin de mois", "semaine prochaine": "semaine prochaine"}
_TOKEN = re.compile(r"\d{1,2}/\d{1,2}(?:/\d{4})?|\w+(?:-\w+)*|[,?!.;:]")
_SPEAKER = re.compile(r"^\s*([^:]{1,80}?)\s*:\s+(.+)$")


def _is_name(token: str) -> bool:
    return token[:1].isupper() and token.replace("-", "").isalpha() and normalize(token) not in _NOT_NAMES


def _commitment(tokens: list[str], speaker: str | None) -> tuple[int, str, str | None] | None:
    """(position du verbe, infinitif, responsable entendu) ou None."""
    norms = [normalize(t) for t in tokens]
    for i, norm in enumerate(norms):
        infinitive = VERBS.get(norm)
        if not infinitive or i == 0:
            continue
        before = norms[i - 1]
        if _is_name(tokens[i - 1]):                                   # « Olivier prépare »
            return i, infinitive, tokens[i - 1]
        if before == "tu" and i >= 3 and tokens[i - 2] == "," and _is_name(tokens[i - 3]):  # « Eric, tu commandes »
            return i, infinitive, tokens[i - 3]
        if before in ("je", "j"):                                     # « je rédige » : l'intervenant
            return i, infinitive, speaker
        if before in _OBLIGATION:                                     # « il faudra valider »
            return i, infinitive, None
    return None


def _title(tokens: list[str], verb_at: int, infinitive: str) -> str:
    words = []
    for token in tokens[verb_at + 1:]:
        norm = normalize(token)
        if token in ",?!.;:" or norm in _STOPS or token[:1].isdigit():
            break
        words.append(token)
    while words and normalize(words[0]) in _DETERMINERS:
        words.pop(0)
    while words and normalize(words[-1]) in _TRAILING:
        words.pop()
    return " ".join([infinitive, *words])


def _due_text(sentence: str) -> str | None:
    if match := re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{4})?\b", sentence):
        return match[0]
    norm = normalize(sentence)
    for expression, spoken in _DUE.items():
        if expression in norm:
            return spoken
    return next((day for day in WEEKDAYS if re.search(rf"\b{day}\b", norm)), None)


def _priority(sentence: str) -> str:
    norm = normalize(sentence)
    if "critique" in norm or "bloquant" in norm:
        return "critical"
    return "high" if any(w in norm for w in ("urgent", "urgence", "au plus vite", "prioritaire")) else "medium"


class MockProvider:
    name = "mock"

    def extract(self, transcript: str, meeting_date: date, participants: list[str]) -> dict:
        actions, topics, decisions, open_points = [], [], [], []
        for line in transcript.splitlines():
            match = _SPEAKER.match(line)
            speaker, text = (match[1], match[2]) if match else (None, line)
            for sentence in filter(None, (s.strip() for s in re.split(r"(?<=[.!?])\s+", text))):
                norm = normalize(sentence)
                if "rien a faire" not in norm and (found := _commitment(_TOKEN.findall(sentence), speaker)):
                    verb_at, infinitive, assignee = found
                    actions.append({"title": _title(_TOKEN.findall(sentence), verb_at, infinitive),
                                    "assignee_name": assignee, "due_date_text": _due_text(sentence),
                                    "priority": _priority(sentence), "source_quote": sentence})
                elif any(k in norm for k in ("on valide", "decide", "d accord pour", "on part sur", "c est acte")):
                    decisions.append(sentence)
                elif sentence.endswith("?"):
                    open_points.append(sentence)
                elif any(k in norm for k in ("parle", "point sur", "sujet", "ordre du jour", "avancement")):
                    topics.append(sentence)
        context = (f"Réunion du {meeting_date:%d/%m/%Y}"
                   f"{' avec ' + ', '.join(participants) if participants else ''}. "
                   "Synthèse produite par le fournisseur de démonstration (règles simples, sans IA).")
        return {"summary": {"context": context, "topics": topics, "decisions": decisions,
                            "open_points": open_points}, "actions": actions}
