import json
import pytest
import httpx

from app.agents.pronunciation_translation_agent import PronunciationTranslationAgent


class _FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, russian_text: str):
        self._russian_text = russian_text

    async def handle_async_request(self, request):
        body = json.dumps({
            "choices": [{"message": {"content": json.dumps({"russian_text": self._russian_text})}}]
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


async def test_translate_returns_russian_text():
    transport = _FakeTransport("Привет")
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")

    result = await agent.translate(text="Bonjour", language="fr-FR")

    assert result == "Привет"


async def test_translate_includes_language_name_in_request():
    captured = {}

    class _CapturingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            captured["body"] = json.loads(request.content)
            body = json.dumps({
                "choices": [{"message": {"content": json.dumps({"russian_text": "Привет"})}}]
            }).encode()
            return httpx.Response(
                200,
                content=body,
                request=request,
                headers={"content-type": "application/json"},
            )

    client = httpx.AsyncClient(transport=_CapturingTransport())
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")
    await agent.translate(text="Bonjour", language="fr-FR")

    user_content = captured["body"]["messages"][-1]["content"]
    assert "French" in user_content
    assert "Bonjour" in user_content


async def test_translate_english_includes_english_in_request():
    captured = {}

    class _CapturingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            captured["body"] = json.loads(request.content)
            body = json.dumps({
                "choices": [{"message": {"content": json.dumps({"russian_text": "Привет"})}}]
            }).encode()
            return httpx.Response(
                200,
                content=body,
                request=request,
                headers={"content-type": "application/json"},
            )

    client = httpx.AsyncClient(transport=_CapturingTransport())
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")
    await agent.translate(text="Hello", language="en-US")

    user_content = captured["body"]["messages"][-1]["content"]
    assert "English" in user_content


async def test_translate_raises_on_invalid_json():
    transport = _BadJsonTransport()
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")

    with pytest.raises(ValueError, match="non-JSON"):
        await agent.translate(text="Bonjour", language="fr-FR")
