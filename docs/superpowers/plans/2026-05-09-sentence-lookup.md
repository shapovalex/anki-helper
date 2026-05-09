# French Sentence Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a /sentence-lookup page that translates a French sentence to Russian, generates a single audio file via Azure TTS, and saves a 3-field Anki note; also fix both voice dropdowns to fetch voices dynamically from Azure.

**Architecture:** New parallel router/agent/page pattern mirrors the existing word-lookup feature. `AudioAgent` gains a `list_voices()` method shared by both routers. All other components (translation agent, router, page) are new and independent.

**Tech Stack:** FastAPI, Pydantic v2, httpx, Azure TTS REST API, OpenRouter, Anki-Connect, vanilla JS

---

## File Map

| Action | File |
|--------|------|
| Modify | `app/schemas.py` |
| Modify | `app/config.py` |
| Modify | `app/agents/audio_agent.py` |
| Modify | `app/routers/word_lookup.py` |
| Modify | `app/routers/settings.py` |
| Modify | `app/main.py` |
| Modify | `static/components/menu.html` |
| Modify | `static/settings.html` |
| Modify | `tests/test_word_lookup_router.py` |
| Modify | `tests/test_settings_router.py` |
| Modify | `tests/test_config.py` |
| Create | `app/agents/french_sentence_translation_agent.py` |
| Create | `app/routers/sentence_lookup.py` |
| Create | `static/sentence-lookup.html` |
| Create | `tests/test_sentence_lookup_router.py` |

---

## Task 1: Add new Pydantic schemas

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: Add three new models and update two existing ones in `app/schemas.py`**

Add after the existing `AddToAnkiResponse` model:

```python
class SentenceTranslationResult(BaseModel):
    russian_sentence: str
    sentence_evaluation: str
    is_valid: bool


class SentenceGenerateRequest(BaseModel):
    sentence: str


class AddSentenceToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    french_sentence: str = Field(min_length=1, max_length=500)
    russian_sentence: str
    audio_base64: str
```

Update `SettingsResponse` to add `sentence_note_type: str`:

```python
class SettingsResponse(BaseModel):
    model: str
    azure_region: str
    openrouter_key_set: bool
    azure_key_set: bool
    note_type: str
    sentence_note_type: str
```

Update `SettingsUpdateRequest` to add `sentence_note_type`:

```python
class SettingsUpdateRequest(BaseModel):
    model: str | None = Field(default=None, min_length=1)
    azure_region: str | None = Field(default=None, min_length=1)
    openrouter_api_key: str | None = Field(default=None, min_length=1)
    azure_api_key: str | None = Field(default=None, min_length=1)
    note_type: str | None = Field(default=None, min_length=1)
    sentence_note_type: str | None = Field(default=None, min_length=1)
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add sentence lookup schemas"
```

---

## Task 2: Add SENTENCE_NOTE_TYPE_NAME to config

**Files:**
- Modify: `app/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_sentence_note_type_default():
    from app.config import ConfigManager
    config = ConfigManager()
    assert config.sentence_note_type_name == "French-Russian-Sentence"
```

Also update the `isolated_env` fixture's `monkeypatch.delenv` list to include `"SENTENCE_NOTE_TYPE_NAME"`:

```python
@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    fake_env = tmp_path / ".env.local"
    monkeypatch.setattr("app.config.ENV_LOCAL_PATH", fake_env)
    for key in ["OPENROUTER_API_KEY", "OPENROUTER_MODEL", "AZURE_TTS_KEY", "AZURE_TTS_REGION", "NOTE_TYPE_NAME", "SENTENCE_NOTE_TYPE_NAME"]:
        monkeypatch.delenv(key, raising=False)
    return fake_env
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_config.py::test_sentence_note_type_default -v
```

Expected: `FAILED` — `AttributeError: 'ConfigManager' object has no attribute 'sentence_note_type_name'`

- [ ] **Step 3: Add to `app/config.py`**

In `_DEFAULTS`, add:
```python
"SENTENCE_NOTE_TYPE_NAME": "French-Russian-Sentence",
```

In `_MANAGED_KEYS`, add:
```python
"SENTENCE_NOTE_TYPE_NAME",
```

Add property after `note_type_name`:
```python
@property
def sentence_note_type_name(self) -> str:
    return self._data["SENTENCE_NOTE_TYPE_NAME"]
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_config.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add SENTENCE_NOTE_TYPE_NAME config key"
```

