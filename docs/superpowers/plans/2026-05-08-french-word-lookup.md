# French Word Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a French-word lookup screen that generates Russian translation, CEFR example, grammar evaluation, and Azure TTS audio, then lets the user add the result as an Anki card.

**Architecture:** Two plain Python agent classes (`FrenchWordTranslationAgent`, `AudioAgent`) are injected into FastAPI routers via dependency functions. A `ConfigManager` reads API keys from system env vars first, then `.env.local`, so the settings page can persist keys without touching the real environment. All browser preferences (CEFR, voice, deck) live in `localStorage`.

**Tech Stack:** Python 3.13, FastAPI, httpx (already present), Pydantic, pytest + pytest-asyncio; OpenRouter REST API (OpenAI-compatible); Azure TTS REST API; Anki Connect (existing).

---

## File Map

| File | Status | Role |
|---|---|---|
| `app/config.py` | **new** | `ConfigManager` — reads env vars → `.env.local` → defaults; writes to `.env.local` |
| `app/agents/__init__.py` | **new** | package marker |
| `app/agents/french_word_translation_agent.py` | **new** | `FrenchWordTranslationAgent` — OpenRouter structured output |
| `app/agents/audio_agent.py` | **new** | `AudioAgent` — Azure TTS REST → base64 MP3 |
| `app/schemas.py` | **extend** | add `TranslationResult`, request/response models |
| `app/routers/settings.py` | **new** | `GET/POST /api/settings` |
| `app/routers/word_lookup.py` | **new** | `/api/word-lookup/*` endpoints |
| `app/main.py` | **extend** | lifespan wires `config` + `http_client`; new routers + page routes |
| `static/components/menu.html` | **extend** | add Word Lookup and Settings nav links |
| `static/word-lookup.html` | **new** | full lookup UI |
| `static/settings.html` | **new** | settings UI |
| `tests/__init__.py` | **new** | package marker |
| `tests/agents/__init__.py` | **new** | package marker |
| `tests/test_config.py` | **new** | unit tests for ConfigManager |
| `tests/agents/test_french_word_translation_agent.py` | **new** | integration test (skipped if no key) |
| `tests/agents/test_audio_agent.py` | **new** | integration test (skipped if no key) |
| `tests/test_settings_router.py` | **new** | router unit tests with mock config |
| `tests/test_word_lookup_router.py` | **new** | router unit tests with mock agents |
| `.gitignore` | **extend** | add `.env.local` |
| `pyproject.toml` | **extend** | add pytest + pytest-asyncio dev deps |

---

## Task 1: Dev Setup

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `app/agents/__init__.py`, `tests/__init__.py`, `tests/agents/__init__.py`

- [ ] **Step 1: Add dev dependencies and pytest config to pyproject.toml**

Open `pyproject.toml` and add:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Add .env.local to .gitignore**

Append to `.gitignore`:

```
.env.local
```

- [ ] **Step 3: Create package markers**

```bash
touch app/agents/__init__.py tests/__init__.py tests/agents/__init__.py
```

- [ ] **Step 4: Install dev dependencies**

```bash
uv sync --dev
```

Expected: resolves and installs pytest and pytest-asyncio.

- [ ] **Step 5: Verify pytest discovers nothing yet**

```bash
uv run pytest --collect-only
```

Expected: `no tests ran` or `0 items`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock .gitignore app/agents/__init__.py tests/__init__.py tests/agents/__init__.py
git commit -m "chore: add pytest dev deps and test directory structure"
```

---

## Task 2: ConfigManager (TDD)

**Files:**
- Create: `app/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
import os
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    fake_env = tmp_path / ".env.local"
    monkeypatch.setattr("app.config.ENV_LOCAL_PATH", fake_env)
    for key in ["OPENROUTER_API_KEY", "OPENROUTER_MODEL", "AZURE_TTS_KEY", "AZURE_TTS_REGION", "NOTE_TYPE_NAME"]:
        monkeypatch.delenv(key, raising=False)
    return fake_env


def test_defaults_when_no_file():
    from app.config import ConfigManager
    config = ConfigManager()
    assert config.openrouter_model == "google/gemini-flash-1.5"
    assert config.azure_tts_region == "westeurope"
    assert config.note_type_name == "French-Russian"
    assert not config.openrouter_key_set
    assert not config.azure_key_set


def test_reads_env_file(isolated_env):
    from app.config import ConfigManager
    isolated_env.write_text("OPENROUTER_API_KEY=sk-test\nOPENROUTER_MODEL=gpt-4o\n")
    config = ConfigManager()
    assert config.openrouter_api_key == "sk-test"
    assert config.openrouter_model == "gpt-4o"
    assert config.openrouter_key_set


def test_env_var_overrides_file(isolated_env, monkeypatch):
    from app.config import ConfigManager
    isolated_env.write_text("OPENROUTER_API_KEY=from-file\n")
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-env")
    config = ConfigManager()
    assert config.openrouter_api_key == "from-env"


