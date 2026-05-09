import httpx
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.anki_client import AnkiConnectError
from app.main import app
from app.schemas import SentenceTranslationResult, Voice


@pytest.fixture
def mock_translation_agent():
    agent = MagicMock()
    agent.generate = AsyncMock(return_value=SentenceTranslationResult(
        russian_sentence="Привет, как дела?",
        sentence_evaluation="Grammatically correct and natural French greeting.",
        is_valid=True,
    ))
    return agent


@pytest.fixture
def mock_audio_agent():
    agent = MagicMock()
    agent.list_voices = AsyncMock(return_value=[
        Voice(id="fr-FR-DeniseNeural", name="Denise (Female)"),
        Voice(id="fr-FR-HenriNeural", name="Henri (Male)"),
        Voice(id="fr-FR-EloiseNeural", name="Eloise (Female)"),
    ])
    return agent


@pytest.fixture
def mock_anki():
    anki = MagicMock()
    anki.invoke = AsyncMock(side_effect=[None, 98765])  # storeMedia×1, addNote
    return anki


@pytest.fixture
def client(mock_translation_agent, mock_audio_agent, mock_anki):
    from app.routers.sentence_lookup import get_translation_agent, get_audio_agent, get_anki_client
    app.dependency_overrides[get_translation_agent] = lambda: mock_translation_agent
    app.dependency_overrides[get_audio_agent] = lambda: mock_audio_agent
    app.dependency_overrides[get_anki_client] = lambda: mock_anki
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_voices_returns_list_from_agent(client, mock_audio_agent):
    response = client.get("/api/sentence-lookup/voices")
    assert response.status_code == 200
    voices = response.json()["voices"]
    assert len(voices) == 3
    assert all("id" in v and "name" in v for v in voices)
    mock_audio_agent.list_voices.assert_called_once()


def test_generate_delegates_to_agent(client, mock_translation_agent):
    response = client.post(
        "/api/sentence-lookup/generate",
        json={"sentence": "Bonjour, comment allez-vous?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["russian_sentence"] == "Привет, как дела?"
    assert data["is_valid"] is True
    mock_translation_agent.generate.assert_called_once_with(sentence="Bonjour, comment allez-vous?")


def test_add_to_anki_stores_one_media_file_and_creates_note(client, mock_anki):
    response = client.post("/api/sentence-lookup/add-to-anki", json={
        "deck": "French::Sentences",
        "note_type": "French-Russian-Sentence",
        "french_sentence": "Bonjour, comment allez-vous?",
        "russian_sentence": "Привет, как дела?",
        "audio_base64": "bW9jaw==",
    })
    assert response.status_code == 200
    assert response.json()["note_id"] == 98765
    assert mock_anki.invoke.call_count == 2  # storeMedia×1 + addNote


def test_add_to_anki_uses_slugified_filename(client, mock_anki):
    client.post("/api/sentence-lookup/add-to-anki", json={
        "deck": "French",
        "note_type": "French-Russian-Sentence",
        "french_sentence": "être ou ne pas être",
        "russian_sentence": "быть или не быть",
        "audio_base64": "bW9jaw==",
    })
    store_call = mock_anki.invoke.call_args_list[0]
    assert store_call.kwargs["filename"] == "etre_ou_ne_pas_etre.mp3"


def test_generate_returns_503_when_key_not_configured():
    from app.routers.sentence_lookup import get_translation_agent

    def raise_503():
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured.")

    app.dependency_overrides[get_translation_agent] = raise_503
    try:
        with TestClient(app) as c:
            response = c.post("/api/sentence-lookup/generate", json={"sentence": "Bonjour"})
        assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_translation_agent, None)


def test_generate_returns_502_on_unexpected_error():
    from app.routers.sentence_lookup import get_translation_agent

    mock_agent = MagicMock()
    mock_agent.generate = AsyncMock(side_effect=RuntimeError("unexpected"))

    app.dependency_overrides[get_translation_agent] = lambda: mock_agent
    try:
        with TestClient(app) as c:
            response = c.post("/api/sentence-lookup/generate", json={"sentence": "Bonjour"})
        assert response.status_code == 502
    finally:
        app.dependency_overrides.pop(get_translation_agent, None)


def test_add_to_anki_returns_400_for_missing_note_type(client, mock_anki):
    mock_anki.invoke.side_effect = AnkiConnectError("deck or model not found")
    response = client.post("/api/sentence-lookup/add-to-anki", json={
        "deck": "French",
        "note_type": "Wrong-Type",
        "french_sentence": "Bonjour!",
        "russian_sentence": "Привет!",
        "audio_base64": "bW9jaw==",
    })
    assert response.status_code == 400


def test_add_to_anki_returns_503_when_anki_not_running(client, mock_anki):
    mock_anki.invoke.side_effect = httpx.ConnectError("Connection refused")
    response = client.post("/api/sentence-lookup/add-to-anki", json={
        "deck": "French",
        "note_type": "French-Russian-Sentence",
        "french_sentence": "Bonjour!",
        "russian_sentence": "Привет!",
        "audio_base64": "bW9jaw==",
    })
    assert response.status_code == 503