---

## Task 3: Update settings router, tests, and page

**Files:**
- Modify: `app/routers/settings.py`
- Modify: `tests/test_settings_router.py`
- Modify: `static/settings.html`

- [ ] **Step 1: Write the failing tests**

Update `mock_config` fixture in `tests/test_settings_router.py` to add `sentence_note_type_name`:

```python
@pytest.fixture
def mock_config():
    config = MagicMock()
    config.openrouter_model = "google/gemini-flash-1.5"
    config.azure_tts_region = "westeurope"
    config.openrouter_key_set = True
    config.azure_key_set = False
    config.note_type_name = "French-Russian"
    config.sentence_note_type_name = "French-Russian-Sentence"
    return config
```

Update `test_get_settings_returns_status_and_model` to also assert `sentence_note_type`:

```python
def test_get_settings_returns_status_and_model(client, mock_config):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "google/gemini-flash-1.5"
    assert data["azure_region"] == "westeurope"
    assert data["openrouter_key_set"] is True
    assert data["azure_key_set"] is False
    assert data["note_type"] == "French-Russian"
    assert data["sentence_note_type"] == "French-Russian-Sentence"
    assert "openrouter_api_key" not in data
    assert "azure_api_key" not in data
```

Add a new test for saving `sentence_note_type`:

```python
def test_post_settings_saves_sentence_note_type(client, mock_config):
    response = client.post("/api/settings", json={"sentence_note_type": "My-Sentence-Type"})
    assert response.status_code == 200
    mock_config.save.assert_called_once_with({"SENTENCE_NOTE_TYPE_NAME": "My-Sentence-Type"})
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_settings_router.py -v
```

Expected: `test_get_settings_returns_status_and_model` and `test_post_settings_saves_sentence_note_type` FAIL

- [ ] **Step 3: Update `app/routers/settings.py`**

In `get_settings`, add `sentence_note_type=config.sentence_note_type_name`:

```python
@router.get("", response_model=SettingsResponse)
async def get_settings(
    config: ConfigManager = Depends(get_config),
) -> SettingsResponse:
    return SettingsResponse(
        model=config.openrouter_model,
        azure_region=config.azure_tts_region,
        openrouter_key_set=config.openrouter_key_set,
        azure_key_set=config.azure_key_set,
        note_type=config.note_type_name,
        sentence_note_type=config.sentence_note_type_name,
    )
```

In `update_settings`, add handling for `sentence_note_type`:

```python
@router.post("", response_model=dict[str, bool])
async def update_settings(
    body: SettingsUpdateRequest,
    config: ConfigManager = Depends(get_config),
) -> dict:
    updates: dict[str, str] = {}
    if body.openrouter_api_key is not None:
        updates["OPENROUTER_API_KEY"] = body.openrouter_api_key
    if body.azure_api_key is not None:
        updates["AZURE_TTS_KEY"] = body.azure_api_key
    if body.model is not None:
        updates["OPENROUTER_MODEL"] = body.model
    if body.azure_region is not None:
        updates["AZURE_TTS_REGION"] = body.azure_region
    if body.note_type is not None:
        updates["NOTE_TYPE_NAME"] = body.note_type
    if body.sentence_note_type is not None:
        updates["SENTENCE_NOTE_TYPE_NAME"] = body.sentence_note_type
    if updates:
        try:
            config.save(updates)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Failed to persist settings") from exc
    return {"ok": True}
```

- [ ] **Step 4: Run to verify tests pass**

```bash
uv run pytest tests/test_settings_router.py -v
```

Expected: all PASSED

- [ ] **Step 5: Update `static/settings.html`**

Add the new field inside the Anki section, after the existing Note Type Name field (after its closing `</div>`):

```html
        <div class="field">
            <label>Sentence Note Type Name</label>
            <input type="text" id="sentence-note-type" placeholder="French-Russian-Sentence">
            <p class="hint">Must exactly match the note type in Anki with fields: french_sentence, russian_sentence, audio.</p>
        </div>
```

In `loadSettings()`, add:
```js
document.getElementById('sentence-note-type').value = s.sentence_note_type;
```

In `saveSettings()`, after the `noteType` variable, add:
```js
const sentenceNoteType = document.getElementById('sentence-note-type').value.trim();
```

