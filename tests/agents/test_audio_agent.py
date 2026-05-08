import os
import base64
import pytest
import httpx
from app.agents.audio_agent import AudioAgent

AZURE_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_REGION = os.getenv("AZURE_TTS_REGION", "westeurope")


class _FakeMP3Transport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request):
        # minimal valid-looking response
        body = b"ID3" + b"\x00" * 100  # fake MP3 bytes
        return httpx.Response(200, content=body, request=request)


async def test_synthesize_returns_base64_string():
    """Unit test — no Azure credential required."""
    client = httpx.AsyncClient(transport=_FakeMP3Transport())
    agent = AudioAgent(client=client, api_key="fake-key", region="westeurope")
    result = await agent.synthesize(text="bonjour", voice="fr-FR-DeniseNeural")

    decoded = base64.b64decode(result)
    assert decoded[:3] == b"ID3"


async def test_synthesize_escapes_xml_special_chars():
    """Verify SSML injection is prevented."""
    captured_body: list[bytes] = []

    class _CapturingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            captured_body.append(await request.aread())
            return httpx.Response(200, content=b"ID3" + b"\x00" * 100, request=request)

    client = httpx.AsyncClient(transport=_CapturingTransport())
    agent = AudioAgent(client=client, api_key="fake-key", region="westeurope")
    await agent.synthesize(text="hello & <world>", voice="fr-FR-DeniseNeural")

    ssml = captured_body[0].decode()
    assert "&amp;" in ssml
    assert "&lt;" in ssml
    assert "&gt;" in ssml


@pytest.fixture
def require_azure_key():
    if not AZURE_KEY:
        pytest.skip("AZURE_TTS_KEY not set")


@pytest.fixture
async def audio_agent(require_azure_key):
    async with httpx.AsyncClient() as client:
        yield AudioAgent(client=client, api_key=AZURE_KEY, region=AZURE_REGION)


async def test_synthesize_returns_non_empty_mp3(audio_agent):
    audio_b64 = await audio_agent.synthesize(text="bonjour", voice="fr-FR-DeniseNeural")

    decoded = base64.b64decode(audio_b64)
    assert len(decoded) > 1000  # real MP3 audio, not an empty response
    assert decoded[:3] == b"ID3" or decoded[:2] == b"\xff\xfb"  # MP3 magic bytes
