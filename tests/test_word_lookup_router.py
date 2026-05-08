import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.routers.word_lookup import get_translation_agent, get_audio_agent, get_anki_client
from app.schemas import TranslationResult


@pytest.fixture
def mock_translation_agent():
    agent = MagicMock()
    agent.generate = AsyncMock(return_value=TranslationResult(
        russian_word="привет",
        example="Bonjour, comment allez-vous?",
        word_evaluation="Valid French interjection used as a greeting.",
        is_valid=True,
    ))
    return agent


@pytest.fixture
def mock_audio_agent():
    agent = MagicMock()
    agent.synthesize = AsyncMock(return_value="bW9jaw==")  # base64("mock")
    return agent


@pytest.fixture
def mock_anki():
    anki = MagicMock()
    anki.invoke = AsyncMock(side_effect=[None, None, 98765])  # storeMedia×2, addNote
    return anki


@pytest.fixture
def client(mock_translation_agent, mock_audio_agent, mock_anki):
    app.dependency_overrides[get_translation_agent] = lambda: mock_translation_agent
    app.dependency_overrides[get_audio_agent] = lambda: mock_audio_agent
    app.dependency_overrides[get_anki_client] = lambda: mock_anki
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_voices_returns_non_empty_list(client):
    response = client.get("/api/word-lookup/voices")
    assert response.status_code == 200
    voices = response.json()["voices"]
    assert len(voices) >= 3
    assert all("id" in v and "name" in v for v in voices)


def test_generate_delegates_to_agent(client, mock_translation_agent):
    response = client.post(
        "/api/word-lookup/generate",
        json={"word": "bonjour", "cefr_level": "B1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["russian_word"] == "привет"
    assert data["is_valid"] is True
    mock_translation_agent.generate.assert_called_once_with(word="bonjour", cefr_level="B1")


def test_audio_delegates_to_agent(client, mock_audio_agent):
    response = client.post(
        "/api/word-lookup/audio",
        json={"text": "bonjour", "voice": "fr-FR-DeniseNeural"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["audio_base64"] == "bW9jaw=="
    assert data["filename"].endswith(".mp3")
    mock_audio_agent.synthesize.assert_called_once_with(
        text="bonjour", voice="fr-FR-DeniseNeural"
    )


def test_add_to_anki_stores_media_and_creates_note(client, mock_anki):
    response = client.post("/api/word-lookup/add-to-anki", json={
        "deck": "French::Vocabulary",
        "note_type": "French-Russian",
        "french_word": "bonjour",
        "russian_word": "привет",
        "example": "Bonjour, comment allez-vous?",
        "french_word_audio_base64": "bW9jaw==",
        "example_audio_base64": "bW9jaw==",
    })
    assert response.status_code == 200
    assert response.json()["note_id"] == 98765
    assert mock_anki.invoke.call_count == 3  # storeMedia×2 + addNote


def test_add_to_anki_uses_slugified_filenames(client, mock_anki):
    client.post("/api/word-lookup/add-to-anki", json={
        "deck": "French",
        "note_type": "French-Russian",
        "french_word": "être",
        "russian_word": "быть",
        "example": "Je vais être là.",
        "french_word_audio_base64": "bW9jaw==",
        "example_audio_base64": "bW9jaw==",
    })
    calls = [str(c) for c in mock_anki.invoke.call_args_list]
    # Slugified "être" → "tre" (accent stripped); filenames must be ASCII
    assert any("tre.mp3" in c for c in calls)
    assert any("tre_example.mp3" in c for c in calls)
