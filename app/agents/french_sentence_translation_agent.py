import json
import httpx
from pydantic import ValidationError
from app.schemas import SentenceTranslationResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a French language expert. When given a French sentence, "
    "respond ONLY with a JSON object (no markdown) with exactly these keys:\n"
    "- russian_sentence: Russian translation of the sentence\n"
    "- sentence_evaluation: brief note on the grammar and naturalness of the French sentence\n"
    "- is_valid: true if the sentence is grammatically correct French, false otherwise"
)


class FrenchSentenceTranslationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def generate(self, sentence: str) -> SentenceTranslationResult:
        response = await self._client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": sentence},
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
            return SentenceTranslationResult(**data)
        except ValidationError as exc:
            raise ValueError(f"OpenRouter response missing required fields: {exc}") from exc
