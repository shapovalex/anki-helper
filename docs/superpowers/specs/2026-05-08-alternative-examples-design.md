# Alternative Examples Feature — Design Spec

**Date:** 2026-05-08

## Summary

When a user generates a word lookup, the LLM returns one primary example sentence and five alternative example sentences in the same API call. The primary example works exactly as today (audio generated immediately). The five alternatives appear as clickable buttons below the primary example field; clicking one replaces the primary example and re-generates its audio.

## Backend

### `app/schemas.py`

Add one field to `TranslationResult`:

```python
alternative_examples: list[str]
```

No changes to `GenerateRequest`, `AddToAnkiRequest`, or any router/service. The `/generate` endpoint already returns `TranslationResult` directly, so the new field flows through automatically.

### `app/agents/french_word_translation_agent.py`

Extend `_SYSTEM_PROMPT` to request `alternative_examples`:

- Key: `alternative_examples`
- Type: JSON array of exactly 5 strings
- Each string: a natural French sentence using the word, appropriate for the given CEFR level
- These are distinct alternatives to `example`, not repetitions

The existing `response_format: json_object` already handles structured output; no other changes to the agent.

## Frontend (`static/word-lookup.html`)

### New UI section

Below the primary "Example (French)" `<textarea>`, add an "Alternative Examples" section:

- Hidden on page load; shown when results arrive (alongside `#result-section`)
- Contains 5 full-width buttons, one per alternative, each showing the example text
- Styled consistently with existing secondary buttons

### Interaction

Clicking an alternative button:
1. Sets `#example` textarea value to that alternative's text
2. Calls `regenAudio('example')` to re-generate example audio with the current voice

### Data flow

In the `generate()` function, after a successful `/generate` response, populate the alternative example buttons from `data.alternative_examples` before showing the result section.

## Out of scope

- Audio pre-generation for the 5 alternatives (only primary gets audio)
- Saving alternatives to Anki (only the primary example field is sent)
- Persisting the chosen alternative across page reloads