def test_save_writes_to_file(isolated_env):
    from app.config import ConfigManager
    config = ConfigManager()
    config.save({"OPENROUTER_API_KEY": "new-key", "OPENROUTER_MODEL": "claude-opus"})
    assert config.openrouter_api_key == "new-key"
    assert config.openrouter_model == "claude-opus"
    content = isolated_env.read_text()
    assert "OPENROUTER_API_KEY=new-key" in content
    assert "OPENROUTER_MODEL=claude-opus" in content


def test_save_preserves_existing_keys(isolated_env):
    from app.config import ConfigManager
    isolated_env.write_text("AZURE_TTS_KEY=azure-key\n")
    config = ConfigManager()
    config.save({"OPENROUTER_API_KEY": "or-key"})
    assert config.azure_tts_key == "azure-key"
    assert config.openrouter_api_key == "or-key"


def test_reload_picks_up_file_changes(isolated_env):
    from app.config import ConfigManager
    config = ConfigManager()
    assert not config.openrouter_key_set
    isolated_env.write_text("OPENROUTER_API_KEY=late-key\n")
    config.reload()
    assert config.openrouter_api_key == "late-key"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `app.config`.

- [ ] **Step 3: Implement ConfigManager**

Create `app/config.py`:

```python
import os
from pathlib import Path

ENV_LOCAL_PATH = Path(".env.local")

_DEFAULTS: dict[str, str] = {
    "OPENROUTER_MODEL": "google/gemini-flash-1.5",
    "AZURE_TTS_REGION": "westeurope",
    "NOTE_TYPE_NAME": "French-Russian",
}

_MANAGED_KEYS = {
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "AZURE_TTS_KEY",
    "AZURE_TTS_REGION",
    "NOTE_TYPE_NAME",
}


class ConfigManager:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        merged = {**_DEFAULTS, **self._read_env_file()}
        for key in _MANAGED_KEYS:
            if key in os.environ:
                merged[key] = os.environ[key]
        self._data = merged

    def _read_env_file(self) -> dict[str, str]:
        if not ENV_LOCAL_PATH.exists():
            return {}
        result: dict[str, str] = {}
        for line in ENV_LOCAL_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
        return result

    def save(self, updates: dict[str, str]) -> None:
        current = self._read_env_file()
        current.update(updates)
        ENV_LOCAL_PATH.write_text(
            "\n".join(f"{k}={v}" for k, v in current.items()) + "\n"
        )
        self.reload()

    @property
    def openrouter_api_key(self) -> str:
        return self._data.get("OPENROUTER_API_KEY", "")

    @property
    def openrouter_model(self) -> str:
        return self._data["OPENROUTER_MODEL"]

    @property
    def azure_tts_key(self) -> str:
        return self._data.get("AZURE_TTS_KEY", "")

    @property
    def azure_tts_region(self) -> str:
        return self._data["AZURE_TTS_REGION"]

    @property
    def note_type_name(self) -> str:
        return self._data["NOTE_TYPE_NAME"]

    @property
    def openrouter_key_set(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def azure_key_set(self) -> bool:
        return bool(self.azure_tts_key)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add ConfigManager with .env.local persistence"
```

---

## Task 3: Extend Schemas

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: Replace app/schemas.py with the extended version**

```python
from pydantic import BaseModel


class DeckListResponse(BaseModel):
    decks: list[str]


class TranslationResult(BaseModel):
    russian_word: str
    example: str
    word_evaluation: str
    is_valid: bool


class GenerateRequest(BaseModel):
    word: str
    cefr_level: str


class AudioRequest(BaseModel):
    text: str
    voice: str


class AudioResponse(BaseModel):
    audio_base64: str
    filename: str


class Voice(BaseModel):
    id: str
    name: str


class VoicesResponse(BaseModel):
    voices: list[Voice]


class AddToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    french_word: str
    russian_word: str
    example: str
    french_word_audio_base64: str
    example_audio_base64: str


class AddToAnkiResponse(BaseModel):
    note_id: int


class SettingsResponse(BaseModel):
    model: str
    azure_region: str
    openrouter_key_set: bool
    azure_key_set: bool
    note_type: str


class SettingsUpdateRequest(BaseModel):
    model: str | None = None
    azure_region: str | None = None
    openrouter_api_key: str | None = None
    azure_api_key: str | None = None
    note_type: str | None = None
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
uv run pytest -v
```

Expected: all previously passing tests still PASS.

- [ ] **Step 3: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add schemas for word lookup, audio, and settings"
```

---

## Task 4: FrenchWordTranslationAgent (TDD)

**Files:**
- Create: `app/agents/french_word_translation_agent.py`
- Create: `tests/agents/test_french_word_translation_agent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_french_word_translation_agent.py`:

```python
import os
import base64
import pytest
import httpx
from app.agents.french_word_translation_agent import FrenchWordTranslationAgent
from app.schemas import TranslationResult

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")


