# Pronunciation Practice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/pronunciation` page where the user selects a deck, text field, audio field, and language, then practices pronunciation card-by-card using Azure Speech assessment with phoneme-level feedback and optional LLM tips.

**Architecture:** Server-side proxy — browser records WebM/Opus audio via press-and-hold `MediaRecorder`, sends it base64-encoded to FastAPI, which calls the Azure Speech REST API with `PronunciationAssessment` config (phoneme granularity) and returns structured scores. Reference audio comes from the card's audio field (parsed from `[sound:...]` tag, retrieved via AnkiConnect) or falls back to the existing TTS endpoint. LLM tips are generated on demand via OpenRouter.

**Tech Stack:** FastAPI, httpx, Pydantic, AnkiConnect, Azure Speech REST API, OpenRouter, vanilla JS with `MediaRecorder`.

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `app/agents/pronunciation_agent.py` | Azure Speech REST call + response parsing |
| Create | `app/agents/recommendations_agent.py` | OpenRouter LLM tips generation |
| Create | `app/routers/pronunciation.py` | 5 API endpoints |
| Create | `static/pronunciation.html` | Frontend page |
| Create | `tests/agents/test_pronunciation_agent.py` | Agent unit tests |
| Create | `tests/agents/test_recommendations_agent.py` | Agent unit tests |
| Create | `tests/test_pronunciation_router.py` | Router integration tests |
| Modify | `app/schemas.py` | Add 10 pronunciation schemas |
| Modify | `app/main.py` | Register router + page route |
| Modify | `static/components/menu.html` | Add Pronunciation nav link |
| Modify | `static/css/theme.css` | Add `.btn-danger` class |

---

## Task 1: Add pronunciation schemas to `app/schemas.py`

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: Add schemas**

Append to `app/schemas.py` (after the existing `SettingsUpdateRequest` class):

```python
class PronunciationFieldsResponse(BaseModel):
    fields: list[str]


class PronunciationCardResponse(BaseModel):
    card_id: int
    text: str
    audio_base64: str | None


class PronunciationAssessRequest(BaseModel):
    audio_base64: str
    reference_text: str
    language: str


class PhonemeResult(BaseModel):
    symbol: str
    accuracy: float


class WordResult(BaseModel):
    word: str
    accuracy: float
    error_type: str
    phonemes: list[PhonemeResult]


class OverallScore(BaseModel):
    accuracy: float
    fluency: float
    completeness: float
    pron_score: float


class PronunciationAssessResponse(BaseModel):
    overall: OverallScore
    recognized_text: str
    words: list[WordResult]


class PronunciationRecommendRequest(BaseModel):
    reference_text: str
    language: str
    words: list[WordResult]


class PronunciationRecommendResponse(BaseModel):
    tips: list[str]


class PronunciationAnswerRequest(BaseModel):
    card_id: int
    ease: int = Field(ge=1, le=4)


class PronunciationAnswerResponse(BaseModel):
    ok: bool
```

- [ ] **Step 2: Verify schemas import cleanly**

```bash
uv run python -c "from app.schemas import PronunciationAssessResponse, WordResult, PhonemeResult, OverallScore, PronunciationAnswerRequest; print('ok')"
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add pronunciation practice schemas"
```

---

## Task 2: Create PronunciationAgent (Azure Speech)

**Files:**
- Create: `app/agents/pronunciation_agent.py`
- Create: `tests/agents/test_pronunciation_agent.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/agents/test_pronunciation_agent.py`:

