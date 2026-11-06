"""Interface fournisseur IA (DFB B.3), contrôle de la sortie, découpage des longues transcriptions.

Appels HTTP directs (bibliothèque standard) : aucun SDK, aucune dépendance ajoutée.
"""
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings


class LLMError(Exception):
    """Échec du fournisseur : le message est affiché tel quel à l'utilisateur (S17)."""


class Summary(BaseModel):
    context: str = ""
    topics: list[str] = []
    decisions: list[str] = []
    open_points: list[str] = []

    @field_validator("topics", "decisions", "open_points", mode="before")
    @classmethod
    def _drop_empty(cls, items):  # le schéma d'exemple contient [""] : on retire les entrées vides
        return [i for i in items or [] if isinstance(i, str) and i.strip()]


class Candidate(BaseModel):
    title: str = Field(min_length=1)
    assignee_name: str | None = None
    due_date_text: str | None = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    source_quote: str = ""

    @field_validator("title")
    @classmethod
    def _short_title(cls, value: str) -> str:
        return value.strip()[:200]


class Extraction(BaseModel):
    summary: Summary = Summary()
    actions: list[Candidate] = []


class LLMProvider(Protocol):
    name: str

    def extract(self, transcript: str, meeting_date: date, participants: list[str]) -> dict: ...


def parse(text: str) -> dict:
    """Objet JSON de la réponse (éventuellement entouré de texte ou de ```json), validé par le schéma B.5."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("aucun objet JSON")
    return Extraction.model_validate(json.loads(text[start:end + 1])).model_dump()


def extract_json(call: Callable[[], str]) -> dict:
    """B.3 : une réponse invalide déclenche une seule nouvelle tentative, puis l'échec."""
    for _ in range(2):
        try:
            return parse(call())
        except (ValueError, ValidationError):
            continue
    raise LLMError("La réponse de l'IA n'est pas exploitable (JSON invalide), même après une nouvelle tentative.")


def post_json(url: str, body: dict, headers: dict, service: str) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    timeout = settings.llm_timeout_seconds
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise LLMError(f"{service} : accès refusé, vérifiez la clé ou les droits.") from exc
        if exc.code == 429:
            raise LLMError(f"{service} : limite de requêtes atteinte, réessayez dans quelques minutes.") from exc
        detail = exc.read().decode(errors="replace")[:200]
        raise LLMError(f"{service} : erreur {exc.code} ({detail}).") from exc
    except TimeoutError as exc:
        raise LLMError(f"{service} : pas de réponse en {timeout} s.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise LLMError(f"{service} : pas de réponse en {timeout} s.") from exc
        raise LLMError(f"{service} injoignable ({exc.reason}).") from exc
    except ValueError as exc:
        raise LLMError(f"{service} : réponse illisible.") from exc


def split(transcript: str, size: int) -> list[str]:
    """Blocs d'au plus `size` caractères, coupés entre deux lignes (une ligne plus longue reste entière)."""
    blocks, current = [], ""
    for line in transcript.splitlines(keepends=True):
        if current and len(current) + len(line) > size:
            blocks.append(current)
            current = ""
        current += line
    if current.strip():
        blocks.append(current)
    return blocks


def analyze(provider: LLMProvider, transcript: str, meeting_date: date, participants: list[str]) -> dict:
    """Extraction bloc par bloc puis fusion : résumés mis bout à bout, actions concaténées (B.3)."""
    results = [Extraction.model_validate(provider.extract(block, meeting_date, participants))
               for block in split(transcript, settings.llm_chunk_chars)]
    return {
        "summary": {
            "context": "\n\n".join(r.summary.context for r in results if r.summary.context),
            **{key: [item for r in results for item in getattr(r.summary, key)]
               for key in ("topics", "decisions", "open_points")},
        },
        "actions": [a.model_dump() for r in results for a in r.actions],
    }


def get_provider() -> LLMProvider:
    if settings.llm_provider == "anthropic":
        from app.ai.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if settings.llm_provider == "local":
        from app.ai.local_provider import LocalProvider
        return LocalProvider()
    from app.ai.mock_provider import MockProvider
    return MockProvider()
