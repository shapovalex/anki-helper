import os
import base64
import pytest
import httpx
from app.agents.audio_agent import AudioAgent

AZURE_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_REGION = os.getenv("AZURE_TTS_REGION", "westeurope")


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