And add to body building:
```js
if (sentenceNoteType) body.sentence_note_type = sentenceNoteType;
```

- [ ] **Step 6: Commit**

```bash
git add app/routers/settings.py tests/test_settings_router.py static/settings.html
git commit -m "feat: expose sentence_note_type in settings"
```

---

## Task 4: Add list_voices() to AudioAgent and fix word-lookup voices endpoint

**Files:**
- Modify: `app/agents/audio_agent.py`
- Modify: `app/routers/word_lookup.py`
- Modify: `tests/test_word_lookup_router.py`

- [ ] **Step 1: Update the word-lookup voices test to expect dynamic voices**

In `tests/test_word_lookup_router.py`, add `from app.schemas import Voice` to imports.

Replace the `mock_audio_agent` fixture with:

```python
@pytest.fixture
def mock_audio_agent():
    agent = MagicMock()
    agent.synthesize = AsyncMock(return_value="bW9jaw==")
    agent.list_voices = AsyncMock(return_value=[
        Voice(id="fr-FR-DeniseNeural", name="Denise (Female)"),
        Voice(id="fr-FR-HenriNeural", name="Henri (Male)"),
        Voice(id="fr-FR-EloiseNeural", name="Eloise (Female)"),
    ])
    return agent
```

Replace `test_voices_returns_non_empty_list` with:

```python
def test_voices_returns_list_from_agent(client, mock_audio_agent):
    response = client.get("/api/word-lookup/voices")
    assert response.status_code == 200
    voices = response.json()["voices"]
    assert len(voices) == 3
    assert all("id" in v and "name" in v for v in voices)
    mock_audio_agent.list_voices.assert_called_once()
```

- [ ] **Step 2: Run to verify the test fails**

```bash
uv run pytest tests/test_word_lookup_router.py::test_voices_returns_list_from_agent -v
```

Expected: FAILED (endpoint returns hardcoded list, not from agent)

- [ ] **Step 3: Add `list_voices()` to `app/agents/audio_agent.py`**

Add `from app.schemas import Voice` at the top of the file.

Add this method to `AudioAgent`:

```python
async def list_voices(self, locale_prefix: str = "fr-") -> list[Voice]:
    url = f"https://{self._region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
    response = await self._client.get(
        url,
        headers={"Ocp-Apim-Subscription-Key": self._api_key},
        timeout=10.0,
    )
    response.raise_for_status()
    voices = [
        Voice(
            id=v["ShortName"],
            name=f"{v['DisplayName']} ({v['Gender']})",
        )
        for v in response.json()
        if v.get("Locale", "").startswith(locale_prefix)
    ]
    return sorted(voices, key=lambda v: v.name)
```

- [ ] **Step 4: Update `app/routers/word_lookup.py`**

Remove the `_FRENCH_VOICES` constant entirely.

Replace the voices endpoint:

```python
@router.get("/voices", response_model=VoicesResponse)
async def list_voices(
    agent: AudioAgent = Depends(get_audio_agent),
) -> VoicesResponse:
    try:
        voices = await agent.list_voices()
        return VoicesResponse(voices=voices)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
```

- [ ] **Step 5: Run all word-lookup tests**

```bash
uv run pytest tests/test_word_lookup_router.py -v
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add app/agents/audio_agent.py app/routers/word_lookup.py tests/test_word_lookup_router.py
git commit -m "feat: fetch French voices dynamically from Azure TTS"
```

---

## Task 5: Create FrenchSentenceTranslationAgent

**Files:**
- Create: `app/agents/french_sentence_translation_agent.py`

- [ ] **Step 1: Create the agent file**

```python
import json
import httpx
from pydantic import ValidationError
from app.schemas import SentenceTranslationResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a French language expert. When given a French sentence, "
    "respond ONLY with a JSON object (no markdown) with exactly these keys:\n"
    "- russian_sentence: Russian translation of the sentence\n"
    "- sentence_evaluation: brief note on the grammar and naturalness of the French sentence\n"
    "- is_valid: true if the sentence is grammatically correct French, false otherwise"
)


class FrenchSentenceTranslationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def generate(self, sentence: str) -> SentenceTranslationResult:
        response = await self._client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": sentence},
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
        try:
            return SentenceTranslationResult(**data)
        except ValidationError as exc:
            raise ValueError(f"OpenRouter response missing required fields: {exc}") from exc
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/french_sentence_translation_agent.py
git commit -m "feat: add FrenchSentenceTranslationAgent"
```