```python
import base64
import json
import pytest
import httpx

from app.agents.pronunciation_agent import PronunciationAgent

SAMPLE_AZURE_RESPONSE = {
    "RecognitionStatus": "Success",
    "NBest": [{
        "Display": "Bonjour.",
        "PronunciationAssessment": {
            "AccuracyScore": 85.0,
            "FluencyScore": 90.0,
            "CompletenessScore": 95.0,
            "PronScore": 88.0,
        },
        "Words": [{
            "Word": "bonjour",
            "PronunciationAssessment": {
                "AccuracyScore": 85.0,
                "ErrorType": "None",
            },
            "Phonemes": [
                {"Phoneme": "b", "PronunciationAssessment": {"AccuracyScore": 95.0}},
                {"Phoneme": "ɔ̃", "PronunciationAssessment": {"AccuracyScore": 72.0}},
            ],
        }],
    }],
}


class _FakeAzureTransport(httpx.AsyncBaseTransport):
    def __init__(self, response_data: dict, status_code: int = 200):
        self._response_data = response_data
        self._status_code = status_code
        self.last_request = None

    async def handle_async_request(self, request):
        self.last_request = request
        body = json.dumps(self._response_data).encode()
        return httpx.Response(
            self._status_code,
            content=body,
            request=request,
            headers={"content-type": "application/json"},
        )


async def test_assess_parses_overall_scores():
    transport = _FakeAzureTransport(SAMPLE_AZURE_RESPONSE)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="fake-key", region="eastus")

    result = await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")

    assert result.overall.pron_score == 88.0
    assert result.overall.accuracy == 85.0
    assert result.overall.fluency == 90.0
    assert result.overall.completeness == 95.0


async def test_assess_parses_words_and_phonemes():
    transport = _FakeAzureTransport(SAMPLE_AZURE_RESPONSE)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="fake-key", region="eastus")

    result = await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")

    assert len(result.words) == 1
    word = result.words[0]
    assert word.word == "bonjour"
    assert word.accuracy == 85.0
    assert word.error_type == "None"
    assert len(word.phonemes) == 2
    assert word.phonemes[0].symbol == "b"
    assert word.phonemes[0].accuracy == 95.0
    assert word.phonemes[1].symbol == "ɔ̃"
    assert word.phonemes[1].accuracy == 72.0


async def test_assess_sends_correct_pronunciation_assessment_header():
    transport = _FakeAzureTransport(SAMPLE_AZURE_RESPONSE)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="fake-key", region="eastus")

    await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")

    headers = dict(transport.last_request.headers)
    assert "pronunciation-assessment" in headers
    config = json.loads(base64.b64decode(headers["pronunciation-assessment"]))
    assert config["ReferenceText"] == "bonjour"
    assert config["Granularity"] == "Phoneme"
    assert config["GradingSystem"] == "HundredMark"
    assert config["EnableMiscue"] is True


async def test_assess_raises_value_error_on_http_error():
    transport = _FakeAzureTransport({}, status_code=401)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="bad-key", region="eastus")

    with pytest.raises(ValueError, match="Azure Speech request failed"):
        await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_pronunciation_agent.py -v
```

Expected: `ModuleNotFoundError` — `pronunciation_agent` does not exist yet.

- [ ] **Step 3: Implement PronunciationAgent**

Create `app/agents/pronunciation_agent.py`:

```python
import base64
import json

import httpx

from app.schemas import OverallScore, PhonemeResult, PronunciationAssessResponse, WordResult


class PronunciationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, region: str) -> None:
        self._client = client
        self._api_key = api_key
        self._region = region

    async def assess(
        self, audio_bytes: bytes, reference_text: str, language: str
    ) -> PronunciationAssessResponse:
        config = json.dumps({
            "ReferenceText": reference_text,
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "EnableMiscue": True,
        })
        config_b64 = base64.b64encode(config.encode()).decode()
        url = (
            f"https://{self._region}.stt.speech.microsoft.com"
            f"/speech/recognition/conversation/cognitiveservices/v1"
            f"?language={language}&format=detailed"
        )
        response = await self._client.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Pronunciation-Assessment": config_b64,
                "Content-Type": "audio/webm;codecs=opus",
            },
            content=audio_bytes,
            timeout=30.0,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"Azure Speech request failed ({exc.response.status_code}): "
                f"{exc.response.text[:200]}"
            ) from exc
        return self._parse(response.json())

    def _parse(self, data: dict) -> PronunciationAssessResponse:
        nbest = data.get("NBest", [{}])[0]
        pa = nbest.get("PronunciationAssessment", {})
        overall = OverallScore(
            accuracy=pa.get("AccuracyScore", 0.0),
            fluency=pa.get("FluencyScore", 0.0),
            completeness=pa.get("CompletenessScore", 0.0),
            pron_score=pa.get("PronScore", 0.0),
        )
        words = []
        for w in nbest.get("Words", []):
            wpa = w.get("PronunciationAssessment", {})
            phonemes = [
                PhonemeResult(
                    symbol=p["Phoneme"],
                    accuracy=p.get("PronunciationAssessment", {}).get("AccuracyScore", 0.0),
                )
                for p in w.get("Phonemes", [])
            ]
            words.append(WordResult(
                word=w["Word"],
                accuracy=wpa.get("AccuracyScore", 0.0),
                error_type=wpa.get("ErrorType", "None"),
                phonemes=phonemes,
            ))
        return PronunciationAssessResponse(
            overall=overall,
            recognized_text=nbest.get("Display", ""),
            words=words,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_pronunciation_agent.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/pronunciation_agent.py tests/agents/test_pronunciation_agent.py
git commit -m "feat: add PronunciationAgent for Azure Speech assessment"
```

