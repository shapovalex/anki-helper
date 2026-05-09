# French Sentence Lookup — Design Spec

**Date:** 2026-05-09

## Overview

Add a French Sentence Lookup feature that mirrors the existing Word Lookup flow. The user types a French sentence, the app generates a Russian translation and a grammar check via AI, synthesizes a single audio file via Azure TTS, then lets the user add the result to Anki as a note with three fields: `french_sentence`, `russian_sentence`, `audio`.

Additionally, fix the existing Word Lookup page so voices are fetched dynamically from Azure rather than being hardcoded.

---

## 1. AI Agent

**File:** `app/agents/french_sentence_translation_agent.py`

Mirrors `FrenchWordTranslationAgent`. Calls OpenRouter with a system prompt that instructs the model to respond with JSON only:

```
- russian_sentence: Russian translation of the input sentence
- sentence_evaluation: brief note on grammar and naturalness of the French sentence
- is_valid: true if the sentence is grammatically correct French, false otherwise
```

**New Pydantic model** in `app/schemas.py`:

```python
class SentenceTranslationResult(BaseModel):
    russian_sentence: str
    sentence_evaluation: str
    is_valid: bool
```

**New request model** in `app/schemas.py`:

```python
class SentenceGenerateRequest(BaseModel):
    sentence: str
```

---

## 2. Dynamic Azure Voices

**Affected files:** `app/agents/audio_agent.py`, `app/routers/word_lookup.py`, `app/routers/sentence_lookup.py`

`AudioAgent` gains a `list_voices(locale_prefix: str = "fr-")` method that calls:

```
GET https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list
Ocp-Apim-Subscription-Key: {key}
```

Filters results to voices where `Locale` starts with `locale_prefix`, maps each to `Voice(id=ShortName, name=DisplayName)`, sorted by `DisplayName`.

Both `GET /api/word-lookup/voices` and `GET /api/sentence-lookup/voices` call this method. Both return 503 if the Azure key is not configured (consistent with audio endpoints). The hardcoded `_FRENCH_VOICES` list in `word_lookup.py` is removed.

---

## 3. Sentence Lookup Router

**File:** `app/routers/sentence_lookup.py`

Prefix: `/api/sentence-lookup`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/voices` | Return French voices from Azure |
| POST | `/generate` | Body: `SentenceGenerateRequest`; returns `SentenceTranslationResult` |
| POST | `/add-to-anki` | Body: `AddSentenceToAnkiRequest`; stores one audio file and creates Anki note |

**New Pydantic model** in `app/schemas.py`:

```python
class AddSentenceToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    french_sentence: str = Field(min_length=1, max_length=500)
    russian_sentence: str
    audio_base64: str
```

The `add-to-anki` endpoint stores one media file (slugified from the first 40 chars of the sentence) and creates an Anki note with fields:

```python
{
    "french_sentence": body.french_sentence,
    "russian_sentence": body.russian_sentence,
    "audio": f"[sound:{filename}]",
}
```

Audio generation for the sentence reuses the existing `POST /api/word-lookup/audio` endpoint — no duplication needed.

---

## 4. Config

**File:** `app/config.py`

New key: `SENTENCE_NOTE_TYPE_NAME` (default: `"French-Russian-Sentence"`).

Exposed via `GET /api/settings` as a new field `sentence_note_type`. The `SettingsResponse` and `SettingsUpdateRequest` schemas are updated accordingly. The Settings page gains a second "Sentence Note Type Name" input field (below the existing word note type field) with hint text listing the expected fields: `french_sentence`, `russian_sentence`, `audio`.

---

## 5. Frontend Page

**File:** `static/sentence-lookup.html`

Mirrors `word-lookup.html` with these differences:

- Input is a `<textarea>` (not a single-line input) to accommodate full sentences
- No CEFR level selector
- Grammar evaluation badge (same `eval-badge` style: green for `is_valid=true`, yellow for false)
- Russian translation textarea (editable by user before adding)
- Single audio player with ↺ Re-generate button (calls `/api/word-lookup/audio`)
- Deck selector + "Add to Anki" button (calls `/api/sentence-lookup/add-to-anki`)
- Voice dropdown populated from `/api/sentence-lookup/voices`

The "Add to Anki" button is enabled only after audio has been generated.

---

## 6. Routing & Navigation

**File:** `app/main.py`

New route:

```python
@app.get("/sentence-lookup")
async def sentence_lookup() -> FileResponse:
    return FileResponse("static/sentence-lookup.html")
```

The router is included:

```python
from app.routers import sentence_lookup as sentence_lookup_router
app.include_router(sentence_lookup_router.router)
```

The navigation menu (`static/js/menu.js` or equivalent) gains a "Sentence Lookup" entry pointing to `/sentence-lookup`.

---

## 7. Error Handling

Follows existing patterns exactly:
- 503 if OpenRouter key not set (generate endpoint)
- 503 if Azure key not set (voices and audio endpoints)
- 502 on upstream HTTP errors (OpenRouter or Azure)
- 400 if Anki note type not found
- 503 if Anki is not reachable
