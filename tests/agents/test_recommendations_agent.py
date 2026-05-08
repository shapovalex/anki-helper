import json
import pytest
import httpx

from app.agents.recommendations_agent import RecommendationsAgent
from app.schemas import PhonemeResult, WordResult

SAMPLE_WORDS = [
    WordResult(
        word="bonjour",
        accuracy=42.0,
        error_type="Mispronunciation",
        phonemes=[
            PhonemeResult(symbol="b", accuracy=90.0),
            PhonemeResult(symbol="ɔ̃", accuracy=20.0),
        ],
    )
]


class _FakeOpenRouterTransport(httpx.AsyncBaseTransport):
    def __init__(self, tips: list[str]):
        self._tips = tips

    async def handle_async_request(self, request):
        body = json.dumps({
            "choices": [{"message": {"content": json.dumps({"tips": self._tips})}}]
        }).encode()
        return httpx.Response(
            200,
            content=body,
            request=request,
            headers={"content-type": "application/json"},
        )


class _BadJsonTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request):
        body = json.dumps({
            "choices": [{"message": {"content": "not valid json"}}]
        }).encode()
        return httpx.Response(
            200,
            content=body,
            request=request,
            headers={"content-type": "application/json"},
        )


async def test_recommend_returns_tips():
    transport = _FakeOpenRouterTransport(["Tip one", "Tip two"])
    client = httpx.AsyncClient(transport=transport)
    agent = RecommendationsAgent(client=client, api_key="fake-key", model="test-model")

    result = await agent.recommend(
        reference_text="bonjour", language="fr-FR", words=SAMPLE_WORDS
    )

    assert result.tips == ["Tip one", "Tip two"]


async def test_recommend_raises_on_invalid_json():
    transport = _BadJsonTransport()
    client = httpx.AsyncClient(transport=transport)
    agent = RecommendationsAgent(client=client, api_key="fake-key", model="test-model")

    with pytest.raises(ValueError, match="non-JSON"):
        await agent.recommend(
            reference_text="bonjour", language="fr-FR", words=SAMPLE_WORDS
        )
