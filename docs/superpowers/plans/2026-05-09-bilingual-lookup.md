# Bilingual Lookup (French + English) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add English word lookup and sentence lookup pages (each with their own agent, router, Anki note type, and en-filtered voices) alongside the existing French pages, wired into the navigation menu.

**Architecture:** Full duplication per language — each language has its own agent file with independently editable system prompt, its own router, and its own HTML page. Voice filtering (`fr-*` / `en-*`) is applied in each router's `/voices` endpoint. French routers are also updated to apply `fr-*` filtering (currently unfiltered).

**Tech Stack:** Python 3.13, FastAPI, httpx, Pydantic v2, Azure TTS, OpenRouter, vanilla JS

---

## File Map

**Create:**
- `tests/__init__.py`
- `tests/test_config.py`
- `tests/test_schemas.py`
- `tests/test_voice_filtering.py`
- `app/agents/english_word_translation_agent.py`
- `app/agents/english_sentence_translation_agent.py`
- `app/routers/english_word_lookup.py`
- `app/routers/english_sentence_lookup.py`
- `static/english-word-lookup.html`
- `static/english-sentence-lookup.html`

**Modify:**
- `app/config.py` — add `ENGLISH_NOTE_TYPE_NAME`, `ENGLISH_SENTENCE_NOTE_TYPE_NAME`
- `app/schemas.py` — add 2 new request schemas, extend `SettingsResponse` + `SettingsUpdateRequest`
- `app/routers/settings.py` — expose 2 new config keys
- `app/routers/word_lookup.py` — filter voices to `fr-*`
- `app/routers/sentence_lookup.py` — filter voices to `fr-*`
- `app/main.py` — import + include 2 new routers, add 2 new page routes
- `static/settings.html` — add 2 new note type inputs
- `static/components/menu.html` — rename existing entries to (FR), add 2 EN entries

---

### Task 1: Extend config with English note type keys

**Files:**
- Modify: `app/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/__init__.py` (empty file).

Create `tests/test_config.py`:

```python
import pytest
from app.config import ConfigManager


def test_english_note_type_name_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ENGLISH_NOTE_TYPE_NAME", raising=False)
    config = ConfigManager()
    assert config.english_note_type_name == "English-Russian"


def test_english_sentence_note_type_name_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ENGLISH_SENTENCE_NOTE_TYPE_NAME", raising=False)
    config = ConfigManager()
    assert config.english_sentence_note_type_name == "English-Russian-Sentence"


def test_english_note_type_name_from_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENGLISH_NOTE_TYPE_NAME", "MyEnglish")
    config = ConfigManager()
    assert config.english_note_type_name == "MyEnglish"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `AttributeError` — `ConfigManager` has no attribute `english_note_type_name`

- [ ] **Step 3: Implement config changes**

In `app/config.py`, replace `_DEFAULTS` with:

```python
_DEFAULTS: dict[str, str] = {
    "OPENROUTER_MODEL": "google/gemini-flash-1.5",
    "AZURE_TTS_REGION": "westeurope",
    "NOTE_TYPE_NAME": "French-Russian",
    "SENTENCE_NOTE_TYPE_NAME": "French-Russian-Sentence",
    "ENGLISH_NOTE_TYPE_NAME": "English-Russian",
    "ENGLISH_SENTENCE_NOTE_TYPE_NAME": "English-Russian-Sentence",
}
```

Replace `_MANAGED_KEYS` with:

```python
_MANAGED_KEYS = {
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "AZURE_TTS_KEY",
    "AZURE_TTS_REGION",
    "NOTE_TYPE_NAME",
    "SENTENCE_NOTE_TYPE_NAME",
    "ENGLISH_NOTE_TYPE_NAME",
    "ENGLISH_SENTENCE_NOTE_TYPE_NAME",
}
```

Add two new properties after `sentence_note_type_name`:

```python
    @property
    def english_note_type_name(self) -> str:
        return self._data["ENGLISH_NOTE_TYPE_NAME"]

    @property
    def english_sentence_note_type_name(self) -> str:
        return self._data["ENGLISH_SENTENCE_NOTE_TYPE_NAME"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: add English note type config keys"
```

---

### Task 2: Extend schemas

**Files:**
- Modify: `app/schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from app.schemas import (
    AddEnglishWordToAnkiRequest,
    AddEnglishSentenceToAnkiRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)


def test_add_english_word_to_anki_request_valid():
    req = AddEnglishWordToAnkiRequest(
        deck="Default",
        note_type="English-Russian",
        english_word="hello",
        russian_word="привет",
        example="Hello, how are you?",
        english_word_audio_base64="abc123",
        example_audio_base64="def456",
    )
    assert req.english_word == "hello"


def test_add_english_word_to_anki_request_empty_word():
    with pytest.raises(ValidationError):
        AddEnglishWordToAnkiRequest(
            deck="Default",
            note_type="English-Russian",
            english_word="",
            russian_word="привет",
            example="Hello!",
            english_word_audio_base64="abc",
            example_audio_base64="def",
        )


def test_add_english_sentence_to_anki_request_valid():
    req = AddEnglishSentenceToAnkiRequest(
        deck="Default",
        note_type="English-Russian-Sentence",
        english_sentence="How are you?",
        russian_sentence="Как дела?",
        audio_base64="abc123",
    )
    assert req.english_sentence == "How are you?"


def test_settings_response_includes_english_fields():
    s = SettingsResponse(
        model="gpt-4",
        azure_region="westeurope",
        openrouter_key_set=True,
        azure_key_set=True,
        note_type="French-Russian",
        sentence_note_type="French-Russian-Sentence",
        english_note_type="English-Russian",
        english_sentence_note_type="English-Russian-Sentence",
    )
    assert s.english_note_type == "English-Russian"
    assert s.english_sentence_note_type == "English-Russian-Sentence"


def test_settings_update_request_english_fields():
    req = SettingsUpdateRequest(
        english_note_type="My-English",
        english_sentence_note_type="My-English-Sentence",
    )
    assert req.english_note_type == "My-English"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_schemas.py -v
```

Expected: `ImportError` — cannot import `AddEnglishWordToAnkiRequest`

- [ ] **Step 3: Add new schemas and extend existing ones**

In `app/schemas.py`, add after `AddSentenceToAnkiRequest`:

```python
class AddEnglishWordToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    english_word: str = Field(min_length=1, max_length=100)
    russian_word: str
    example: str
    english_word_audio_base64: str
    example_audio_base64: str


class AddEnglishSentenceToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    english_sentence: str = Field(min_length=1, max_length=500)
    russian_sentence: str
    audio_base64: str
```

Replace `SettingsResponse` with:

```python
class SettingsResponse(BaseModel):
    model: str
    azure_region: str
    openrouter_key_set: bool
    azure_key_set: bool
    note_type: str
    sentence_note_type: str
    english_note_type: str
    english_sentence_note_type: str
```

Replace `SettingsUpdateRequest` with:

```python
class SettingsUpdateRequest(BaseModel):
    model: str | None = Field(default=None, min_length=1)
    azure_region: str | None = Field(default=None, min_length=1)
    openrouter_api_key: str | None = Field(default=None, min_length=1)
    azure_api_key: str | None = Field(default=None, min_length=1)
    note_type: str | None = Field(default=None, min_length=1)
    sentence_note_type: str | None = Field(default=None, min_length=1)
    english_note_type: str | None = Field(default=None, min_length=1)
    english_sentence_note_type: str | None = Field(default=None, min_length=1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_schemas.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py tests/test_schemas.py
git commit -m "feat: add English Anki request schemas and extend settings schemas"
```

---

### Task 3: English word translation agent

**Files:**
- Create: `app/agents/english_word_translation_agent.py`

- [ ] **Step 1: Create the agent**

Create `app/agents/english_word_translation_agent.py`:

```python
import json
import httpx
from pydantic import ValidationError
from app.schemas import TranslationResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are an English language expert. When given an English word and a CEFR level, "
    "respond ONLY with a JSON object (no markdown) with exactly these keys:\n"
    "- russian_word: Russian translation of the word\n"
    "- example: a natural English sentence using the word, appropriate for the CEFR level\n"
    "- alternative_examples: a JSON array of exactly 5 additional natural English sentences "
    "using the word, each appropriate for the CEFR level and distinct from 'example'\n"
    "- word_evaluation: brief note on whether the word is correctly spelled and valid English\n"
    "- is_valid: true if the word is a real, correctly spelled English word, false otherwise"
)


class EnglishWordTranslationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def generate(self, word: str, cefr_level: str) -> TranslationResult:
        prompt = (
            f"English word: {word}\n"
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
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenRouter returned non-JSON content: {content!r}") from exc
        try:
            return TranslationResult(**data)
        except ValidationError as exc:
            raise ValueError(f"OpenRouter response missing required fields: {exc}") from exc
```

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from app.agents.english_word_translation_agent import EnglishWordTranslationAgent; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/agents/english_word_translation_agent.py
git commit -m "feat: add EnglishWordTranslationAgent"
```

---

### Task 4: English sentence translation agent

**Files:**
- Create: `app/agents/english_sentence_translation_agent.py`

- [ ] **Step 1: Create the agent**

Create `app/agents/english_sentence_translation_agent.py`:

```python
import json
import httpx
from pydantic import ValidationError
from app.schemas import SentenceTranslationResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are an English language expert. When given an English sentence, "
    "respond ONLY with a JSON object (no markdown) with exactly these keys:\n"
    "- russian_sentence: Russian translation of the sentence\n"
    "- sentence_evaluation: brief note on the grammar and naturalness of the English sentence\n"
    "- is_valid: true if the sentence is grammatically correct English, false otherwise"
)


class EnglishSentenceTranslationAgent:
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

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from app.agents.english_sentence_translation_agent import EnglishSentenceTranslationAgent; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/agents/english_sentence_translation_agent.py
git commit -m "feat: add EnglishSentenceTranslationAgent"
```

---

### Task 5: Voice filtering tests

**Files:**
- Create: `tests/test_voice_filtering.py`

The `_filter_voices` helper will live in each router. Test the logic in isolation here.

- [ ] **Step 1: Write the tests**

Create `tests/test_voice_filtering.py`:

```python
from app.schemas import Voice


def _filter_voices(voices: list[Voice], lang_prefix: str) -> list[Voice]:
    return [v for v in voices if v.id.startswith(lang_prefix)]


def test_filter_french_voices():
    all_voices = [
        Voice(id="fr-FR-DeniseNeural", name="Denise"),
        Voice(id="en-US-JennyNeural", name="Jenny"),
        Voice(id="fr-CA-SylvieNeural", name="Sylvie"),
        Voice(id="de-DE-KatjaNeural", name="Katja"),
    ]
    result = _filter_voices(all_voices, "fr-")
    assert [v.id for v in result] == ["fr-FR-DeniseNeural", "fr-CA-SylvieNeural"]


def test_filter_english_voices():
    all_voices = [
        Voice(id="fr-FR-DeniseNeural", name="Denise"),
        Voice(id="en-US-JennyNeural", name="Jenny"),
        Voice(id="en-GB-LibbyNeural", name="Libby"),
        Voice(id="de-DE-KatjaNeural", name="Katja"),
    ]
    result = _filter_voices(all_voices, "en-")
    assert [v.id for v in result] == ["en-US-JennyNeural", "en-GB-LibbyNeural"]


def test_filter_returns_empty_when_none_match():
    all_voices = [Voice(id="de-DE-KatjaNeural", name="Katja")]
    result = _filter_voices(all_voices, "fr-")
    assert result == []
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
uv run pytest tests/test_voice_filtering.py -v
```

Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_voice_filtering.py
git commit -m "test: add voice filtering tests"
```

---

### Task 6: English word lookup router

**Files:**
- Create: `app/routers/english_word_lookup.py`

- [ ] **Step 1: Create the router**

Create `app/routers/english_word_lookup.py`:

```python
import logging
import re
import unicodedata
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.audio_agent import AudioAgent
from app.agents.english_word_translation_agent import EnglishWordTranslationAgent
from app.anki_client import AnkiClient, AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    AddEnglishWordToAnkiRequest,
    AddToAnkiResponse,
    AudioRequest,
    AudioResponse,
    GenerateRequest,
    TranslationResult,
    Voice,
    VoicesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/english-word-lookup", tags=["english-word-lookup"])


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", text).strip("_")
    return slug or "word"


def _filter_voices(voices: list[Voice], lang_prefix: str) -> list[Voice]:
    return [v for v in voices if v.id.startswith(lang_prefix)]


def get_translation_agent(request: Request) -> EnglishWordTranslationAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return EnglishWordTranslationAgent(
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
        return VoicesResponse(voices=_filter_voices(voices, "en-"))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Azure TTS.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Azure TTS timed out.")


@router.post("/generate", response_model=TranslationResult)
async def generate(
    body: GenerateRequest,
    agent: EnglishWordTranslationAgent = Depends(get_translation_agent),
) -> TranslationResult:
    try:
        return await agent.generate(word=body.word, cefr_level=body.cefr_level)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Unexpected error in generate endpoint")
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
        logger.exception("Unexpected error in generate_audio endpoint")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/add-to-anki", response_model=AddToAnkiResponse)
async def add_to_anki(
    body: AddEnglishWordToAnkiRequest,
    anki_client=Depends(get_anki_client),
) -> AddToAnkiResponse:
    word_slug = _slugify(body.english_word)
    word_filename = f"{word_slug}.mp3"
    example_filename = f"{word_slug}_example.mp3"
    try:
        await anki_client.invoke(
            "storeMediaFile",
            filename=word_filename,
            data=body.english_word_audio_base64,
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
                    "english_word": body.english_word,
                    "russian_word": body.russian_word,
                    "example": body.example,
                    "english_word_audio": f"[sound:{word_filename}]",
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

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from app.routers.english_word_lookup import router; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/routers/english_word_lookup.py
git commit -m "feat: add English word lookup router"
```

---

### Task 7: English sentence lookup router

**Files:**
- Create: `app/routers/english_sentence_lookup.py`

- [ ] **Step 1: Create the router**

Create `app/routers/english_sentence_lookup.py`:

```python
import logging
import re
import unicodedata
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.audio_agent import AudioAgent
from app.agents.english_sentence_translation_agent import EnglishSentenceTranslationAgent
from app.anki_client import AnkiClient, AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    AddEnglishSentenceToAnkiRequest,
    AddToAnkiResponse,
    SentenceGenerateRequest,
    SentenceTranslationResult,
    Voice,
    VoicesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/english-sentence-lookup", tags=["english-sentence-lookup"])


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", text).strip("_")
    return slug or "sentence"


def _filter_voices(voices: list[Voice], lang_prefix: str) -> list[Voice]:
    return [v for v in voices if v.id.startswith(lang_prefix)]


def get_translation_agent(request: Request) -> EnglishSentenceTranslationAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return EnglishSentenceTranslationAgent(
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
        return VoicesResponse(voices=_filter_voices(voices, "en-"))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Azure TTS.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Azure TTS timed out.")


@router.post("/generate", response_model=SentenceTranslationResult)
async def generate(
    body: SentenceGenerateRequest,
    agent: EnglishSentenceTranslationAgent = Depends(get_translation_agent),
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
    body: AddEnglishSentenceToAnkiRequest,
    anki_client=Depends(get_anki_client),
) -> AddToAnkiResponse:
    filename = f"{_slugify(body.english_sentence[:40])}.mp3"
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
                    "english_sentence": body.english_sentence,
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

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from app.routers.english_sentence_lookup import router; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/routers/english_sentence_lookup.py
git commit -m "feat: add English sentence lookup router"
```

---

### Task 8: Wire up new routers and page routes in main.py

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add imports and router registrations**

In `app/main.py`, add two imports after the existing router imports:

```python
from app.routers import english_word_lookup as english_word_lookup_router
from app.routers import english_sentence_lookup as english_sentence_lookup_router
```

Add two `include_router` calls after the existing ones:

```python
app.include_router(english_word_lookup_router.router)
app.include_router(english_sentence_lookup_router.router)
```

Add two page routes after the existing `/sentence-lookup` route:

```python
@app.get("/english-word-lookup")
async def english_word_lookup() -> FileResponse:
    return FileResponse("static/english-word-lookup.html")


@app.get("/english-sentence-lookup")
async def english_sentence_lookup() -> FileResponse:
    return FileResponse("static/english-sentence-lookup.html")
```

- [ ] **Step 2: Verify the app imports cleanly**

```bash
uv run python -c "from app.main import app; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: register English lookup routers and page routes"
```

---

### Task 9: Update settings router to expose English config keys

**Files:**
- Modify: `app/routers/settings.py`

- [ ] **Step 1: Update get_settings to include English fields**

In `app/routers/settings.py`, replace the `get_settings` handler body:

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
        english_note_type=config.english_note_type_name,
        english_sentence_note_type=config.english_sentence_note_type_name,
    )
```

- [ ] **Step 2: Update update_settings to handle English fields**

In the `update_settings` handler, add after the `sentence_note_type` block:

```python
    if body.english_note_type is not None:
        updates["ENGLISH_NOTE_TYPE_NAME"] = body.english_note_type
    if body.english_sentence_note_type is not None:
        updates["ENGLISH_SENTENCE_NOTE_TYPE_NAME"] = body.english_sentence_note_type
```

- [ ] **Step 3: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add app/routers/settings.py
git commit -m "feat: expose English note type keys in settings router"
```

---

### Task 10: Fix voice filtering on existing French routers

**Files:**
- Modify: `app/routers/word_lookup.py`
- Modify: `app/routers/sentence_lookup.py`

- [ ] **Step 1: Update word_lookup.py**

In `app/routers/word_lookup.py`, add `Voice` to the imports from `app.schemas`:

```python
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
```

Add after the `_slugify` function:

```python
def _filter_voices(voices: list[Voice], lang_prefix: str) -> list[Voice]:
    return [v for v in voices if v.id.startswith(lang_prefix)]
```

Replace the body of the `list_voices` endpoint:

```python
@router.get("/voices", response_model=VoicesResponse)
async def list_voices(
    agent: AudioAgent = Depends(get_audio_agent),
) -> VoicesResponse:
    try:
        voices = await agent.list_voices()
        return VoicesResponse(voices=_filter_voices(voices, "fr-"))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Azure TTS.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Azure TTS timed out.")
```

- [ ] **Step 2: Update sentence_lookup.py**

In `app/routers/sentence_lookup.py`, add `Voice` to the imports from `app.schemas`:

```python
from app.schemas import (
    AddSentenceToAnkiRequest,
    AddToAnkiResponse,
    SentenceGenerateRequest,
    SentenceTranslationResult,
    Voice,
    VoicesResponse,
)
```

Add after the `_slugify` function:

```python
def _filter_voices(voices: list[Voice], lang_prefix: str) -> list[Voice]:
    return [v for v in voices if v.id.startswith(lang_prefix)]
```

Replace the body of the `list_voices` endpoint:

```python
@router.get("/voices", response_model=VoicesResponse)
async def list_voices(
    agent: AudioAgent = Depends(get_audio_agent),
) -> VoicesResponse:
    try:
        voices = await agent.list_voices()
        return VoicesResponse(voices=_filter_voices(voices, "fr-"))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Azure TTS.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Azure TTS timed out.")
```

- [ ] **Step 3: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add app/routers/word_lookup.py app/routers/sentence_lookup.py
git commit -m "fix: filter voices to fr-* in French word and sentence lookup routers"
```

---

### Task 11: Update settings HTML

**Files:**
- Modify: `static/settings.html`

- [ ] **Step 1: Add English note type inputs**

In `static/settings.html`, after the closing `</div>` of the Sentence Note Type Name field (line 55), add:

```html
        <div class="field">
            <label>English Note Type Name</label>
            <input type="text" id="english-note-type" placeholder="English-Russian">
            <p class="hint">Must exactly match the note type in Anki with fields: english_word, russian_word, example, english_word_audio, example_audio.</p>
        </div>

        <div class="field">
            <label>English Sentence Note Type Name</label>
            <input type="text" id="english-sentence-note-type" placeholder="English-Russian-Sentence">
            <p class="hint">Must exactly match the note type in Anki with fields: english_sentence, russian_sentence, audio.</p>
        </div>
```

- [ ] **Step 2: Update loadSettings() to populate English fields**

In the `loadSettings` function, after `document.getElementById('sentence-note-type').value = s.sentence_note_type;`, add:

```javascript
            document.getElementById('english-note-type').value = s.english_note_type;
            document.getElementById('english-sentence-note-type').value = s.english_sentence_note_type;
```

- [ ] **Step 3: Update saveSettings() to read and send English fields**

After `const sentenceNoteType = document.getElementById('sentence-note-type').value.trim();`, add:

```javascript
            const englishNoteType = document.getElementById('english-note-type').value.trim();
            const englishSentenceNoteType = document.getElementById('english-sentence-note-type').value.trim();
```

After `if (sentenceNoteType) body.sentence_note_type = sentenceNoteType;`, add:

```javascript
            if (englishNoteType) body.english_note_type = englishNoteType;
            if (englishSentenceNoteType) body.english_sentence_note_type = englishSentenceNoteType;
```

- [ ] **Step 4: Commit**

```bash
git add static/settings.html
git commit -m "feat: add English note type fields to settings page"
```

---

### Task 12: English word lookup HTML page

**Files:**
- Create: `static/english-word-lookup.html`

- [ ] **Step 1: Create the page**

Create `static/english-word-lookup.html` with this exact content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Word Lookup (EN) — Anki Helper</title>
    <link rel="stylesheet" href="/static/css/theme.css">
</head>
<body>
    <div id="menu-container"></div>
    <main class="page">
        <div class="page-header">
            <h1 class="page-title">Word Lookup (EN)</h1>
            <p class="page-subtitle">Generate translation, example, and audio for an English word.</p>
        </div>

        <div id="keys-banner" class="banner banner-error">
            API keys not configured. <a href="/settings">Go to Settings →</a>
        </div>

        <div class="field">
            <label>English Word</label>
            <input type="text" id="word-input" placeholder="e.g. serendipity" autocomplete="off">
        </div>

        <div class="row" style="margin-bottom: 1.25rem;">
            <div class="field" style="margin-bottom: 0;">
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
            <div class="field" style="margin-bottom: 0;">
                <label>Azure Voice</label>
                <select id="voice-select"></select>
            </div>
        </div>

        <button id="generate-btn" class="btn-primary btn-full" disabled>⚡ Generate</button>
        <div id="generate-error" class="inline-error"></div>

        <div id="result-section" class="result-section">
            <div id="eval-badge" class="eval-badge"></div>

            <div class="field">
                <label>Translation (Russian)</label>
                <textarea id="translation" rows="2"></textarea>
            </div>

            <div class="field">
                <label>Example (English)</label>
                <textarea id="example" rows="3"></textarea>
            </div>

            <div id="alt-examples-section" class="field" style="display:none;">
                <label>Alternative Examples</label>
                <div id="alt-examples-list"></div>
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
        const LS_CEFR  = 'anki_en_cefr';
        const LS_VOICE = 'anki_en_voice';
        const LS_DECK  = 'anki_en_deck';

        let wordAudioBase64    = null;
        let exampleAudioBase64 = null;
        let noteTypeName       = 'English-Russian';

        async function init() {
            const vRes = await fetch('/api/english-word-lookup/voices');
            const { voices } = await vRes.json();
            const voiceSel = document.getElementById('voice-select');
            voices.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = v.name;
                voiceSel.appendChild(opt);
            });

            const savedCefr  = localStorage.getItem(LS_CEFR);
            const savedVoice = localStorage.getItem(LS_VOICE);
            if (savedCefr)  document.getElementById('cefr-select').value = savedCefr;
            if (savedVoice) voiceSel.value = savedVoice;

            document.getElementById('cefr-select').addEventListener('change', e =>
                localStorage.setItem(LS_CEFR, e.target.value));
            voiceSel.addEventListener('change', e =>
                localStorage.setItem(LS_VOICE, e.target.value));

            const sRes     = await fetch('/api/settings');
            const settings = await sRes.json();
            noteTypeName   = settings.english_note_type;

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
            const word = document.getElementById('word-input').value.trim();
            if (!word) return;

            wordAudioBase64    = null;
            exampleAudioBase64 = null;
            document.getElementById('add-anki-btn').disabled = true;
            document.getElementById('result-section').style.display = 'none';
            document.getElementById('alt-examples-section').style.display = 'none';
            document.getElementById('generate-error').textContent = '';
            document.getElementById('word-audio').src    = '';
            document.getElementById('example-audio').src = '';

            const btn = document.getElementById('generate-btn');
            btn.textContent = '⏳ Generating…';
            btn.disabled    = true;

            try {
                const res = await fetch('/api/english-word-lookup/generate', {
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

                const altList = document.getElementById('alt-examples-list');
                altList.innerHTML = '';
                (data.alternative_examples || []).forEach(alt => {
                    const btn = document.createElement('button');
                    btn.className = 'btn-secondary btn-full';
                    btn.style.cssText = 'text-align:left; margin-bottom:0.5rem; white-space:normal; height:auto; padding:0.5rem 0.75rem;';
                    btn.textContent = alt;
                    btn.addEventListener('click', () => {
                        document.getElementById('example').value = alt;
                        regenAudio('example');
                    });
                    altList.appendChild(btn);
                });
                document.getElementById('alt-examples-section').style.display = 'block';

                const badge = document.getElementById('eval-badge');
                badge.textContent = (data.is_valid ? '✓ ' : '⚠ ') + data.word_evaluation;
                badge.className   = 'eval-badge ' + (data.is_valid ? 'eval-valid' : 'eval-warning');

                document.getElementById('result-section').style.display = 'block';

                const voice = document.getElementById('voice-select').value;
                await Promise.all([
                    generateAudio('word',    word,         voice),
                    generateAudio('example', data.example, voice),
                ]);
            } catch {
                document.getElementById('generate-error').textContent = 'Network error.';
            } finally {
                btn.textContent = '⚡ Generate';
                btn.disabled    = false;
            }
        }

        async function generateAudio(type, text, voice) {
            const audioEl = document.getElementById(type + '-audio');
            const errEl   = document.getElementById(type + '-audio-error');
            errEl.textContent = '';

            try {
                const res = await fetch('/api/english-word-lookup/audio', {
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
                const res = await fetch('/api/english-word-lookup/add-to-anki', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        deck:                      document.getElementById('deck-select').value,
                        note_type:                 noteTypeName,
                        english_word:              document.getElementById('word-input').value.trim(),
                        russian_word:              document.getElementById('translation').value,
                        example:                   document.getElementById('example').value,
                        english_word_audio_base64: wordAudioBase64,
                        example_audio_base64:      exampleAudioBase64,
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

- [ ] **Step 2: Commit**

```bash
git add static/english-word-lookup.html
git commit -m "feat: add English word lookup HTML page"
```

---

### Task 13: English sentence lookup HTML page

**Files:**
- Create: `static/english-sentence-lookup.html`

- [ ] **Step 1: Create the page**

Create `static/english-sentence-lookup.html` with this exact content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentence Lookup (EN) — Anki Helper</title>
    <link rel="stylesheet" href="/static/css/theme.css">
</head>
<body>
    <div id="menu-container"></div>
    <main class="page">
        <div class="page-header">
            <h1 class="page-title">Sentence Lookup (EN)</h1>
            <p class="page-subtitle">Translate an English sentence and generate audio for Anki.</p>
        </div>

        <div id="keys-banner" class="banner banner-error" style="display:none;">
            API keys not configured. <a href="/settings">Go to Settings →</a>
        </div>

        <div class="field">
            <label>English Sentence</label>
            <textarea id="sentence-input" rows="3" placeholder="e.g. The early bird catches the worm." autocomplete="off"></textarea>
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
        const LS_VOICE = 'anki_en_sentence_voice';
        const LS_DECK  = 'anki_en_sentence_deck';

        let audioBase64  = null;
        let noteTypeName = 'English-Russian-Sentence';

        async function init() {
            const vRes = await fetch('/api/english-sentence-lookup/voices');
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
            noteTypeName   = settings.english_sentence_note_type;

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
                const res = await fetch('/api/english-sentence-lookup/generate', {
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
                const res = await fetch('/api/english-sentence-lookup/audio', {
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
                const res = await fetch('/api/english-sentence-lookup/add-to-anki', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        deck:             document.getElementById('deck-select').value,
                        note_type:        noteTypeName,
                        english_sentence: document.getElementById('sentence-input').value.trim(),
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

- [ ] **Step 2: Commit**

```bash
git add static/english-sentence-lookup.html
git commit -m "feat: add English sentence lookup HTML page"
```

---

### Task 14: Update navigation menu

**Files:**
- Modify: `static/components/menu.html`

- [ ] **Step 1: Update menu entries**

Replace the entire contents of `static/components/menu.html` with:

```html
<nav>
    <a href="/" class="nav-brand">Anki Helper</a>
    <div class="nav-links">
        <a href="/">Home</a>
        <a href="/word-lookup">Word Lookup (FR)</a>
        <a href="/english-word-lookup">Word Lookup (EN)</a>
        <a href="/sentence-lookup">Sentence Lookup (FR)</a>
        <a href="/english-sentence-lookup">Sentence Lookup (EN)</a>
        <a href="/pronunciation">Pronunciation</a>
        <a href="/settings">Settings</a>
        <a href="/help">Help</a>
    </div>
</nav>
```

- [ ] **Step 2: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add static/components/menu.html
git commit -m "feat: add English lookup entries to navigation menu"
```
