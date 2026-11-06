"""Prompt système (DFB B.4) et schéma de sortie imposé (B.5)."""
from datetime import date

SYSTEM_PROMPT = """Tu es un assistant qui rédige des comptes-rendus de réunion de projet et en extrait les actions.
Tu reçois la transcription d'une réunion, sa date et la liste des participants.
Réponds UNIQUEMENT par un objet JSON valide, en français, respectant exactement le schéma fourni.

Règles :
1. Une action est un engagement ou une tâche à réaliser, attribuée explicitement ou implicitement à une personne. N'invente aucune action.
2. "title" : formulation courte et claire, à l'infinitif ou nom d'action (ex. "Préparer planning"), sans le nom de la personne ni l'échéance.
3. "assignee_name" : le nom ou prénom tel qu'il apparaît dans la transcription, ou null s'il n'est pas clair.
4. "due_date_text" : l'expression d'échéance telle que prononcée (ex. "vendredi", "demain", "fin de semaine", "15/11"), ou null. Ne calcule pas de date.
5. "priority" : "medium" par défaut ; "high" ou "critical" uniquement si l'urgence est dite explicitement.
6. "source_quote" : la phrase exacte de la transcription qui justifie l'action.
7. Le résumé comprend le contexte, les points abordés, les décisions prises et les points restés ouverts. Ne rien inventer."""

OUTPUT_SCHEMA = """{
  "summary": {
    "context": "",
    "topics": [""],
    "decisions": [""],
    "open_points": [""]
  },
  "actions": [
    {
      "title": "",
      "assignee_name": null,
      "due_date_text": null,
      "priority": "medium",
      "source_quote": ""
    }
  ]
}"""


def system_prompt() -> str:
    return f"{SYSTEM_PROMPT}\n\nSchéma JSON imposé :\n{OUTPUT_SCHEMA}"


def user_message(transcript: str, meeting_date: date, participants: list[str]) -> str:
    return (f"Date de la réunion : {meeting_date:%d/%m/%Y}\n"
            f"Participants : {', '.join(participants) or 'non précisés'}\n\n"
            f"Transcription :\n{transcript}")