@pytest.mark.skipif(not OPENROUTER_KEY, reason="OPENROUTER_API_KEY not set")
async def test_generate_returns_translation_result():
    async with httpx.AsyncClient() as client:
        agent = FrenchWordTranslationAgent(
            client=client,
            api_key=OPENROUTER_KEY,
            model="google/gemini-flash-1.5",
        )
        result = await agent.generate(word="bonjour", cefr_level="B1")

    assert isinstance(result, TranslationResult)
    assert result.russian_word  # non-empty string
    assert result.example       # non-empty French sentence
    assert result.word_evaluation
    assert result.is_valid is True  # "bonjour" is valid


@pytest.mark.skipif(not OPENROUTER_KEY, reason="OPENROUTER_API_KEY not set")
async def test_generate_flags_misspelled_word():
    async with httpx.AsyncClient() as client:
        agent = FrenchWordTranslationAgent(
            client=client,
            api_key=OPENROUTER_KEY,
            model="google/gemini-flash-1.5",
        )
        result = await agent.generate(word="bonjore", cefr_level="A1")

    assert isinstance(result, TranslationResult)
    assert result.is_valid is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_french_word_translation_agent.py -v
```

Expected: `ImportError` — `app.agents.french_word_translation_agent` does not exist yet.

- [ ] **Step 3: Implement FrenchWordTranslationAgent**

Create `app/agents/french_word_translation_agent.py`:

```python
import json
import httpx
from app.schemas import TranslationResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a French language expert. When given a French word and a CEFR level, "
    "respond ONLY with a JSON object (no markdown) with exactly these keys:\n"
    "- russian_word: Russian translation of the word\n"
    "- example: a natural French sentence using the word, appropriate for the CEFR level\n"
    "- word_evaluation: brief note on whether the word is correctly spelled and valid French\n"
    "- is_valid: true if the word is a real, correctly spelled French word, false otherwise"
)


class FrenchWordTranslationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def generate(self, word: str, cefr_level: str) -> TranslationResult:
        prompt = (
            f"French word: {word}\n"
            f"CEFR level for the example sentence: {cefr_level}"
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
        return TranslationResult(**json.loads(content))
```

- [ ] **Step 4: Run tests**

If `OPENROUTER_API_KEY` is set in your environment:
```bash
uv run pytest tests/agents/test_french_word_translation_agent.py -v
```
Expected: both tests PASS.

If not set:
```bash
uv run pytest tests/agents/test_french_word_translation_agent.py -v
```
Expected: both tests SKIPPED (not failed).

- [ ] **Step 5: Commit**

```bash
git add app/agents/french_word_translation_agent.py tests/agents/test_french_word_translation_agent.py
git commit -m "feat: add FrenchWordTranslationAgent with OpenRouter structured output"
```

---

## Task 5: AudioAgent (TDD)

**Files:**
- Create: `app/agents/audio_agent.py`
- Create: `tests/agents/test_audio_agent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_audio_agent.py`:

```python
import os
import base64
import pytest
import httpx
from app.agents.audio_agent import AudioAgent

AZURE_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_REGION = os.getenv("AZURE_TTS_REGION", "westeurope")


@pytest.mark.skipif(not AZURE_KEY, reason="AZURE_TTS_KEY not set")
async def test_synthesize_returns_base64_mp3():
    async with httpx.AsyncClient() as client:
        agent = AudioAgent(client=client, api_key=AZURE_KEY, region=AZURE_REGION)
        result = await agent.synthesize(text="bonjour", voice="fr-FR-DeniseNeural")

    # Must be valid base64 and non-empty audio bytes
    audio_bytes = base64.b64decode(result)
    assert len(audio_bytes) > 1000  # real MP3 is always > 1KB


@pytest.mark.skipif(not AZURE_KEY, reason="AZURE_TTS_KEY not set")
async def test_synthesize_different_voice():
    async with httpx.AsyncClient() as client:
        agent = AudioAgent(client=client, api_key=AZURE_KEY, region=AZURE_REGION)
        result = await agent.synthesize(text="au revoir", voice="fr-FR-HenriNeural")

    assert len(base64.b64decode(result)) > 1000
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/agents/test_audio_agent.py -v
```

Expected: `ImportError` — `app.agents.audio_agent` does not exist.

- [ ] **Step 3: Implement AudioAgent**

Create `app/agents/audio_agent.py`:

```python
import base64
import httpx


class AudioAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, region: str) -> None:
        self._client = client
        self._api_key = api_key
        self._region = region

    async def synthesize(self, text: str, voice: str) -> str:
        url = f"https://{self._region}.tts.speech.microsoft.com/cognitiveservices/v1"
        ssml = (
            f"<speak version='1.0' xml:lang='fr-FR'>"
            f"<voice xml:lang='fr-FR' name='{voice}'>{text}</voice>"
            f"</speak>"
        )
        response = await self._client.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            },
            content=ssml.encode("utf-8"),
        )
        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/agents/test_audio_agent.py -v
