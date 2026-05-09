import base64
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

import httpx

from app.anki_client import AnkiConnectError
from app.main import app
from app.routers.pronunciation import (
    get_anki_client,
    get_pronunciation_agent,
    get_recommendations_agent,
)
from app.schemas import (
    OverallScore,
    PhonemeResult,
    PronunciationAssessResponse,
    PronunciationRecommendResponse,
    WordResult,
)

_MOCK_ASSESSMENT = PronunciationAssessResponse(
    overall=OverallScore(accuracy=85.0, fluency=90.0, completeness=95.0, pron_score=88.0),
    recognized_text="Bonjour.",
    words=[
        WordResult(
            word="bonjour",
            accuracy=85.0,
            error_type="None",
            phonemes=[
                PhonemeResult(symbol="b", accuracy=95.0),
                PhonemeResult(symbol="ɔ̃", accuracy=72.0),
            ],
        )
    ],
)


@pytest.fixture
def mock_anki():
    return MagicMock()


@pytest.fixture
def mock_pronunciation_agent():
    agent = MagicMock()
    agent.assess = AsyncMock(return_value=_MOCK_ASSESSMENT)
    return agent


@pytest.fixture
def mock_recommendations_agent():
    agent = MagicMock()
    agent.recommend = AsyncMock(
        return_value=PronunciationRecommendResponse(tips=["Tip 1", "Tip 2"])
    )
    return agent


@pytest.fixture
def client(mock_anki, mock_pronunciation_agent, mock_recommendations_agent):
    app.dependency_overrides[get_anki_client] = lambda: mock_anki
    app.dependency_overrides[get_pronunciation_agent] = lambda: mock_pronunciation_agent
    app.dependency_overrides[get_recommendations_agent] = lambda: mock_recommendations_agent
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_fields_returns_field_names(client, mock_anki):
    mock_anki.invoke = AsyncMock(side_effect=[
        [1234],  # findCards
        [{"fields": {
            "french_word": {"value": "bonjour", "order": 0},
            "example": {"value": "...", "order": 1},
        }}],  # cardsInfo
    ])
    response = client.get("/api/pronunciation/fields?deck=French")
    assert response.status_code == 200
    assert response.json()["fields"] == ["french_word", "example"]


def test_fields_returns_404_when_no_cards(client, mock_anki):
    mock_anki.invoke = AsyncMock(return_value=[])
    response = client.get("/api/pronunciation/fields?deck=EmptyDeck")
    assert response.status_code == 404


def test_card_returns_card_data_with_audio(client, mock_anki):
    mock_anki.invoke = AsyncMock(side_effect=[
        [5678],  # findCards (due cards)
        [{"fields": {
            "french_word": {"value": "bonjour", "order": 0},
            "french_word_audio": {"value": "[sound:bonjour.mp3]", "order": 1},
        }}],  # cardsInfo
        "AAAA==",  # retrieveMediaFile
    ])
    response = client.get(
        "/api/pronunciation/card?deck=French&field=french_word&audio_field=french_word_audio"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["card_id"] == 5678
    assert data["text"] == "bonjour"
    assert data["audio_base64"] == "AAAA=="


def test_card_returns_null_audio_when_no_sound_tag(client, mock_anki):
    mock_anki.invoke = AsyncMock(side_effect=[
        [1234],
        [{"fields": {
            "french_word": {"value": "bonjour", "order": 0},
            "french_word_audio": {"value": "", "order": 1},
        }}],
    ])
    response = client.get(
        "/api/pronunciation/card?deck=French&field=french_word&audio_field=french_word_audio"
    )
    assert response.status_code == 200
    assert response.json()["audio_base64"] is None


def test_card_returns_404_when_no_due_cards(client, mock_anki):
    mock_anki.invoke = AsyncMock(return_value=[])
    response = client.get(
        "/api/pronunciation/card?deck=French&field=french_word&audio_field=french_word_audio"
    )
    assert response.status_code == 404


def test_assess_delegates_to_agent(client, mock_pronunciation_agent):
    audio_b64 = base64.b64encode(b"fake audio").decode()
    response = client.post("/api/pronunciation/assess", json={
        "audio_base64": audio_b64,
        "reference_text": "bonjour",
        "language": "fr-FR",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["overall"]["pron_score"] == 88.0
    assert len(data["words"]) == 1
    mock_pronunciation_agent.assess.assert_called_once()


def test_assess_returns_503_when_azure_not_configured():
    from fastapi import HTTPException

    def raise_503():
        raise HTTPException(status_code=503, detail="Azure key not configured.")

    app.dependency_overrides[get_pronunciation_agent] = raise_503
    try:
        with TestClient(app) as c:
            response = c.post("/api/pronunciation/assess", json={
                "audio_base64": "AAAA",
                "reference_text": "test",
                "language": "fr-FR",
            })
        assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_pronunciation_agent, None)


def test_recommendations_delegates_to_agent(client, mock_recommendations_agent):
    response = client.post("/api/pronunciation/recommendations", json={
        "reference_text": "bonjour",
        "language": "fr-FR",
        "words": [{
            "word": "bonjour",
            "accuracy": 72.0,
            "error_type": "Mispronunciation",
            "phonemes": [
                {"symbol": "b", "accuracy": 95.0},
                {"symbol": "ɔ̃", "accuracy": 42.0},
            ],
        }],
    })
    assert response.status_code == 200
    assert response.json()["tips"] == ["Tip 1", "Tip 2"]
    mock_recommendations_agent.recommend.assert_called_once()


def test_answer_calls_answerCards(client, mock_anki):
    mock_anki.invoke = AsyncMock(return_value=[True])
    response = client.post("/api/pronunciation/answer", json={"card_id": 1234, "ease": 3})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_anki.invoke.assert_called_once_with(
        "answerCards", answers=[{"cardId": 1234, "ease": 3}]
    )


def test_answer_returns_503_when_anki_not_running(client, mock_anki):
    mock_anki.invoke = AsyncMock(side_effect=httpx.ConnectError("refused"))
    response = client.post("/api/pronunciation/answer", json={"card_id": 1234, "ease": 1})
    assert response.status_code == 503