---

## Task 3: Create RecommendationsAgent (LLM tips)

**Files:**
- Create: `app/agents/recommendations_agent.py`
- Create: `tests/agents/test_recommendations_agent.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/agents/test_recommendations_agent.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_recommendations_agent.py -v
```

Expected: `ModuleNotFoundError` — `recommendations_agent` does not exist yet.

- [ ] **Step 3: Implement RecommendationsAgent**

Create `app/agents/recommendations_agent.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_recommendations_agent.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/recommendations_agent.py tests/agents/test_recommendations_agent.py
git commit -m "feat: add RecommendationsAgent for LLM pronunciation tips"
```

---

## Task 4: Create pronunciation router with tests

**Files:**
- Create: `app/routers/pronunciation.py`
- Create: `tests/test_pronunciation_router.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pronunciation_router.py`:

```python
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


def test_answer_calls_answerCard(client, mock_anki):
    mock_anki.invoke = AsyncMock(return_value=True)
    response = client.post("/api/pronunciation/answer", json={"card_id": 1234, "ease": 3})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_anki.invoke.assert_called_once_with("answerCard", id=1234, ease=3)


def test_answer_returns_503_when_anki_not_running(client, mock_anki):
    mock_anki.invoke = AsyncMock(side_effect=httpx.ConnectError("refused"))
    response = client.post("/api/pronunciation/answer", json={"card_id": 1234, "ease": 1})
    assert response.status_code == 503
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_pronunciation_router.py -v
```

Expected: `ImportError` — `app.routers.pronunciation` does not exist yet.

- [ ] **Step 3: Implement the pronunciation router**

Create `app/routers/pronunciation.py`:

```python
import base64
import random
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.pronunciation_agent import PronunciationAgent
from app.agents.recommendations_agent import RecommendationsAgent
from app.anki_client import AnkiClient, AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    PronunciationAnswerRequest,
    PronunciationAnswerResponse,
    PronunciationAssessRequest,
    PronunciationAssessResponse,
    PronunciationCardResponse,
    PronunciationFieldsResponse,
    PronunciationRecommendRequest,
    PronunciationRecommendResponse,
)

router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])

_SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")


def get_anki_client(request: Request) -> AnkiClient:
    return request.app.state.anki_client


def get_pronunciation_agent(request: Request) -> PronunciationAgent:
    config: ConfigManager = request.app.state.config
    if not config.azure_key_set:
        raise HTTPException(
            status_code=503,
            detail="Azure key not configured. Go to Settings.",
        )
    return PronunciationAgent(
        client=request.app.state.http_client,
        api_key=config.azure_tts_key,
        region=config.azure_tts_region,
    )


def get_recommendations_agent(request: Request) -> RecommendationsAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return RecommendationsAgent(
        client=request.app.state.http_client,
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
    )


@router.get("/fields", response_model=PronunciationFieldsResponse)
async def get_fields(
    deck: str,
    anki_client: AnkiClient = Depends(get_anki_client),
) -> PronunciationFieldsResponse:
    try:
        card_ids = await anki_client.invoke("findCards", query=f'deck:"{deck}"')
        if not card_ids:
            raise HTTPException(status_code=404, detail="No cards found in deck.")
        cards_info = await anki_client.invoke("cardsInfo", cards=[card_ids[0]])
        fields = list(cards_info[0]["fields"].keys())
        return PronunciationFieldsResponse(fields=fields)
    except AnkiConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )


@router.get("/card", response_model=PronunciationCardResponse)
async def get_card(
    deck: str,
    field: str,
    audio_field: str,
    anki_client: AnkiClient = Depends(get_anki_client),
) -> PronunciationCardResponse:
    try:
        card_ids = await anki_client.invoke(
            "findCards", query=f'deck:"{deck}" is:due'
        )
        if not card_ids:
            raise HTTPException(status_code=404, detail="No due cards in deck.")
        card_id = random.choice(card_ids)
        cards_info = await anki_client.invoke("cardsInfo", cards=[card_id])
        card = cards_info[0]
        text = card["fields"].get(field, {}).get("value", "")
        audio_field_value = card["fields"].get(audio_field, {}).get("value", "")
        audio_base64 = None
        m = _SOUND_RE.search(audio_field_value)
        if m:
            filename = m.group(1)
            audio_base64 = await anki_client.invoke("retrieveMediaFile", filename=filename)
        return PronunciationCardResponse(
            card_id=card_id, text=text, audio_base64=audio_base64
        )
    except AnkiConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )


@router.post("/assess", response_model=PronunciationAssessResponse)
async def assess(
    body: PronunciationAssessRequest,
    agent: PronunciationAgent = Depends(get_pronunciation_agent),
) -> PronunciationAssessResponse:
    audio_bytes = base64.b64decode(body.audio_base64)
    try:
        return await agent.assess(
            audio_bytes=audio_bytes,
            reference_text=body.reference_text,
            language=body.language,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/recommendations", response_model=PronunciationRecommendResponse)
async def recommendations(
    body: PronunciationRecommendRequest,
    agent: RecommendationsAgent = Depends(get_recommendations_agent),
) -> PronunciationRecommendResponse:
    try:
        return await agent.recommend(
            reference_text=body.reference_text,
            language=body.language,
            words=body.words,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/answer", response_model=PronunciationAnswerResponse)
async def answer(
    body: PronunciationAnswerRequest,
    anki_client: AnkiClient = Depends(get_anki_client),
) -> PronunciationAnswerResponse:
    try:
        await anki_client.invoke("answerCard", id=body.card_id, ease=body.ease)
        return PronunciationAnswerResponse(ok=True)
    except AnkiConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_pronunciation_router.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/pronunciation.py tests/test_pronunciation_router.py
git commit -m "feat: add pronunciation router with 5 endpoints"
```

---

## Task 5: Wire up main.py, menu, and theme

**Files:**
- Modify: `app/main.py`
- Modify: `static/components/menu.html`
- Modify: `static/css/theme.css`

- [ ] **Step 1: Register the router and page route in `app/main.py`**

Add the import and router registration. The final file should look like:

```python
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.anki_client import AnkiClient
from app.config import ConfigManager
from app.routers import decks as decks_router
from app.routers import settings as settings_router
from app.routers import word_lookup as word_lookup_router
from app.routers import pronunciation as pronunciation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        app.state.config = ConfigManager()
        app.state.http_client = http_client
        app.state.anki_client = AnkiClient(http_client)
        yield


app = FastAPI(title="Anki Helper", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(decks_router.router)
app.include_router(settings_router.router)
app.include_router(word_lookup_router.router)
app.include_router(pronunciation_router.router)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/word-lookup")
async def word_lookup() -> FileResponse:
    return FileResponse("static/word-lookup.html")


@app.get("/settings")
async def settings() -> FileResponse:
    return FileResponse("static/settings.html")


@app.get("/help")
async def help_page() -> FileResponse:
    return FileResponse("static/help.html")


@app.get("/pronunciation")
async def pronunciation() -> FileResponse:
    return FileResponse("static/pronunciation.html")
```

- [ ] **Step 2: Add Pronunciation link to menu**

Replace the contents of `static/components/menu.html`:

```html
<nav>
    <a href="/" class="nav-brand">Anki Helper</a>
    <div class="nav-links">
        <a href="/">Home</a>
        <a href="/word-lookup">Word Lookup</a>
        <a href="/pronunciation">Pronunciation</a>
        <a href="/settings">Settings</a>
        <a href="/help">Help</a>
    </div>
</nav>
```

- [ ] **Step 3: Add `.btn-danger` to theme CSS**

Append to `static/css/theme.css` (after the `.btn-full` rule):

```css
.btn-danger {
  background: var(--error);
  color: white;
  font-weight: 600;
}
.btn-danger:hover:not(:disabled) { background: #bf5550; }
```

- [ ] **Step 4: Run full test suite to verify nothing is broken**

```bash
uv run pytest -v
```

Expected: all existing tests plus the new tests PASS (no regressions).