```

Expected: PASS (or SKIPPED if `AZURE_TTS_KEY` not set).

- [ ] **Step 5: Commit**

```bash
git add app/agents/audio_agent.py tests/agents/test_audio_agent.py
git commit -m "feat: add AudioAgent with Azure TTS REST API"
```

---

## Task 6: Settings Router (TDD)

**Files:**
- Create: `app/routers/settings.py`
- Create: `tests/test_settings_router.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_settings_router.py`:

```python
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.routers.settings import get_config


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.openrouter_model = "google/gemini-flash-1.5"
    config.azure_tts_region = "westeurope"
    config.openrouter_key_set = True
    config.azure_key_set = False
    config.note_type_name = "French-Russian"
    return config


@pytest.fixture
def client(mock_config):
    app.dependency_overrides[get_config] = lambda: mock_config
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_settings_returns_status_and_model(client, mock_config):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "google/gemini-flash-1.5"
    assert data["azure_region"] == "westeurope"
    assert data["openrouter_key_set"] is True
    assert data["azure_key_set"] is False
    assert data["note_type"] == "French-Russian"
    assert "openrouter_api_key" not in data
    assert "azure_api_key" not in data


def test_post_settings_saves_provided_fields(client, mock_config):
    response = client.post("/api/settings", json={
        "openrouter_api_key": "sk-new",
        "model": "claude-opus",
    })
    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_config.save.assert_called_once_with({
        "OPENROUTER_API_KEY": "sk-new",
        "OPENROUTER_MODEL": "claude-opus",
    })


def test_post_settings_ignores_none_fields(client, mock_config):
    response = client.post("/api/settings", json={"azure_region": "eastus"})
    assert response.status_code == 200
    mock_config.save.assert_called_once_with({"AZURE_TTS_REGION": "eastus"})


def test_post_settings_empty_body_does_not_call_save(client, mock_config):
    response = client.post("/api/settings", json={})
    assert response.status_code == 200
    mock_config.save.assert_not_called()
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_settings_router.py -v
```

Expected: `ImportError` or 404 — `app.routers.settings` and `get_config` do not exist.

- [ ] **Step 3: Implement settings router**

Create `app/routers/settings.py`:

```python
from fastapi import APIRouter, Depends, Request

from app.config import ConfigManager
from app.schemas import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_config(request: Request) -> ConfigManager:
    return request.app.state.config


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
    )


@router.post("", response_model=dict)
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
    if updates:
        config.save(updates)
    return {"ok": True}
```

- [ ] **Step 4: Register the router temporarily so the tests can run**

Add to `app/main.py` (minimal change — full wiring comes in Task 8):

```python
from app.routers import settings as settings_router
# inside the FastAPI app setup, after existing include_router call:
app.include_router(settings_router.router)
```

Also add `app.state.config = ConfigManager()` to the lifespan:

```python
from app.config import ConfigManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        app.state.config = ConfigManager()
        app.state.http_client = http_client
        app.state.anki_client = AnkiClient(http_client)
        yield
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_settings_router.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/routers/settings.py tests/test_settings_router.py app/main.py
git commit -m "feat: add settings router with GET/POST /api/settings"
```

---

## Task 7: Word Lookup Router (TDD)

**Files:**
- Create: `app/routers/word_lookup.py`
- Create: `tests/test_word_lookup_router.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_word_lookup_router.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_word_lookup_router.py -v
```

Expected: `ImportError` — `app.routers.word_lookup` does not exist.

- [ ] **Step 3: Implement word lookup router**

Create `app/routers/word_lookup.py`:

```python
import re
import unicodedata
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.audio_agent import AudioAgent
from app.agents.french_word_translation_agent import FrenchWordTranslationAgent
from app.anki_client import AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    AddToAnkiRequest,
    AddToAnkiResponse,
    AudioRequest,
    AudioResponse,
    GenerateRequest,
    TranslationResult,
    Voice,
    VoicesResponse,
)

router = APIRouter(prefix="/api/word-lookup", tags=["word-lookup"])

_FRENCH_VOICES = [
    Voice(id="fr-FR-DeniseNeural", name="Denise (Female)"),
    Voice(id="fr-FR-EloiseNeural", name="Eloise (Female)"),
    Voice(id="fr-FR-HenriNeural", name="Henri (Male)"),
    Voice(id="fr-FR-VivienneMultilingualNeural", name="Vivienne Multilingual (Female)"),
    Voice(id="fr-FR-RemyMultilingualNeural", name="Remy Multilingual (Male)"),
]


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", text).strip("_")
    return slug or "word"


