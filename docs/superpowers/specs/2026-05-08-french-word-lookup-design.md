# French Word Lookup Feature — Design Spec

**Date:** 2026-05-08

## Overview

A new screen in the Anki Helper app where the user types a French word and the app generates:

- Russian translation and a CEFR-level French example sentence (via OpenRouter LLM with structured output)
- An LLM grammar evaluation of the input word (informational, never blocks generation)
- Audio for the word and the example sentence independently (via Azure TTS)

Results are editable before the user adds them as a card to an Anki deck. CEFR level, Azure voice, and default deck are persisted in `localStorage`. API keys and model config are stored server-side in `.env.local`.

---

## Architecture

```
Browser
  word-lookup.html       settings.html
  └─ localStorage        └─ POST /api/settings
       cefr_level
       azure_voice
       default_deck

FastAPI
  routers/word_lookup.py     routers/settings.py
  POST /api/word-lookup/generate
  POST /api/word-lookup/audio
  POST /api/word-lookup/add-to-anki
  GET  /api/word-lookup/voices
  GET  /api/settings
  POST /api/settings

  app/agents/
    FrenchWordTranslationAgent   → OpenRouter (JSON mode, structured output)
    AudioAgent                   → Azure TTS REST API

  app/config.py  (ConfigManager)
    priority: system env vars → .env.local → hardcoded defaults

  app/anki_client.py  (existing)
    storeMediaFile, addNote, deckNames

External
  OpenRouter API   (default model: google/gemini-flash-1.5)
  Azure TTS REST   (fr-FR voices)
  Anki Connect     (localhost:8765, existing)
```

---

## Agents

### FrenchWordTranslationAgent

**Location:** `app/agents/french_word_translation_agent.py`

**Responsibilities:** call OpenRouter with JSON-mode structured output to produce a Russian translation, a French example sentence at the specified CEFR level, and an informational grammar evaluation of the input word.

**Constructor:** `__init__(self, api_key: str, model: str)`

**Method:** `async def generate(self, word: str, cefr_level: str) -> TranslationResult`

**Output model:**
```python
class TranslationResult(BaseModel):
    russian_word: str
    example: str          # French sentence at the specified CEFR level
    word_evaluation: str  # LLM note on spelling/grammar validity
    is_valid: bool        # drives green ✓ vs yellow ⚠ badge in UI
```

No FastAPI imports. Pure async class — instantiate directly in tests.

This agent is the first of a planned family. Future agents (`FrenchSentenceTranslationAgent`, `EnglishWordTranslationAgent`) follow the same shape (constructor + `generate` method, different prompt) and slot in without touching routers or config.

### AudioAgent

**Location:** `app/agents/audio_agent.py`

**Responsibilities:** call Azure TTS REST API to synthesize speech for any text+voice combination. Returns base64-encoded MP3. Stateless and reusable across all future translation agents.

**Constructor:** `__init__(self, api_key: str, region: str)`

**Method:** `async def synthesize(self, text: str, voice: str) -> str` (base64 MP3)

Azure TTS endpoint: `https://{region}.tts.speech.microsoft.com/cognitiveservices/v1`
Headers: `Ocp-Apim-Subscription-Key`, `Content-Type: application/ssml+xml`, `X-Microsoft-OutputFormat: audio-16khz-128kbitrate-mono-mp3`

---

## Endpoints

### `POST /api/word-lookup/generate`

```
in:  { word: str, cefr_level: str }
out: { russian_word: str, example: str, word_evaluation: str, is_valid: bool }
```

Calls `FrenchWordTranslationAgent.generate`. Returns 502 on OpenRouter error, 503 if keys not configured.

### `POST /api/word-lookup/audio`

```
in:  { text: str, voice: str }
out: { audio_base64: str, filename: str }
```

Calls `AudioAgent.synthesize`. The frontend fires two concurrent calls — one for the word, one for the example — after text generation completes. Returns 502 on Azure error. The `filename` in the response is for display only (e.g. audio player label); Anki media filenames are derived independently by the `add-to-anki` endpoint from `french_word`.

### `POST /api/word-lookup/add-to-anki`

```
in:  {
  deck: str,
  note_type: str,
  french_word: str,
  russian_word: str,
  example: str,
  french_word_audio_base64: str,
  example_audio_base64: str
}
out: { note_id: int }
```

1. Calls `anki_client.invoke("storeMediaFile", ...)` for each audio (base64 → Anki media collection).
2. Calls `anki_client.invoke("addNote", ...)` with fields mapping to the custom note type:
   `french_word`, `russian_word`, `example`, `french_word_audio` (`[sound:filename.mp3]`), `example_audio` (`[sound:filename.mp3]`).

Returns 400 if note type not found, 503 if Anki is not running.

### `GET /api/word-lookup/voices`

```
out: { voices: [{ id: str, name: str }] }
```

Returns a curated list of French Azure TTS voices (hardcoded — the list is stable). Used to populate the voice dropdown on the lookup page.

### `GET /api/settings`

```
out: {
  model: str,
  azure_region: str,
  openrouter_key_set: bool,
  azure_key_set: bool,
  note_type: str
}
```

Keys are never returned in plaintext — only their presence is indicated.

### `POST /api/settings`

```
in:  { model?: str, azure_region?: str, openrouter_api_key?: str, azure_api_key?: str, note_type?: str }
out: { ok: bool }
```

