# Pronunciation Practice — Translate to Russian Button

## Overview

Add a "Translate to Russian" button to the pronunciation practice card view. When clicked, it fetches a Russian translation of the current card text using the configured OpenRouter LLM and displays it in a panel below the card text. The translation is language-aware (French or English based on the selected practice language).

## Backend

### New agent: `app/agents/pronunciation_translation_agent.py`

A lightweight `PronunciationTranslationAgent` class:
- Constructor accepts `client: httpx.AsyncClient`, `api_key: str`, `model: str`
- Single async method `translate(text: str, language: str) -> str`
- System prompt: "Translate the given text to Russian. Respond only with a JSON object with key `russian_text`."
- User message includes the source language name (derived from the BCP-47 code, e.g. `fr-FR` → "French") so the LLM does not guess
- Calls OpenRouter `/api/v1/chat/completions` with `response_format: {type: json_object}`
- Returns the `russian_text` string from the parsed JSON response

### New schemas in `app/schemas.py`

```
PronunciationTranslateRequest:
  text: str
  language: str  # BCP-47 code, e.g. "fr-FR"

PronunciationTranslateResponse:
  russian_text: str
```

### New endpoint in `app/routers/pronunciation.py`

```
POST /api/pronunciation/translate
Request:  PronunciationTranslateRequest
Response: PronunciationTranslateResponse
```

- Uses the same `get_recommendations_agent`-style dependency that checks `config.openrouter_key_set` and raises 503 if not set
- Instantiates `PronunciationTranslationAgent` from request app state
- Returns `{russian_text: ...}`

## Frontend (`static/pronunciation.html`)

### New HTML (inserted immediately after `#pronounce-text`)

```html
<div style="display:flex; gap:0.5rem; margin-bottom:0.5rem;">
  <button id="translate-btn" class="btn-secondary btn-full">Translate to Russian</button>
</div>
<div id="translation-error" class="inline-error"></div>
<div id="translation-panel" style="display:none; ...">
  <p id="translation-text" style="..."></p>
</div>
```

### Behavior

- Button visible immediately when a card loads
- First click: button disabled, text changes to "Translating…", calls `POST /api/pronunciation/translate` with `{text: currentCardText, language: selectedLang}`
- On success: panel revealed with Russian text, button hidden
- On error: inline error shown below button, button re-enabled with "Retry" label
- On `loadCard()`: panel hidden, error cleared, button re-enabled and text reset to "Translate to Russian"
- No second fetch if translation already loaded for current card

## Data Flow

```
[Translate btn click]
  → POST /api/pronunciation/translate {text, language}
    → PronunciationTranslationAgent.translate(text, language)
      → OpenRouter LLM → {russian_text: "..."}
    → PronunciationTranslateResponse
  → #translation-panel revealed with russian_text
```

## Error Handling

- OpenRouter key not configured → 503, frontend shows inline error
- LLM returns malformed JSON → backend raises ValueError → 502, frontend shows inline error
- Network error → frontend catches and shows inline error