def get_translation_agent(request: Request) -> FrenchWordTranslationAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return FrenchWordTranslationAgent(
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


def get_anki_client(request: Request):
    return request.app.state.anki_client


@router.get("/voices", response_model=VoicesResponse)
async def list_voices() -> VoicesResponse:
    return VoicesResponse(voices=_FRENCH_VOICES)


@router.post("/generate", response_model=TranslationResult)
async def generate(
    body: GenerateRequest,
    agent: FrenchWordTranslationAgent = Depends(get_translation_agent),
) -> TranslationResult:
    try:
        return await agent.generate(word=body.word, cefr_level=body.cefr_level)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/audio", response_model=AudioResponse)
async def generate_audio(
    body: AudioRequest,
    agent: AudioAgent = Depends(get_audio_agent),
) -> AudioResponse:
    try:
        audio_b64 = await agent.synthesize(text=body.text, voice=body.voice)
        filename = f"{_slugify(body.text[:40])}.mp3"
        return AudioResponse(audio_base64=audio_b64, filename=filename)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/add-to-anki", response_model=AddToAnkiResponse)
async def add_to_anki(
    body: AddToAnkiRequest,
    anki_client=Depends(get_anki_client),
) -> AddToAnkiResponse:
    word_slug = _slugify(body.french_word)
    word_filename = f"{word_slug}.mp3"
    example_filename = f"{word_slug}_example.mp3"
    try:
        await anki_client.invoke(
            "storeMediaFile",
            filename=word_filename,
            data=body.french_word_audio_base64,
        )
        await anki_client.invoke(
            "storeMediaFile",
            filename=example_filename,
            data=body.example_audio_base64,
        )
        note_id = await anki_client.invoke(
            "addNote",
            note={
                "deckName": body.deck,
                "modelName": body.note_type,
                "fields": {
                    "french_word": body.french_word,
                    "russian_word": body.russian_word,
                    "example": body.example,
                    "french_word_audio": f"[sound:{word_filename}]",
                    "example_audio": f"[sound:{example_filename}]",
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

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_word_lookup_router.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/routers/word_lookup.py tests/test_word_lookup_router.py
git commit -m "feat: add word lookup router with generate, audio, and add-to-anki endpoints"
```

---

## Task 8: Wire Up main.py and Navigation

**Files:**
- Modify: `app/main.py`
- Modify: `static/components/menu.html`

- [ ] **Step 1: Replace app/main.py with the fully wired version**

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


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/decks")
async def decks() -> FileResponse:
    return FileResponse("static/decks.html")


@app.get("/word-lookup")
async def word_lookup() -> FileResponse:
    return FileResponse("static/word-lookup.html")


@app.get("/settings")
async def settings() -> FileResponse:
    return FileResponse("static/settings.html")
```

- [ ] **Step 2: Update navigation menu**

Replace `static/components/menu.html`:

```html
<nav>
    <a href="/">Home</a>
    <a href="/decks">Decks</a>
    <a href="/word-lookup">Word Lookup</a>
    <a href="/settings">Settings</a>
</nav>
```

- [ ] **Step 3: Run full test suite to confirm nothing is broken**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Start the dev server and verify the new routes respond**

```bash
uv run uvicorn app.main:app --reload
```

In another terminal:
```bash
curl -s http://localhost:8000/api/settings | python3 -m json.tool
```

Expected: JSON with `model`, `azure_region`, `openrouter_key_set`, etc.

```bash
curl -s http://localhost:8000/api/word-lookup/voices | python3 -m json.tool
```

Expected: JSON with a `voices` list of 5 French voices.

- [ ] **Step 5: Commit**

```bash
git add app/main.py static/components/menu.html
git commit -m "feat: wire word-lookup and settings routers into main app"
```

---

## Task 9: word-lookup.html

**Files:**
- Create: `static/word-lookup.html`

- [ ] **Step 1: Create static/word-lookup.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Word Lookup — Anki Helper</title>
    <style>
        body { font-family: sans-serif; max-width: 620px; margin: 2rem auto; padding: 0 1rem; }
        label { display: block; font-size: 0.75em; text-transform: uppercase; color: #888; margin-bottom: 0.2em; }
        input, select, textarea {
            width: 100%; box-sizing: border-box; padding: 0.5rem;
            border: 1px solid #ccc; border-radius: 4px; font-size: 1em; font-family: inherit;
        }
        textarea { resize: vertical; }
        button { padding: 0.5rem 1rem; border-radius: 4px; border: none; cursor: pointer; font-size: 1em; }
        .btn-primary { background: #4f8ef7; color: white; }
        .btn-secondary { background: #e5e7eb; color: #333; }
        .btn-success { background: #22c55e; color: white; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .banner { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 6px; padding: 0.75rem; margin-bottom: 1rem; color: #dc2626; display: none; }
        .eval-badge { border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 1rem; font-size: 0.9em; }
        .eval-valid { background: #f0fdf4; border: 1px solid #86efac; color: #15803d; }
        .eval-warning { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; }
        .result-section { margin-top: 1.5rem; display: none; }
        .field { margin-bottom: 1rem; }
        .audio-row { display: flex; gap: 0.5rem; align-items: center; margin-top: 0.3rem; }
        .audio-row audio { flex: 1; height: 36px; }
        .row { display: flex; gap: 0.75rem; }
        .row > * { flex: 1; }
        .inline-error { color: #dc2626; font-size: 0.85em; margin-top: 0.2rem; }
        .success-msg { color: #15803d; font-size: 0.9em; }
        audio { width: 100%; }
    </style>
</head>
<body>
    <div id="menu-container"></div>

    <div id="keys-banner" class="banner">
        API keys not configured. <a href="/settings">Go to Settings</a>.
    </div>

    <h1>French Word Lookup</h1>

    <div class="field">
        <label>French Word</label>
        <input type="text" id="word-input" placeholder="e.g. bonjour">
    </div>

    <div class="row" style="margin-bottom: 1rem;">
        <div>
            <label>CEFR Level</label>
            <select id="cefr-select">
                <option value="A1">A1</option>
                <option value="A2">A2</option>
                <option value="B1" selected>B1</option>
                <option value="B2">B2</option>
                <option value="C1">C1</option>
                <option value="C2">C2</option>
            </select>
        </div>
        <div>
            <label>Azure Voice</label>
            <select id="voice-select"></select>
        </div>
    </div>

    <button id="generate-btn" class="btn-primary" style="width:100%" disabled>⚡ Generate</button>
    <div id="generate-error" class="inline-error"></div>

    <div id="result-section" class="result-section">
        <div id="eval-badge" class="eval-badge"></div>

        <div class="field">
            <label>Translation (Russian)</label>
            <textarea id="translation" rows="2"></textarea>
        </div>

        <div class="field">
            <label>Example (French)</label>
            <textarea id="example" rows="3"></textarea>
        </div>

        <div class="field">
            <label>Word Audio</label>
            <div class="audio-row">
                <audio id="word-audio" controls></audio>
                <button class="btn-secondary" onclick="regenAudio('word')">↺ Re-generate</button>
            </div>
            <div id="word-audio-error" class="inline-error"></div>
        </div>

        <div class="field">
            <label>Example Audio</label>
            <div class="audio-row">
                <audio id="example-audio" controls></audio>
                <button class="btn-secondary" onclick="regenAudio('example')">↺ Re-generate</button>
            </div>
            <div id="example-audio-error" class="inline-error"></div>
        </div>

        <div class="row" style="align-items: flex-end; margin-bottom: 0.5rem;">
            <div>
                <label>Deck</label>
                <select id="deck-select"></select>
            </div>
            <div style="flex: 0; white-space: nowrap;">
                <button id="add-anki-btn" class="btn-success" disabled onclick="addToAnki()">+ Add to Anki</button>
            </div>
        </div>
        <div id="add-anki-status"></div>
    </div>

    <script src="/static/js/menu.js"></script>
    <script>
        const LS_CEFR  = 'anki_cefr';
        const LS_VOICE = 'anki_voice';
        const LS_DECK  = 'anki_deck';

        let wordAudioBase64    = null;
        let exampleAudioBase64 = null;
        let noteTypeName       = 'French-Russian';

        async function init() {
            // Load voices
            const vRes = await fetch('/api/word-lookup/voices');
            const { voices } = await vRes.json();
            const voiceSel = document.getElementById('voice-select');
            voices.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = v.name;
                voiceSel.appendChild(opt);
            });

            // Restore saved preferences
            const savedCefr  = localStorage.getItem(LS_CEFR);
            const savedVoice = localStorage.getItem(LS_VOICE);
            if (savedCefr)  document.getElementById('cefr-select').value = savedCefr;
            if (savedVoice) voiceSel.value = savedVoice;

            document.getElementById('cefr-select').addEventListener('change', e =>
                localStorage.setItem(LS_CEFR, e.target.value));
            voiceSel.addEventListener('change', e =>
                localStorage.setItem(LS_VOICE, e.target.value));

            // Check API keys
            const sRes     = await fetch('/api/settings');
            const settings = await sRes.json();
            noteTypeName   = settings.note_type;

            if (!settings.openrouter_key_set || !settings.azure_key_set) {
                document.getElementById('keys-banner').style.display = 'block';
            } else {
                document.getElementById('generate-btn').disabled = false;
            }

            // Load Anki decks
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
            } catch { /* Anki not running — deck select stays empty */ }
        }

        async function generate() {
            const word = document.getElementById('word-input').value.trim();
            if (!word) return;

            // Reset state
            wordAudioBase64 = null;
            exampleAudioBase64 = null;
            document.getElementById('add-anki-btn').disabled = true;
            document.getElementById('result-section').style.display = 'none';
            document.getElementById('generate-error').textContent = '';
            document.getElementById('word-audio').src = '';
            document.getElementById('example-audio').src = '';

            const btn = document.getElementById('generate-btn');
            btn.textContent = '⏳ Generating…';
            btn.disabled = true;

            try {
                const res = await fetch('/api/word-lookup/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        word,
                        cefr_level: document.getElementById('cefr-select').value,
                    }),
                });

                if (!res.ok) {
                    const { detail } = await res.json().catch(() => ({}));
                    document.getElementById('generate-error').textContent = detail ?? `Error ${res.status}`;
                    return;
                }

                const data = await res.json();
                document.getElementById('translation').value = data.russian_word;
                document.getElementById('example').value     = data.example;

                const badge = document.getElementById('eval-badge');
                badge.textContent = (data.is_valid ? '✓ ' : '⚠ ') + data.word_evaluation;
                badge.className   = 'eval-badge ' + (data.is_valid ? 'eval-valid' : 'eval-warning');

                document.getElementById('result-section').style.display = 'block';

                // Fire both audio requests concurrently
                const voice = document.getElementById('voice-select').value;
                await Promise.all([
                    generateAudio('word',    word,        voice),
                    generateAudio('example', data.example, voice),
                ]);
            } catch {
                document.getElementById('generate-error').textContent = 'Network error.';
            } finally {
                btn.textContent = '⚡ Generate';
                btn.disabled = false;
            }
        }

        async function generateAudio(type, text, voice) {
            const audioEl = document.getElementById(type + '-audio');
            const errEl   = document.getElementById(type + '-audio-error');
            errEl.textContent = '';

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

                if (type === 'word') wordAudioBase64    = audio_base64;
                else                 exampleAudioBase64 = audio_base64;
            } catch {
                errEl.textContent = 'Audio generation failed.';
            }

            updateAddButton();
        }

        function updateAddButton() {
            document.getElementById('add-anki-btn').disabled =
                !(wordAudioBase64 && exampleAudioBase64);
        }

        async function regenAudio(type) {
            const text = type === 'word'
                ? document.getElementById('word-input').value.trim()
                : document.getElementById('example').value.trim();
            const voice = document.getElementById('voice-select').value;
            if (!text) return;
            await generateAudio(type, text, voice);
        }

        async function addToAnki() {
            const statusEl = document.getElementById('add-anki-status');
            statusEl.textContent = '';
            document.getElementById('add-anki-btn').disabled = true;

            try {
                const res = await fetch('/api/word-lookup/add-to-anki', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        deck:                    document.getElementById('deck-select').value,
                        note_type:               noteTypeName,
                        french_word:             document.getElementById('word-input').value.trim(),
                        russian_word:            document.getElementById('translation').value,
                        example:                 document.getElementById('example').value,
                        french_word_audio_base64: wordAudioBase64,
                        example_audio_base64:    exampleAudioBase64,
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
                updateAddButton();
            }
        }

        document.getElementById('generate-btn').addEventListener('click', generate);
        document.getElementById('word-input').addEventListener('keydown', e => {
            if (e.key === 'Enter' && !document.getElementById('generate-btn').disabled) generate();
        });

        init();
    </script>
</body>
</html>
```

- [ ] **Step 2: Start the dev server and open the page**

```bash
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000/word-lookup in a browser.

- [ ] **Step 3: Verify the following manually**

- [ ] Page loads with Word Lookup in the nav
- [ ] If API keys are missing → banner appears and Generate is disabled
- [ ] After configuring keys in Settings → Generate is enabled
- [ ] Entering "bonjour" and clicking Generate → spinner → translation + example appear
- [ ] Both audio players show audio after generation
- [ ] Editing the example textarea and clicking Re-generate (example) → audio regenerates with edited text
- [ ] Changing voice and clicking Re-generate → new audio plays
- [ ] CEFR and voice persist across page reload (localStorage)
- [ ] Add to Anki is disabled until both audios are loaded
- [ ] Clicking Add to Anki (with Anki running) → "✓ Added to Anki!"

- [ ] **Step 4: Commit**

```bash
git add static/word-lookup.html
git commit -m "feat: add word-lookup.html frontend"
```

---

## Task 10: settings.html

**Files:**
- Create: `static/settings.html`

- [ ] **Step 1: Create static/settings.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings — Anki Helper</title>
    <style>
        body { font-family: sans-serif; max-width: 500px; margin: 2rem auto; padding: 0 1rem; }
        label { display: block; font-size: 0.75em; text-transform: uppercase; color: #888; margin-bottom: 0.2em; }
        input {
            width: 100%; box-sizing: border-box; padding: 0.5rem;
            border: 1px solid #ccc; border-radius: 4px; font-size: 1em; margin-bottom: 1rem;
        }
        button { padding: 0.5rem 1.5rem; border-radius: 4px; border: none; cursor: pointer; font-size: 1em; background: #4f8ef7; color: white; }
        .hint { font-size: 0.75em; color: #999; margin-top: -0.8rem; margin-bottom: 1rem; }
        .success-msg { color: #15803d; font-size: 0.9em; margin-left: 1rem; }
        .error-msg   { color: #dc2626; font-size: 0.9em; margin-left: 1rem; }
        h2 { margin-top: 2rem; font-size: 1em; text-transform: uppercase; color: #555; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
    </style>
</head>
<body>
    <div id="menu-container"></div>
    <h1>Settings</h1>
    <p style="font-size:0.9em;color:#666;">All values are saved to <code>.env.local</code> on the server. System environment variables take priority over saved values.</p>

    <h2>OpenRouter</h2>

    <label>API Key</label>
    <input type="password" id="openrouter-key" autocomplete="off" placeholder="sk-or-…">

    <label>Model</label>
    <input type="text" id="openrouter-model" placeholder="google/gemini-flash-1.5">
    <p class="hint">Default: google/gemini-flash-1.5. Browse models at openrouter.ai/models</p>

    <h2>Azure Text-to-Speech</h2>

    <label>API Key</label>
    <input type="password" id="azure-key" autocomplete="off" placeholder="your azure key">

    <label>Region</label>
    <input type="text" id="azure-region" placeholder="westeurope">
    <p class="hint">Find your region in the Azure portal under your Speech resource.</p>

    <h2>Anki</h2>

    <label>Note Type Name</label>
    <input type="text" id="note-type" placeholder="French-Russian">
    <p class="hint">Must exactly match the note type you created in Anki with fields: french_word, russian_word, example, french_word_audio, example_audio.</p>

    <div>
        <button onclick="saveSettings()">Save Settings</button>
        <span id="status-msg"></span>
    </div>

    <script src="/static/js/menu.js"></script>
    <script>
        async function loadSettings() {
            const res = await fetch('/api/settings');
            if (!res.ok) return;
            const s = await res.json();
            document.getElementById('openrouter-model').value = s.model;
            document.getElementById('azure-region').value     = s.azure_region;
            document.getElementById('note-type').value        = s.note_type;
            if (s.openrouter_key_set) document.getElementById('openrouter-key').placeholder = '••••• (already set — leave blank to keep)';
            if (s.azure_key_set)      document.getElementById('azure-key').placeholder      = '••••• (already set — leave blank to keep)';
        }

        async function saveSettings() {
            const statusEl = document.getElementById('status-msg');
            statusEl.textContent = '';

            const body = {};
            const orKey    = document.getElementById('openrouter-key').value.trim();
            const azKey    = document.getElementById('azure-key').value.trim();
            const model    = document.getElementById('openrouter-model').value.trim();
            const region   = document.getElementById('azure-region').value.trim();
            const noteType = document.getElementById('note-type').value.trim();

            if (orKey)    body.openrouter_api_key = orKey;
            if (azKey)    body.azure_api_key      = azKey;
            if (model)    body.model              = model;
            if (region)   body.azure_region       = region;
            if (noteType) body.note_type          = noteType;

            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (!res.ok) {
                    statusEl.className   = 'error-msg';
                    statusEl.textContent = 'Failed to save.';
                    return;
                }
                statusEl.className   = 'success-msg';
                statusEl.textContent = '✓ Saved to .env.local';
                document.getElementById('openrouter-key').value = '';
                document.getElementById('azure-key').value      = '';
                await loadSettings();
            } catch {
                statusEl.className   = 'error-msg';
                statusEl.textContent = 'Network error.';
            }
        }

        loadSettings();
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify in browser**

Open http://localhost:8000/settings.

- [ ] Page loads with Settings in the nav
- [ ] Current model and region are pre-filled from the server
- [ ] Key fields show "already set" placeholder if keys exist
- [ ] Entering a new key and clicking Save → "✓ Saved to .env.local"
- [ ] Key field clears after save; placeholder updates to "already set"
- [ ] Navigating to Word Lookup after saving keys → banner disappears, Generate is enabled

- [ ] **Step 3: Commit**

```bash
git add static/settings.html
git commit -m "feat: add settings.html frontend"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** ConfigManager ✓, FrenchWordTranslationAgent ✓, AudioAgent ✓, Settings router ✓, Word lookup router (generate, audio, add-to-anki, voices) ✓, editable translation/example ✓, grammar evaluation badge ✓, Re-generate audio ✓, deck dropdown with localStorage ✓, CEFR/voice localStorage ✓, API key check banner ✓, Add to Anki disabled until both audios ready ✓, server-side config file ✓, env var priority ✓
- [x] **Placeholders:** None — all steps have actual code
- [x] **Type consistency:** `TranslationResult` defined in Task 3 (schemas), used in Task 4 (agent) and Task 7 (router) with matching field names throughout. `get_translation_agent`, `get_audio_agent`, `get_anki_client` defined in Task 7 (router) and overridden in Task 7 (tests). `get_config` defined in Task 6 (router) and overridden in Task 6 (tests). `ConfigManager.save()` called with uppercase key names consistently.