- [ ] **Step 5: Commit**

```bash
git add app/main.py static/components/menu.html static/css/theme.css
git commit -m "feat: register pronunciation router, add menu link and btn-danger style"
```

---

## Task 6: Build the pronunciation frontend

**Files:**
- Create: `static/pronunciation.html`

- [ ] **Step 1: Create `static/pronunciation.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pronunciation Practice — Anki Helper</title>
    <link rel="stylesheet" href="/static/css/theme.css">
    <style>
        .pronounce-text {
            font-family: var(--font-display);
            font-size: 2.5rem;
            font-weight: 700;
            text-align: center;
            color: var(--text);
            margin: 1.5rem 0;
            line-height: 1.2;
        }
        .score-badge {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: var(--radius);
            font-size: 0.82rem;
            font-weight: 600;
        }
        .score-green  { background: rgba(74, 140, 98, 0.15); border: 1px solid rgba(74, 140, 98, 0.35); color: var(--success-text); }
        .score-yellow { background: rgba(184, 140, 48, 0.15); border: 1px solid rgba(184, 140, 48, 0.35); color: var(--warn-text); }
        .score-red    { background: rgba(168, 74, 68, 0.15); border: 1px solid rgba(168, 74, 68, 0.35); color: var(--error-text); }
        .sub-scores {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
        }
        .word-chip {
            display: inline-block;
            padding: 0.3rem 0.7rem;
            border-radius: var(--radius);
            font-size: 0.9rem;
            cursor: pointer;
            border: 1px solid transparent;
            margin-bottom: 0.4rem;
            transition: opacity 0.12s;
        }
        .word-chip:hover { opacity: 0.8; }
        .phoneme-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
            padding: 0.4rem 0 0.5rem 0.5rem;
        }
        .phoneme-chip {
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-family: var(--font-mono);
            border: 1px solid transparent;
        }
        .rating-row {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .rating-row button { flex: 1; }
        #record-btn {
            position: relative;
            user-select: none;
        }
        #record-btn.recording {
            background: var(--error);
            color: white;
        }
        .record-status {
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
            min-height: 1.4rem;
            margin: 0.4rem 0;
        }
    </style>
</head>
<body>
    <div id="menu-container"></div>
    <main class="page page-sm">

        <!-- ── Phase 1: Setup ───────────────────────────────────── -->
        <div id="setup-phase">
            <div class="page-header">
                <h1 class="page-title">Pronunciation</h1>
                <p class="page-subtitle">Practice speaking Anki cards aloud with Azure Speech feedback.</p>
            </div>

            <div id="anki-banner" class="banner banner-error">
                Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.
            </div>
            <div id="azure-banner" class="banner banner-error">
                Azure key not configured. <a href="/settings">Go to Settings →</a>
            </div>

            <div class="field">
                <label>Deck</label>
                <select id="deck-select"></select>
            </div>
            <div class="field">
                <label>Text Field</label>
                <select id="text-field-select" disabled></select>
            </div>
            <div class="field">
                <label>Audio Field</label>
                <select id="audio-field-select" disabled></select>
            </div>
            <div class="field">
                <label>Language</label>
                <select id="language-select">
                    <option value="fr-FR">French</option>
                    <option value="en-US">English</option>
                </select>
            </div>
            <button id="start-btn" class="btn-primary btn-full" disabled>Start Practicing</button>
        </div>

        <!-- ── Phase 2: Card practice ───────────────────────────── -->
        <div id="card-phase" style="display:none;">

            <div id="no-cards-msg" style="display:none; text-align:center; padding: 3rem 0;">
                <p style="color: var(--text-muted); margin-bottom: 1rem;">No due cards in this deck.</p>
                <button class="btn-secondary" onclick="showSetup()">← Back to Setup</button>
            </div>

            <div id="card-content">
                <div class="pronounce-text" id="pronounce-text"></div>

                <div class="field">
                    <label>Reference Audio</label>
                    <audio id="ref-audio" controls style="width:100%; color-scheme:dark;"></audio>
                </div>

                <button id="record-btn" class="btn-primary btn-full">🎤 Hold to Record</button>
                <p class="record-status" id="record-status"></p>

                <!-- Results -->
                <div id="results-section" style="display:none;">

                    <div id="overall-badge" class="eval-badge eval-warning" style="margin-bottom:0.5rem;"></div>
                    <div class="sub-scores" id="sub-scores"></div>

                    <div id="heard-row" class="field" style="display:none;">
                        <label>Azure heard</label>
                        <p id="heard-text" style="font-style:italic; color:var(--text-muted); font-size:0.9rem;"></p>
                    </div>

                    <div class="field">
                        <label>Words</label>
                        <div id="words-container"></div>
                    </div>

                    <div class="field" id="recs-section">
                        <button id="get-recs-btn" class="btn-secondary" onclick="getRecommendations()">Get Recommendations</button>
                        <div id="recs-error" class="inline-error"></div>
                        <div id="recs-content" style="display:none; margin-top:0.75rem;"></div>
                    </div>

                    <button class="btn-secondary btn-full" style="margin-bottom:1rem;" onclick="resetForRecording()">🎤 Record Again</button>

                    <div class="divider"></div>

                    <div class="rating-row">
                        <button class="btn-danger"   onclick="answerCard(1)">Again</button>
                        <button class="btn-secondary" onclick="answerCard(2)">Hard</button>
                        <button class="btn-primary"  onclick="answerCard(3)">Good</button>
                        <button class="btn-success"  onclick="answerCard(4)">Easy</button>
                    </div>
                    <div style="text-align:center;">
                        <a href="#" onclick="skip(); return false;" style="font-size:0.82rem; color:var(--text-muted);">Skip (no rating)</a>
                    </div>

                </div><!-- /results-section -->
            </div><!-- /card-content -->
        </div><!-- /card-phase -->

    </main>

    <script src="/static/js/menu.js"></script>
    <script>
        const DEFAULT_VOICES = { 'fr-FR': 'fr-FR-DeniseNeural', 'en-US': 'en-US-JennyNeural' };

        let currentCardId   = null;
        let currentAssessment = null;
        let selectedDeck    = '';
        let selectedField   = '';
        let selectedAudio   = '';
        let selectedLang    = 'fr-FR';
        let mediaRecorder   = null;
        let audioChunks     = [];

        function scoreClass(n) {
            return n >= 80 ? 'score-green' : n >= 50 ? 'score-yellow' : 'score-red';
        }

        // ── Init ──────────────────────────────────────────────────
        async function init() {
            const sRes = await fetch('/api/settings').catch(() => null);
            if (sRes && sRes.ok) {
                const s = await sRes.json();
                if (!s.azure_key_set) show('azure-banner');
            }

            try {
                const res = await fetch('/api/decks');
                if (!res.ok) throw new Error();
                const { decks } = await res.json();
                const sel = document.getElementById('deck-select');
                decks.forEach(d => {
                    const o = document.createElement('option');
                    o.value = o.textContent = d;
                    sel.appendChild(o);
                });
                if (decks.length) {
                    await loadFields(decks[0]);
                    document.getElementById('start-btn').disabled = false;
                }
            } catch {
                show('anki-banner');
            }

            document.getElementById('deck-select').addEventListener('change', e => loadFields(e.target.value));
            document.getElementById('start-btn').addEventListener('click', startPracticing);

            const btn = document.getElementById('record-btn');
            btn.addEventListener('mousedown',  startRecording);
            btn.addEventListener('mouseup',    stopRecording);
            btn.addEventListener('mouseleave', stopRecording);
            btn.addEventListener('touchstart', e => { e.preventDefault(); startRecording(); }, { passive: false });
            btn.addEventListener('touchend',   stopRecording);
        }

        function show(id) { document.getElementById(id).style.display = 'block'; }
        function hide(id) { document.getElementById(id).style.display = 'none'; }

        // ── Field loading ─────────────────────────────────────────
        async function loadFields(deck) {
            const tSel = document.getElementById('text-field-select');
            const aSel = document.getElementById('audio-field-select');
            tSel.innerHTML = '';
            aSel.innerHTML = '';
            tSel.disabled = aSel.disabled = true;
            try {
                const res = await fetch(`/api/pronunciation/fields?deck=${encodeURIComponent(deck)}`);
                if (!res.ok) return;
                const { fields } = await res.json();
                fields.forEach(f => {
                    [tSel, aSel].forEach(sel => {
                        const o = document.createElement('option');
                        o.value = o.textContent = f;
                        sel.appendChild(o);
                    });
                });
                tSel.disabled = aSel.disabled = false;
            } catch { /* leave disabled */ }
        }

        // ── Session start ─────────────────────────────────────────
        async function startPracticing() {
            selectedDeck  = document.getElementById('deck-select').value;
            selectedField = document.getElementById('text-field-select').value;
            selectedAudio = document.getElementById('audio-field-select').value;
            selectedLang  = document.getElementById('language-select').value;
            hide('setup-phase');
            show('card-phase');
            await loadCard();
        }

        function showSetup() {
            hide('card-phase');
            show('setup-phase');
        }

        // ── Card loading ──────────────────────────────────────────
        async function loadCard() {
            resetForRecording();
            hide('results-section');
            hide('no-cards-msg');
            show('card-content');

            const url = `/api/pronunciation/card`
                + `?deck=${encodeURIComponent(selectedDeck)}`
                + `&field=${encodeURIComponent(selectedField)}`
                + `&audio_field=${encodeURIComponent(selectedAudio)}`;

            const res = await fetch(url).catch(() => null);
            if (!res || res.status === 404) {
                hide('card-content');
                show('no-cards-msg');
                return;
            }
            if (!res.ok) return;

            const data = await res.json();
            currentCardId = data.card_id;
            document.getElementById('pronounce-text').textContent = data.text;

            const audioEl = document.getElementById('ref-audio');
            audioEl.src = '';
            if (data.audio_base64) {
                audioEl.src = 'data:audio/mpeg;base64,' + data.audio_base64;
            } else {
                const voice = DEFAULT_VOICES[selectedLang] || DEFAULT_VOICES['fr-FR'];
                const tRes = await fetch('/api/word-lookup/audio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: data.text, voice }),
                }).catch(() => null);
                if (tRes && tRes.ok) {
                    const { audio_base64 } = await tRes.json();
                    audioEl.src = 'data:audio/mpeg;base64,' + audio_base64;
                }
            }
        }

        // ── Recording ─────────────────────────────────────────────
        async function startRecording() {
            if (mediaRecorder && mediaRecorder.state === 'recording') return;
            audioChunks = [];
            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch {
                document.getElementById('record-status').textContent = 'Microphone access denied.';
                return;
            }
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
            mediaRecorder.start();
            document.getElementById('record-btn').classList.add('recording');
            document.getElementById('record-btn').textContent = '● Recording…';
            document.getElementById('record-status').textContent = '';
        }

        async function stopRecording() {
            if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(t => t.stop());
            const btn = document.getElementById('record-btn');
            btn.classList.remove('recording');
            btn.textContent = '🎤 Hold to Record';
            document.getElementById('record-status').textContent = 'Evaluating…';

            await new Promise(resolve => { mediaRecorder.onstop = resolve; });

            const blob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });
            const audioBase64 = await new Promise(resolve => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(blob);
            });

            await submitAudio(audioBase64);
        }

        async function submitAudio(audioBase64) {
            try {
                const res = await fetch('/api/pronunciation/assess', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        audio_base64: audioBase64,
                        reference_text: document.getElementById('pronounce-text').textContent,
                        language: selectedLang,
                    }),
                });
                if (!res.ok) {
                    const { detail } = await res.json().catch(() => ({}));
                    document.getElementById('record-status').textContent = detail ?? `Error ${res.status}`;
                    return;
                }
                currentAssessment = await res.json();
                showResults(currentAssessment);
            } catch {
                document.getElementById('record-status').textContent = 'Network error.';
            }
        }

        // ── Results rendering ─────────────────────────────────────
        function showResults(data) {
            document.getElementById('record-status').textContent = '';
            show('results-section');

            const score = Math.round(data.overall.pron_score);
            const badge = document.getElementById('overall-badge');
            badge.textContent = `PronScore: ${score}/100`;
            badge.className = `eval-badge ${score >= 80 ? 'eval-valid' : 'eval-warning'}`;

            const sub = document.getElementById('sub-scores');
            sub.innerHTML = ['accuracy', 'fluency', 'completeness'].map(k => {
                const v = Math.round(data.overall[k]);
                return `<span class="score-badge ${scoreClass(v)}">${k.charAt(0).toUpperCase() + k.slice(1)}: ${v}</span>`;
            }).join('');

            const refText = document.getElementById('pronounce-text').textContent.toLowerCase().trim();
            const heardText = (data.recognized_text || '').toLowerCase().trim();
            if (heardText && heardText !== refText) {
                document.getElementById('heard-text').textContent = data.recognized_text;
                show('heard-row');
            } else {
                hide('heard-row');
            }

            // Find worst-scoring word index
            let worstIdx = 0;
            data.words.forEach((w, i) => { if (w.accuracy < data.words[worstIdx].accuracy) worstIdx = i; });

            const container = document.getElementById('words-container');
            container.innerHTML = '';
            data.words.forEach((word, idx) => {
                const wordWrap = document.createElement('div');
                wordWrap.style.marginBottom = '0.5rem';

                const chip = document.createElement('div');
                const sc = scoreClass(word.accuracy);
                chip.className = `word-chip ${sc}`;
                const errorLabel = word.error_type !== 'None' ? ` · ${word.error_type}` : '';
                chip.textContent = `${word.word} ${Math.round(word.accuracy)}${errorLabel}`;

                const phonemeRow = document.createElement('div');
                phonemeRow.className = 'phoneme-row';
                phonemeRow.style.display = idx === worstIdx ? 'flex' : 'none';

                word.phonemes.forEach(p => {
                    const pc = document.createElement('span');
                    const psc = scoreClass(p.accuracy);
                    pc.className = `phoneme-chip ${psc}`;
                    pc.textContent = `${p.symbol} ${Math.round(p.accuracy)}`;
                    phonemeRow.appendChild(pc);
                });

                chip.addEventListener('click', () => {
                    phonemeRow.style.display = phonemeRow.style.display === 'none' ? 'flex' : 'none';
                });

                wordWrap.appendChild(chip);
                wordWrap.appendChild(phonemeRow);
                container.appendChild(wordWrap);
            });

            // Reset recommendations
            const recsBtn = document.getElementById('get-recs-btn');
            recsBtn.disabled = false;
            recsBtn.style.display = '';
            recsBtn.textContent = 'Get Recommendations';
            hide('recs-content');
            document.getElementById('recs-content').innerHTML = '';
            document.getElementById('recs-error').textContent = '';
        }

        // ── Recommendations ───────────────────────────────────────
        async function getRecommendations() {
            const btn = document.getElementById('get-recs-btn');
            btn.disabled = true;
            btn.textContent = 'Loading…';
            document.getElementById('recs-error').textContent = '';

            try {
                const res = await fetch('/api/pronunciation/recommendations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        reference_text: document.getElementById('pronounce-text').textContent,
                        language: selectedLang,
                        words: currentAssessment.words,
                    }),
                });
                if (!res.ok) {
                    const { detail } = await res.json().catch(() => ({}));
                    document.getElementById('recs-error').textContent = detail ?? 'Failed.';
                    btn.disabled = false;
                    btn.textContent = 'Retry';
                    return;
                }
                const { tips } = await res.json();
                const content = document.getElementById('recs-content');
                content.innerHTML = tips.map(t => `<p style="margin-bottom:0.4rem;">• ${t}</p>`).join('');
                show('recs-content');
                btn.style.display = 'none';
            } catch {
                document.getElementById('recs-error').textContent = 'Network error.';
                btn.disabled = false;
                btn.textContent = 'Retry';
            }
        }

        // ── Card flow ─────────────────────────────────────────────
        function resetForRecording() {
            hide('results-section');
            document.getElementById('record-status').textContent = '';
            document.getElementById('record-btn').classList.remove('recording');
            document.getElementById('record-btn').textContent = '🎤 Hold to Record';
            currentAssessment = null;
        }

        async function answerCard(ease) {
            if (!currentCardId) return;
            await fetch('/api/pronunciation/answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ card_id: currentCardId, ease }),
            }).catch(() => {});
            await loadCard();
        }

        async function skip() {
            await loadCard();
        }

        init();
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify the dev server starts cleanly**

```bash
uv run uvicorn app.main:app --reload &
sleep 3
curl -s http://localhost:8000/pronunciation | head -5
kill %1
```

Expected: HTML output starting with `<!DOCTYPE html>`.

- [ ] **Step 3: Run the full test suite one final time**

```bash
uv run pytest -v
```

Expected: all tests PASS, no failures.

- [ ] **Step 4: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: add pronunciation practice frontend"
```
