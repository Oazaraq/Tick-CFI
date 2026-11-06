"""IA locale (Ollama, vLLM…) : API compatible OpenAI, les données ne quittent pas l'infrastructure."""
from datetime import date

from app.ai import prompts
from app.ai.provider import LLMError, extract_json, post_json
from app.config import settings


class LocalProvider:
    name = "local"

    def extract(self, transcript: str, meeting_date: date, participants: list[str]) -> dict:
        url = settings.local_llm_url.rstrip("/") + "/chat/completions"
        body = {
            "model": settings.local_llm_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompts.system_prompt()},
                {"role": "user", "content": prompts.user_message(transcript, meeting_date, participants)},
            ],
        }

        def call() -> str:
            data = post_json(url, body, {}, "IA locale")
            try:
                return data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMError("IA locale : réponse inattendue.") from exc

        return extract_json(call)