---

## Task 6: Create sentence-lookup router and tests

**Files:**
- Create: `app/routers/sentence_lookup.py`
- Create: `tests/test_sentence_lookup_router.py`
- Modify: `app/main.py`

- [ ] **Step 1: Register the router in `app/main.py` first**

`TestClient(app)` resolves routes from `app/main.py` at import time, so the router must be registered before the tests can find any endpoints.

Add import after the existing router imports in `app/main.py`:

```python
from app.routers import sentence_lookup as sentence_lookup_router
```

Add include after the existing router includes:

```python
app.include_router(sentence_lookup_router.router)
```

Do NOT add the page route here — that comes in Task 7.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_sentence_lookup_router.py`:

```python
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
```

- [ ] **Step 3: Run to verify tests fail with import error**

```bash
uv run pytest tests/test_sentence_lookup_router.py -v
```

Expected: `ImportError` — `cannot import name 'sentence_lookup' from 'app.routers'` (module doesn't exist yet)

- [ ] **Step 4: Create `app/routers/sentence_lookup.py`**

```python
import logging
import re
import unicodedata
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.audio_agent import AudioAgent
from app.agents.french_sentence_translation_agent import FrenchSentenceTranslationAgent
from app.anki_client import AnkiClient, AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    AddSentenceToAnkiRequest,
    AddToAnkiResponse,
    SentenceGenerateRequest,
    SentenceTranslationResult,
    VoicesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sentence-lookup", tags=["sentence-lookup"])


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", text).strip("_")
    return slug or "sentence"


def get_translation_agent(request: Request) -> FrenchSentenceTranslationAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return FrenchSentenceTranslationAgent(
        client=request.app.state.http_client,
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
    )


def get_audio_agent(request: Request) -> AudioAgent:
    config: ConfigManager = request.app.state.config
    if not config.azure_key_set:
        raise HTTPException(
            status_code=503,
            detail="Azure TTS API key not configured. Go to Settings.",
        )
    return AudioAgent(
        client=request.app.state.http_client,
        api_key=config.azure_tts_key,
        region=config.azure_tts_region,
    )


def get_anki_client(request: Request) -> AnkiClient:
    return request.app.state.anki_client


@router.get("/voices", response_model=VoicesResponse)
async def list_voices(
    agent: AudioAgent = Depends(get_audio_agent),
) -> VoicesResponse:
    try:
        voices = await agent.list_voices()
        return VoicesResponse(voices=voices)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")


@router.post("/generate", response_model=SentenceTranslationResult)
async def generate(
    body: SentenceGenerateRequest,
    agent: FrenchSentenceTranslationAgent = Depends(get_translation_agent),
) -> SentenceTranslationResult:
    try:
        return await agent.generate(sentence=body.sentence)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Unexpected error in generate endpoint")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/add-to-anki", response_model=AddToAnkiResponse)
async def add_to_anki(
    body: AddSentenceToAnkiRequest,
    anki_client=Depends(get_anki_client),
) -> AddToAnkiResponse:
    filename = f"{_slugify(body.french_sentence[:40])}.mp3"
    try:
        await anki_client.invoke(
            "storeMediaFile",
            filename=filename,
            data=body.audio_base64,
        )
        note_id = await anki_client.invoke(
            "addNote",
            note={
                "deckName": body.deck,
                "modelName": body.note_type,
                "fields": {
                    "french_sentence": body.french_sentence,
                    "russian_sentence": body.russian_sentence,
                    "audio": f"[sound:{filename}]",
                },
                "options": {"allowDuplicate": False},
                "tags": [],
            },
        )
        return AddToAnkiResponse(note_id=note_id)
    except AnkiConnectError as e:
        msg = str(e)
        if "model" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Note type '{body.note_type}' not found in Anki. Check Settings.",
            )
        raise HTTPException(status_code=502, detail=msg)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_sentence_lookup_router.py -v
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/routers/sentence_lookup.py tests/test_sentence_lookup_router.py
git commit -m "feat: add sentence-lookup router with generate and add-to-anki endpoints"
```

---

## Task 7: Register router, add page route, update menu

**Files:**
- Modify: `app/main.py`
- Modify: `static/components/menu.html`

> **Note:** The API router (`include_router`) was already added to `app/main.py` in Task 6 Step 1. This task adds the page route and menu entry.

- [ ] **Step 1: Add page route to `app/main.py`**

Add after the existing `/word-lookup` route:

```python
@app.get("/sentence-lookup")
async def sentence_lookup() -> FileResponse:
    return FileResponse("static/sentence-lookup.html")
