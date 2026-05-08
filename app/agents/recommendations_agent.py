import json

import httpx

from app.schemas import PronunciationRecommendResponse, WordResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a language coach specializing in pronunciation. "
    "Given phoneme-level assessment scores for a spoken phrase, "
    "give 2-3 specific, actionable pronunciation tips targeting the worst-scoring phonemes. "
    "Respond ONLY with a JSON object (no markdown) with key 'tips': a JSON array of strings."
)


class RecommendationsAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def recommend(
        self, reference_text: str, language: str, words: list[WordResult]
    ) -> PronunciationRecommendResponse:
        word_summary = "\n".join(
            f"  {w.word}: accuracy={w.accuracy:.0f}, error_type={w.error_type}, "
            f"phonemes={[{'symbol': p.symbol, 'accuracy': p.accuracy} for p in w.phonemes]}"
            for w in words
        )
        prompt = (
            f'Phrase: "{reference_text}"\n'
            f"Language: {language}\n"
            f"Word assessments:\n{word_summary}"
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
            raise ValueError(f"OpenRouter returned non-JSON: {content!r}") from exc
        tips = data.get("tips", [])
        if not isinstance(tips, list):
            raise ValueError(f"Expected tips to be a list, got: {type(tips)}")
        return PronunciationRecommendResponse(tips=[str(t) for t in tips])
