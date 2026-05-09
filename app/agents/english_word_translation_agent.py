import json
import httpx
from pydantic import ValidationError
from app.schemas import TranslationResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are an English language expert. When given an English word and a CEFR level, "
    "respond ONLY with a JSON object (no markdown) with exactly these keys:\n"
    "- russian_word: Russian translation of the word\n"
    "- example: a natural English sentence using the word, appropriate for the CEFR level\n"
    "- alternative_examples: a JSON array of exactly 5 additional natural English sentences "
    "using the word, each appropriate for the CEFR level and distinct from 'example'\n"
    "- word_evaluation: brief note on whether the word is correctly spelled and valid English\n"
    "- is_valid: true if the word is a real, correctly spelled English word, false otherwise"
)


class EnglishWordTranslationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def generate(self, word: str, cefr_level: str) -> TranslationResult:
        prompt = (
            f"English word: {word}\n"
            f"CEFR level for the example sentence: {cefr_level}"
        )
        response = await self._client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenRouter returned non-JSON content: {content!r}") from exc
        try:
            return TranslationResult(**data)
        except ValidationError as exc:
            raise ValueError(f"OpenRouter response missing required fields: {exc}") from exc