Writes provided values to `.env.local`. Unset fields are left unchanged.

---

## Config Management

**Location:** `app/config.py`

`ConfigManager` resolves values in priority order:
1. System environment variables (e.g. `OPENROUTER_API_KEY`)
2. `.env.local` file in the project root (same `KEY=VALUE` format)
3. Hardcoded defaults (model = `google/gemini-flash-1.5`, note_type = `French-Russian`)

`.env.local` is gitignored. The settings endpoint writes only to this file; it never touches actual env vars.

**Keys managed:**
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `AZURE_TTS_KEY`
- `AZURE_TTS_REGION`
- `NOTE_TYPE_NAME`

---

## Frontend UI Flow

### `word-lookup.html`

**Inputs (top of page, always visible):**
- French word — text input
- CEFR level — dropdown (A1–C2), value persisted in `localStorage`
- Azure voice — dropdown (from `/api/word-lookup/voices`), value persisted in `localStorage`
- Generate button

**On Generate click:**
1. `POST /api/word-lookup/generate` — awaited; shows inline spinner
2. On success: show evaluation badge (green ✓ or yellow ⚠), populate editable textareas for translation and example
3. Immediately after: fire two concurrent `POST /api/word-lookup/audio` calls — one for the word, one for the example
4. Each audio section shows its own spinner until its call resolves; on success replace with audio player (data URI) + Re-generate button

**Result area (shown after generation):**
- Evaluation badge (informational only)
- Translation textarea (editable)
- Example textarea (editable)
- Word audio: native `<audio>` element + Re-generate button
- Example audio: native `<audio>` element + Re-generate button
- Deck dropdown (populated from `/api/decks`, default persisted in `localStorage`)
- Add to Anki button

**Re-generate audio:** calls `POST /api/word-lookup/audio` with current voice selection and the current textarea content (so if the user edited the example, the re-generated audio uses the edited text).

**Add to Anki:** button is disabled until both audio clips have been successfully generated. Sends current textarea values + both audio base64 strings to `POST /api/word-lookup/add-to-anki`. On success: brief "Added!" confirmation. On error: inline message.

**Missing keys banner:** on page load, if `GET /api/settings` shows any key unset, show a top banner with a link to Settings. Generate button is disabled.

### `settings.html`

Fields:
- OpenRouter API key (password input, shows `••••` if already set)
- OpenRouter model (text input, default `google/gemini-flash-1.5`)
- Azure TTS API key (password input)
- Azure region (text input, default `westeurope`)
- Anki note type name (text input, default `French-Russian`)

Save button → `POST /api/settings`. Success shows inline confirmation.

---

## Anki Integration

The user manually creates a note type in Anki with exactly these fields (in order):
- `french_word`
- `russian_word`
- `example`
- `french_word_audio`
- `example_audio`

The note type name is configurable in Settings (default `French-Russian`). The app does not create or modify note types.

Audio files are stored in Anki's media collection via `storeMediaFile`. Filenames are derived from the word: `{word}.mp3` and `{word}_example.mp3` (slugified). The note fields `french_word_audio` and `example_audio` reference them as `[sound:filename.mp3]`.

---

## Error Handling

| Scenario | HTTP | UI |
|---|---|---|
| OpenRouter key not set | 503 | Banner on page load, Generate disabled |
| Azure key not set | 503 | Banner on page load, Generate disabled |
| OpenRouter API error | 502 | Inline error below Generate button |
| Azure TTS error (word) | 502 | Inline error in word audio section only |
| Azure TTS error (example) | 502 | Inline error in example audio section only |
| Anki not running | 503 | Inline error near Add to Anki button |
| Note type not found | 400 | Inline error with link to Settings |

Audio errors are isolated — a failure generating word audio does not affect the example audio section or the text results.

---

## Testing Strategy

Agents are plain classes with no FastAPI coupling — test directly:

```python
# tests/agents/test_french_word_translation_agent.py
agent = FrenchWordTranslationAgent(api_key="...", model="google/gemini-flash-1.5")
result = await agent.generate(word="bonjour", cefr_level="B1")
assert result.russian_word
assert result.example
assert isinstance(result.is_valid, bool)

# tests/agents/test_audio_agent.py
agent = AudioAgent(api_key="...", region="westeurope")
audio_b64 = await agent.synthesize(text="bonjour", voice="fr-FR-DeniseNeural")
assert len(base64.b64decode(audio_b64)) > 0
```

Router-level tests use FastAPI `TestClient` with agents injected as mocks to avoid hitting external APIs in CI.

---

## File Layout

```
app/
  agents/
    __init__.py
    french_word_translation_agent.py   (new)
    audio_agent.py                     (new)
  routers/
    word_lookup.py                     (new)
    settings.py                        (new)
    decks.py                           (existing)
  config.py                            (new)
  main.py                              (add new routers + /word-lookup route)
  anki_client.py                       (existing)
  schemas.py                           (existing, extend)
static/
  word-lookup.html                     (new)
  settings.html                        (new)
  index.html                           (existing, add nav links)
  decks.html                           (existing)
  js/
    menu.js                            (existing)
.env.local                             (gitignored, written by settings endpoint)
tests/
  agents/
    test_french_word_translation_agent.py  (new)
    test_audio_agent.py                    (new)
```
