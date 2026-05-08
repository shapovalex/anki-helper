# Pronunciation localStorage Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist pronunciation setup selections (deck, text field, audio field, language) in localStorage so they survive page reloads, with per-deck memory for field and language choices.

**Architecture:** All changes are pure frontend JavaScript inside `static/pronunciation.html`. Two localStorage key patterns are used: a global `pronunciation:lastDeck` key for the last-selected deck, and per-deck keys `pronunciation:deck:<deckName>` storing a JSON object with `{textField, audioField, language}`. On page load the last deck is pre-selected; on deck change the saved settings for that deck are restored into the selects.

**Tech Stack:** Vanilla JavaScript, localStorage API, existing FastAPI backend (unchanged)

---

## File Map

| File | Change |
|------|--------|
| `static/pronunciation.html` | Add localStorage helpers, modify `init()`, `loadFields()`, deck-select handler, `startPracticing()` |

No new files. No backend changes.

---

### Task 1: Add localStorage helpers and constants

**Files:**
- Modify: `static/pronunciation.html` — add helpers near the top of the `<script>` block, after the existing `const DEFAULT_VOICES` line

- [ ] **Step 1: Add the helpers**

Open `static/pronunciation.html`. After line:
```javascript
const DEFAULT_VOICES = { 'fr-FR': 'fr-FR-DeniseNeural', 'en-US': 'en-US-JennyNeural' };
```

Insert:
```javascript
        const LS_LAST_DECK = 'pronunciation:lastDeck';
        function lsDeckKey(deck) { return `pronunciation:deck:${deck}`; }

        function lsGet(key) {
            try { return localStorage.getItem(key); } catch { return null; }
        }
        function lsSet(key, value) {
            try { localStorage.setItem(key, value); } catch { /* storage unavailable */ }
        }

        function saveDeckSettings(deck, textField, audioField, language) {
            lsSet(lsDeckKey(deck), JSON.stringify({ textField, audioField, language }));
        }

        function restoreDeckSettings(deck) {
            const raw = lsGet(lsDeckKey(deck));
            if (!raw) return;
            let saved;
            try { saved = JSON.parse(raw); } catch { return; }
            const tSel = document.getElementById('text-field-select');
            const aSel = document.getElementById('audio-field-select');
            const lSel = document.getElementById('language-select');
            if (saved.textField  && [...tSel.options].some(o => o.value === saved.textField))
                tSel.value = saved.textField;
            if (saved.audioField && [...aSel.options].some(o => o.value === saved.audioField))
                aSel.value = saved.audioField;
            if (saved.language   && [...lSel.options].some(o => o.value === saved.language))
                lSel.value = saved.language;
        }
```

- [ ] **Step 2: Verify the server starts cleanly**

```bash
uv run uvicorn app.main:app --reload &
sleep 2 && curl -s http://localhost:8000/ | head -5
```
Expected: HTML response starting with `<!DOCTYPE html>` (no Python errors in server output).

Kill the server: `kill %1`

- [ ] **Step 3: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: add localStorage helpers for pronunciation settings"
```

---

### Task 2: Restore last deck on page load

**Files:**
- Modify: `static/pronunciation.html` — change the deck-loading block inside `init()`

- [ ] **Step 1: Replace the deck init block**

Find this block inside `init()` (around line 218):
```javascript
                if (decks.length) {
                    await loadFields(decks[0]);
                    document.getElementById('start-btn').disabled = false;
                }
```

Replace it with:
```javascript
                if (decks.length) {
                    const lastDeck = lsGet(LS_LAST_DECK);
                    if (lastDeck && [...sel.options].some(o => o.value === lastDeck)) {
                        sel.value = lastDeck;
                        await loadFields(lastDeck);
                    } else {
                        await loadFields(decks[0]);
                    }
                    document.getElementById('start-btn').disabled = false;
                }
```

- [ ] **Step 2: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: pre-select last used deck on pronunciation page load"
```

---

### Task 3: Restore per-deck settings after fields load

