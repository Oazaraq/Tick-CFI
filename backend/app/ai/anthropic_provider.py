"""Fournisseur Anthropic : API Messages, sortie JSON contrôlée (DFB B.3)."""
from datetime import date

from app.ai import prompts
from app.ai.provider import LLMError, extract_json, post_json
from app.config import settings

API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider:
    name = "anthropic"

    def extract(self, transcript: str, meeting_date: date, participants: list[str]) -> dict:
        if not settings.anthropic_api_key:
            raise LLMError("Clé API Anthropic absente : renseignez ANTHROPIC_API_KEY.")
        body = {
            "model": settings.anthropic_model,
            "max_tokens": 8000,
            "system": prompts.system_prompt(),
            "messages": [{"role": "user", "content": prompts.user_message(transcript, meeting_date, participants)}],
        }
        headers = {"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"}

        def call() -> str:
            data = post_json(API_URL, body, headers, "API Anthropic")
            return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")

        return extract_json(call)
