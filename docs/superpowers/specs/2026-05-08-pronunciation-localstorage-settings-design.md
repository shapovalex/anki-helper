# Pronunciation Screen — Per-Deck localStorage Settings

## Overview

Persist pronunciation setup selections in the browser's localStorage so users don't have to re-configure Text Field, Audio Field, and Language every time they visit the page or switch decks.

## Storage Schema

Two key patterns, all prefixed `pronunciation:`:

| Key | Value | Purpose |
|-----|-------|---------|
| `pronunciation:lastDeck` | `"French Vocab"` | Last selected deck name (global) |
| `pronunciation:deck:<deckName>` | `{"textField":"Front","audioField":"Audio","language":"fr-FR"}` | Per-deck field and language settings |

No backend changes. Pure frontend, all changes in `static/pronunciation.html`.

## Behavior

### Page load
1. Read `pronunciation:lastDeck` from localStorage.
2. If a value exists and matches an option in `#deck-select`, select it.
3. Call `loadFields()` for the selected deck, then restore per-deck settings (see below).

### After fields load (`loadFields`)
1. Read `pronunciation:deck:<deckName>` from localStorage.
2. For `textField`, `audioField`: if the saved value exists as an `<option>` in the respective select, select it; otherwise leave the first option selected.
3. For `language`: if the saved value exists as an `<option>` in `#language-select`, select it; otherwise leave unchanged.

### On deck change (`#deck-select` change event)
1. Write `pronunciation:lastDeck` = new deck name.
2. Call `loadFields()`, which restores per-deck settings as above.

### On "Start Practicing" (`startPracticing`)
1. Write `pronunciation:deck:<deckName>` = `{ textField, audioField, language }` using current select values.

## Error Handling

- If a saved field value no longer exists as an option (deck fields changed), silently fall back to the first available option. No user-visible error.
- If localStorage is unavailable (e.g., private browsing with storage blocked), catch the exception and skip save/restore silently.

## Scope

- One file changed: `static/pronunciation.html`
- No new endpoints, no schema migrations, no backend changes.