**Files:**
- Modify: `static/pronunciation.html` — add `restoreDeckSettings(deck)` call at the end of `loadFields()`

- [ ] **Step 1: Add restore call in loadFields**

Find this inside `loadFields()`:
```javascript
                tSel.disabled = aSel.disabled = false;
            } catch { /* leave disabled */ }
```

Replace with:
```javascript
                tSel.disabled = aSel.disabled = false;
                restoreDeckSettings(deck);
            } catch { /* leave disabled */ }
```

- [ ] **Step 2: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: restore per-deck field settings after fields load"
```

---

### Task 4: Save last deck on deck change

**Files:**
- Modify: `static/pronunciation.html` — update the `deck-select` change event listener in `init()`

- [ ] **Step 1: Update the change event listener**

Find:
```javascript
            document.getElementById('deck-select').addEventListener('change', e => loadFields(e.target.value));
```

Replace with:
```javascript
            document.getElementById('deck-select').addEventListener('change', e => {
                lsSet(LS_LAST_DECK, e.target.value);
                loadFields(e.target.value);
            });
```

- [ ] **Step 2: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: save last selected deck to localStorage on change"
```

---

### Task 5: Save per-deck settings on Start Practicing

**Files:**
- Modify: `static/pronunciation.html` — add `saveDeckSettings()` call in `startPracticing()`

- [ ] **Step 1: Add save call in startPracticing**

Find:
```javascript
        async function startPracticing() {
            selectedDeck  = document.getElementById('deck-select').value;
            selectedField = document.getElementById('text-field-select').value;
            selectedAudio = document.getElementById('audio-field-select').value;
            selectedLang  = document.getElementById('language-select').value;
            hide('setup-phase');
```

Replace with:
```javascript
        async function startPracticing() {
            selectedDeck  = document.getElementById('deck-select').value;
            selectedField = document.getElementById('text-field-select').value;
            selectedAudio = document.getElementById('audio-field-select').value;
            selectedLang  = document.getElementById('language-select').value;
            saveDeckSettings(selectedDeck, selectedField, selectedAudio, selectedLang);
            hide('setup-phase');
```

- [ ] **Step 2: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: save per-deck field and language settings on Start Practicing"
```

---

### Task 6: Manual verification

**Files:** None — verification only

- [ ] **Step 1: Start the dev server**

```bash
uv run uvicorn app.main:app --reload
```

- [ ] **Step 2: Open the pronunciation page and verify last-deck restore**

1. Open `http://localhost:8000/pronunciation` in Chrome.
2. Select a non-default deck from the Deck dropdown.
3. Select a non-default Text Field and Audio Field.
4. Choose a different Language.
5. Click "Start Practicing" (so settings are saved).
6. Navigate away (e.g. go to the home page).
7. Navigate back to `http://localhost:8000/pronunciation`.
8. **Expected:** The previously selected deck, text field, audio field, and language are all pre-selected.

- [ ] **Step 3: Verify per-deck independence**

1. Select Deck A → set Language = English → click "Start Practicing".
2. Go back to setup (← Back to Setup button or reload).
3. Select Deck B → set Language = French → click "Start Practicing".
4. Go back to setup.
5. Select Deck A again.
6. **Expected:** Language reverts to English (the per-deck saved value for Deck A).

- [ ] **Step 4: Verify fallback when saved field is missing**

1. In Chrome DevTools → Application → Local Storage, find a `pronunciation:deck:<name>` key.
2. Edit the `textField` value to something that doesn't exist (e.g. `"__nonexistent__"`).
3. Reload the page.
4. **Expected:** Page loads without errors; the first available field is selected for that deck.

- [ ] **Step 5: Run backend tests to confirm no regressions**

```bash
uv run pytest tests/ -v
```
Expected: All tests pass (no backend code was changed, so all should be green).

- [ ] **Step 6: Final commit if any fixes were made during verification**

```bash
git add static/pronunciation.html
git commit -m "fix: pronunciation localStorage edge cases from manual testing"
```
(Skip this step if no fixes were needed.)