```

- [ ] **Step 2: Update `static/components/menu.html`**

Add "Sentence Lookup" after "Word Lookup":

```html
<nav>
    <a href="/" class="nav-brand">Anki Helper</a>
    <div class="nav-links">
        <a href="/">Home</a>
        <a href="/word-lookup">Word Lookup</a>
        <a href="/sentence-lookup">Sentence Lookup</a>
        <a href="/pronunciation">Pronunciation</a>
        <a href="/settings">Settings</a>
        <a href="/help">Help</a>
    </div>
</nav>
```

- [ ] **Step 3: Run the full test suite to confirm nothing is broken**

```bash
uv run pytest -v
```

Expected: all PASSED

- [ ] **Step 4: Commit**

```bash
git add app/main.py static/components/menu.html
git commit -m "feat: add sentence-lookup page route and navigation menu entry"
```

---

## Task 8: Create the sentence-lookup frontend page

**Files:**
- Create: `static/sentence-lookup.html`

- [ ] **Step 1: Create `static/sentence-lookup.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentence Lookup — Anki Helper</title>
    <link rel="stylesheet" href="/static/css/theme.css">
</head>
<body>
    <div id="menu-container"></div>
    <main class="page">
        <div class="page-header">
            <h1 class="page-title">Sentence Lookup</h1>
            <p class="page-subtitle">Translate a French sentence and generate audio for Anki.</p>
        </div>

        <div id="keys-banner" class="banner banner-error" style="display:none;">
            API keys not configured. <a href="/settings">Go to Settings →</a>
        </div>

        <div class="field">
            <label>French Sentence</label>
            <textarea id="sentence-input" rows="3" placeholder="e.g. Comment allez-vous?" autocomplete="off"></textarea>
        </div>

        <div class="field" style="margin-bottom: 1.25rem;">
            <label>Azure Voice</label>
            <select id="voice-select"></select>
        </div>

        <button id="generate-btn" class="btn-primary btn-full" disabled>⚡ Generate</button>
        <div id="generate-error" class="inline-error"></div>

        <div id="result-section" class="result-section" style="display:none;">
            <div id="eval-badge" class="eval-badge"></div>

            <div class="field">
                <label>Translation (Russian)</label>
                <textarea id="translation" rows="2"></textarea>
            </div>

            <div class="field">
                <label>Audio</label>
                <div class="audio-row">
                    <audio id="sentence-audio" controls></audio>
                    <button class="btn-secondary" onclick="regenAudio()">↺ Re-generate</button>
                </div>
                <div id="sentence-audio-error" class="inline-error"></div>
            </div>

            <div class="divider"></div>

            <div class="add-row">
                <label style="flex-shrink:0; margin-bottom:0;">Deck</label>
                <select id="deck-select"></select>
                <button id="add-anki-btn" class="btn-success" disabled onclick="addToAnki()">+ Add to Anki</button>
            </div>
            <div id="add-anki-status" style="margin-top: 0.5rem;"></div>
        </div>
    </main>

    <script src="/static/js/menu.js"></script>
    <script>
        const LS_VOICE = 'anki_sentence_voice';
        const LS_DECK  = 'anki_sentence_deck';

        let audioBase64  = null;
        let noteTypeName = 'French-Russian-Sentence';

        async function init() {
            const vRes = await fetch('/api/sentence-lookup/voices');
            const { voices } = await vRes.json();
            const voiceSel = document.getElementById('voice-select');
            voices.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = v.name;
                voiceSel.appendChild(opt);
            });

            const savedVoice = localStorage.getItem(LS_VOICE);
            if (savedVoice) voiceSel.value = savedVoice;

            voiceSel.addEventListener('change', e =>
                localStorage.setItem(LS_VOICE, e.target.value));

            const sRes     = await fetch('/api/settings');
            const settings = await sRes.json();
            noteTypeName   = settings.sentence_note_type;

            if (!settings.openrouter_key_set || !settings.azure_key_set) {
                document.getElementById('keys-banner').style.display = 'block';
            } else {
                document.getElementById('generate-btn').disabled = false;
            }

            try {
                const dRes    = await fetch('/api/decks');
                const { decks } = await dRes.json();
                const deckSel = document.getElementById('deck-select');
                decks.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d;
                    opt.textContent = d;
                    deckSel.appendChild(opt);
                });
                const savedDeck = localStorage.getItem(LS_DECK);
                if (savedDeck) deckSel.value = savedDeck;
                deckSel.addEventListener('change', e =>
                    localStorage.setItem(LS_DECK, e.target.value));
            } catch { /* Anki not running */ }
        }

        async function generate() {
            const sentence = document.getElementById('sentence-input').value.trim();
            if (!sentence) return;

            audioBase64 = null;
            document.getElementById('add-anki-btn').disabled = true;
            document.getElementById('result-section').style.display = 'none';
            document.getElementById('generate-error').textContent = '';
            document.getElementById('sentence-audio').src = '';

            const btn = document.getElementById('generate-btn');
            btn.textContent = '⏳ Generating…';
            btn.disabled    = true;

            try {
                const res = await fetch('/api/sentence-lookup/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sentence }),
                });

                if (!res.ok) {
                    const { detail } = await res.json().catch(() => ({}));
                    document.getElementById('generate-error').textContent = detail ?? `Error ${res.status}`;
                    return;
                }

                const data = await res.json();
                document.getElementById('translation').value = data.russian_sentence;

                const badge = document.getElementById('eval-badge');
                badge.textContent = (data.is_valid ? '✓ ' : '⚠ ') + data.sentence_evaluation;
                badge.className   = 'eval-badge ' + (data.is_valid ? 'eval-valid' : 'eval-warning');

                document.getElementById('result-section').style.display = 'block';

                await generateAudio(sentence);
            } catch {
                document.getElementById('generate-error').textContent = 'Network error.';
            } finally {
                btn.textContent = '⚡ Generate';
                btn.disabled    = false;
            }
        }

        async function generateAudio(text) {
            const audioEl = document.getElementById('sentence-audio');
            const errEl   = document.getElementById('sentence-audio-error');
            errEl.textContent = '';

            const voice = document.getElementById('voice-select').value;

            try {
                const res = await fetch('/api/word-lookup/audio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, voice }),
                });

                if (!res.ok) {
                    const { detail } = await res.json().catch(() => ({}));
                    errEl.textContent = detail ?? `Audio error ${res.status}`;
                    return;
                }

                const { audio_base64 } = await res.json();
                audioEl.src = 'data:audio/mpeg;base64,' + audio_base64;
                audioBase64 = audio_base64;
            } catch {
                errEl.textContent = 'Audio generation failed.';
            }

            document.getElementById('add-anki-btn').disabled = !audioBase64;
        }

        async function regenAudio() {
            const text = document.getElementById('sentence-input').value.trim();
            if (!text) return;
            await generateAudio(text);
        }

        async function addToAnki() {
            const statusEl = document.getElementById('add-anki-status');
            statusEl.textContent = '';
            document.getElementById('add-anki-btn').disabled = true;

            try {
                const res = await fetch('/api/sentence-lookup/add-to-anki', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        deck:             document.getElementById('deck-select').value,
                        note_type:        noteTypeName,
                        french_sentence:  document.getElementById('sentence-input').value.trim(),
                        russian_sentence: document.getElementById('translation').value,
                        audio_base64:     audioBase64,
                    }),
                });

                if (!res.ok) {
                    const { detail } = await res.json().catch(() => ({}));
                    statusEl.innerHTML = `<span class="inline-error">${detail ?? 'Failed to add.'}</span>`;
                    return;
                }

                statusEl.innerHTML = '<span class="success-msg">✓ Added to Anki!</span>';
            } catch {
                statusEl.innerHTML = '<span class="inline-error">Network error.</span>';
            } finally {
                document.getElementById('add-anki-btn').disabled = !audioBase64;
            }
        }

        document.getElementById('generate-btn').addEventListener('click', generate);

        init();
    </script>
</body>
</html>
```

- [ ] **Step 2: Run the full test suite one final time**

```bash
uv run pytest -v
```

Expected: all PASSED

- [ ] **Step 3: Commit**

```bash
git add static/sentence-lookup.html
git commit -m "feat: add sentence-lookup frontend page"
```
