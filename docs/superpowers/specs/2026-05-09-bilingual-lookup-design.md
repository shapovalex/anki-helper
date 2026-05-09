# Bilingual Lookup (French + English) — Design Spec

Date: 2026-05-09

## Overview

Add English support to both Word Lookup and Sentence Lookup features. Each language gets its own dedicated pages in the navigation menu, its own backend agents (with independently editable prompts), its own Anki note type, and language-filtered Azure TTS voices.

## Approach

Full duplication per language. Each language has its own agent file, router, and HTML page — no shared abstraction between French and English. This is intentional: prompts for French and English need to be editable independently without shared indirection.

---

## New Files

### Backend

| File | Purpose |
|---|---|
| `app/agents/english_word_translation_agent.py` | `EnglishWordTranslationAgent` — English word → Russian. Has its own `_SYSTEM_PROMPT` editable independently of the French equivalent. Returns `TranslationResult` (same schema as French). |
| `app/agents/english_sentence_translation_agent.py` | `EnglishSentenceTranslationAgent` — English sentence → Russian. Has its own `_SYSTEM_PROMPT`. Returns `SentenceTranslationResult` (same schema as French). |
| `app/routers/english_word_lookup.py` | `/api/english-word-lookup/*` router. Mirrors `word_lookup.py`. Voices filtered to `en-*`. Uses `ENGLISH_NOTE_TYPE_NAME` config key. Anki note fields: `english_word`, `russian_word`, `example`, `english_word_audio`, `example_audio`. |
| `app/routers/english_sentence_lookup.py` | `/api/english-sentence-lookup/*` router. Mirrors `sentence_lookup.py`. Voices filtered to `en-*`. Uses `ENGLISH_SENTENCE_NOTE_TYPE_NAME` config key. Anki note fields: `english_sentence`, `russian_sentence`, `audio`. |

### Frontend

| File | Purpose |
|---|---|
| `static/english-word-lookup.html` | English word lookup page. Calls `/api/english-word-lookup/*`. Mirrors `word-lookup.html`. |
| `static/english-sentence-lookup.html` | English sentence lookup page. Calls `/api/english-sentence-lookup/*`. Mirrors `sentence-lookup.html`. |

---

## Modified Files

### `app/config.py`

Add two new config keys with defaults:

| Env var | Default |
|---|---|
| `ENGLISH_NOTE_TYPE_NAME` | `English-Russian` |
| `ENGLISH_SENTENCE_NOTE_TYPE_NAME` | `English-Russian-Sentence` |

Add to `_DEFAULTS`, `_MANAGED_KEYS`, and expose via two new properties: `english_note_type_name`, `english_sentence_note_type_name`.

### `app/schemas.py`

Add two new request schemas for adding English notes to Anki:

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

Extend `SettingsResponse` with `english_note_type: str` and `english_sentence_note_type: str`.

Extend `SettingsUpdateRequest` with `english_note_type: str | None = None` and `english_sentence_note_type: str | None = None`.

### `app/routers/settings.py`

Map the two new request fields to `ENGLISH_NOTE_TYPE_NAME` and `ENGLISH_SENTENCE_NOTE_TYPE_NAME` in the update handler, and include them in the GET response.

### `app/main.py`

Register `english_word_lookup.router` and `english_sentence_lookup.router`.

### `static/settings.html`

Add two new fields in the Anki section:

- **English Note Type Name** (id: `english-note-type`, placeholder: `English-Russian`)  
  Hint: fields must be `english_word`, `russian_word`, `example`, `english_word_audio`, `example_audio`
- **English Sentence Note Type Name** (id: `english-sentence-note-type`, placeholder: `English-Russian-Sentence`)  
  Hint: fields must be `english_sentence`, `russian_sentence`, `audio`

### `static/components/menu.html`

Replace current "Word Lookup" and "Sentence Lookup" entries with four entries:

```
Word Lookup (FR)      → /word-lookup
Word Lookup (EN)      → /english-word-lookup
Sentence Lookup (FR)  → /sentence-lookup
Sentence Lookup (EN)  → /english-sentence-lookup
```

Pronunciation, Settings, Help remain unchanged.

---

## Voice Filtering

`AudioAgent.list_voices()` returns all Azure voices. Each router's `/voices` endpoint filters the list before returning it:

- French routers: keep only voices where `id` starts with `fr-`
- English routers: keep only voices where `id` starts with `en-`

The existing French routers (`word_lookup.py`, `sentence_lookup.py`) are also updated to apply the `fr-` filter (currently they return all voices unfiltered).

---

## Anki Note Fields

| Feature | Anki field names |
|---|---|
| French word | `french_word`, `russian_word`, `example`, `french_word_audio`, `example_audio` |
| French sentence | `french_sentence`, `russian_sentence`, `audio` |
| English word | `english_word`, `russian_word`, `example`, `english_word_audio`, `example_audio` |
| English sentence | `english_sentence`, `russian_sentence`, `audio` |

The LLM response schemas (`TranslationResult`, `SentenceTranslationResult`) are reused as-is for English — they are language-agnostic.

---

## Config Defaults Summary

| Key | Default |
|---|---|
| `NOTE_TYPE_NAME` | `French-Russian` (existing) |
| `SENTENCE_NOTE_TYPE_NAME` | `French-Russian-Sentence` (existing) |
| `ENGLISH_NOTE_TYPE_NAME` | `English-Russian` (new) |
| `ENGLISH_SENTENCE_NOTE_TYPE_NAME` | `English-Russian-Sentence` (new) |

---

## Out of Scope

- No shared agent base class or abstraction between languages
- No URL-based language switching (`?lang=fr`)
- No third language support
- No changes to Pronunciation feature
