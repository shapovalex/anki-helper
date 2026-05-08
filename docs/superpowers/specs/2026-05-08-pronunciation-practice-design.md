# Pronunciation Practice Page — Design Spec

**Date:** 2026-05-08  
**Status:** Approved

## Overview

A new page (`/pronunciation`) where the user practices pronouncing text from Anki due cards. The user selects a deck, text field, audio field, and language. Cards are shown one at a time; the user records their pronunciation (press-and-hold), receives detailed Azure Speech feedback, optionally requests LLM-generated tips, and rates the card with standard Anki ease buttons before moving to the next card.

---

## Architecture

### Approach

Server-side proxy: the browser captures audio via `MediaRecorder`, sends it as base64 to the FastAPI backend on button release, the backend calls the Azure Speech REST API with `PronunciationAssessment` config, and returns structured results. This matches the existing pattern (Azure TTS is already server-side) and keeps API keys secure.

### New Files

- `app/routers/pronunciation.py` — five API endpoints
- `app/services/pronunciation.py` — Azure Speech assessment + LLM recommendations logic
- `static/pronunciation.html` — frontend page
- Route and menu link added to existing `app/main.py` and `static/components/menu.html`

### Config

Reuses existing `AZURE_TTS_KEY` and `AZURE_TTS_REGION`. No new settings keys needed. No new settings page field needed.

---

## API Endpoints

### `GET /api/pronunciation/fields?deck=X`

Returns the field names available on cards in the given deck.

- Calls AnkiConnect `findCards` with query `deck:X` (any card, just to get structure)
- Calls `cardsInfo` on the first result
- Returns: `{fields: ["french_word", "russian_word", "example", ...]}`

### `GET /api/pronunciation/card?deck=X&field=Y&audio_field=Z`

Returns a random due card from the deck.

- Calls AnkiConnect `findCards` with query `"deck:X" is:due`
- Picks a random card ID
- Calls `cardsInfo` to get field values
- Parses `[sound:filename.mp3]` from the `audio_field` value
  - If found: calls `retrieveMediaFile` → returns base64 audio
  - If empty/no sound tag: returns `audio_base64: null` (frontend calls existing `/api/word-lookup/audio` with a default voice per language: `fr-FR-DeniseNeural` for French, `en-US-JennyNeural` for English)
- Returns: `{card_id: int, text: str, audio_base64: str | null}`

### `POST /api/pronunciation/assess`

Evaluates pronunciation against reference text.

- Body: `{audio_base64: str, reference_text: str, language: str}`
  - `language`: `"fr-FR"` or `"en-US"`
- Calls Azure Speech REST API:
  - Endpoint: `https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={language}&format=detailed`
  - Header `Ocp-Apim-Subscription-Key`: Azure TTS key
  - Header `Pronunciation-Assessment`: base64-encoded JSON `{"ReferenceText": "...", "GradingSystem": "HundredMark", "Granularity": "Phoneme", "EnableMiscue": true}`
  - Header `Content-Type`: `audio/webm;codecs=opus`
  - Body: decoded audio bytes
- Returns structured assessment:

```json
{
  "overall": {
    "accuracy": 85,
    "fluency": 90,
    "completeness": 95,
    "pron_score": 88
  },
  "recognized_text": "bonjour le monde",
  "words": [
    {
      "word": "bonjour",
      "accuracy": 72,
      "error_type": "Mispronunciation",
      "phonemes": [
        {"symbol": "b", "accuracy": 95},
        {"symbol": "ɔ̃", "accuracy": 42}
      ]
    }
  ]
}
```

### `POST /api/pronunciation/recommendations`

Generates LLM pronunciation tips for the worst-scoring phonemes.

- Body: `{reference_text: str, language: str, words: [...worst-scoring words with phonemes]}`
- Passes to LLM via OpenRouter with prompt asking for 2–3 specific, actionable pronunciation tips targeting the lowest-scoring phonemes
- Returns: `{tips: ["tip1", "tip2", "tip3"]}`

### `POST /api/pronunciation/answer`

Submits Anki card rating and advances to the next card.

- Body: `{card_id: int, ease: int}` — ease is 1 (Again), 2 (Hard), 3 (Good), 4 (Easy)
- Calls AnkiConnect `answerCard`
- Returns: `{ok: true}`

---

## Frontend UI & Interaction Flow

### Phase 1: Setup

Shown on page load until "Start Practicing" is clicked.

- **Deck** dropdown — populated from existing `GET /api/decks`
- **Text Field** dropdown — populated from `GET /api/pronunciation/fields?deck=X` after deck is selected
- **Audio Field** dropdown — same field list; the field expected to contain `[sound:...]` reference audio (falls back to TTS if empty)
- **Language** dropdown — static: French (`fr-FR`) / English (`en-US`)
- **"Start Practicing"** button

Error banners shown if Anki is unreachable or Azure key is not configured (with link to Settings).

### Phase 2: Card Practice

Shown after "Start Practicing" and after each card rating.

**Card display:**
- Large, centered text to pronounce
- Reference audio player (loads immediately; if card audio field is empty, frontend calls `/api/word-lookup/audio` with a default voice for the selected language)

**Recording:**
- Press-and-hold **"🎤 Hold to Record"** button — `MediaRecorder` (WebM/Opus) captures while held
- On release: audio sent to `/api/pronunciation/assess`
- Status indicator: idle / recording / evaluating…

**Results (shown after assessment returns):**
- Overall score badge always visible: `PronScore 88/100` with sub-scores (Accuracy, Fluency, Completeness)
- Word row — each word shown as a colored chip (green ≥80, yellow 50–79, red <50) with its accuracy score
- Click a word → expands to show its phoneme chips (IPA symbol + score, color-coded same scale)
- Worst-scoring word starts expanded by default
- `recognized_text` shown below if it differs from reference text ("Azure heard: …")

**Actions after assessment:**
- **"🎤 Record Again"** — clears results, allows another attempt on the same card
- **"Get Recommendations"** button — calls `/api/pronunciation/recommendations` async, shows 2–3 LLM tips below results once loaded
- **Anki rating buttons**: Again / Hard / Good / Easy — calls `/api/pronunciation/answer` then loads next card
- **"Skip"** link — moves to next card without submitting an Anki rating

### Phase 3: Empty Deck

If `findCards` returns no due cards: show message "No due cards in this deck." with option to return to setup.

---

## Error Handling

| Condition | Behavior |
|---|---|
| Anki not reachable | Banner: "Cannot reach Anki. Make sure Anki is running." |
| Azure key not set | Banner: "Azure key not configured." with link to Settings |
| No due cards | Phase 3 message shown |
| Assessment API error | Inline error below record button |
| Recommendations API error | Inline error below "Get Recommendations" button |

---

## Testing

- Unit tests for `pronunciation.py` service: mock Azure HTTP response, verify response parsing into the structured schema
- Unit tests for `recommendations` service: mock OpenRouter call, verify tips extraction
- Router-level tests: mock service layer, verify endpoint contracts (status codes, response shapes)
- No browser automation tests — manual verification of `MediaRecorder` flow and UI state transitions
