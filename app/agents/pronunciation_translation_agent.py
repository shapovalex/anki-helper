import json
import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_LANGUAGE_NAMES: dict[str, str] = {
    "fr-FR": "French",
    "en-US": "English",
}

_SYSTEM_PROMPT = (
    "Translate the given text to Russian. "
    "Respond ONLY with a JSON object (no markdown) with exactly one key: russian_text."
)


class PronunciationTranslationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def translate(self, text: str, language: str) -> str:
        language_name = _LANGUAGE_NAMES.get(language, language)
        user_message = f"Translate the following {language_name} text to Russian:\n{text}"
        response = await self._client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
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
        return data["russian_text"]
