# Pronunciation Phoneme Feedback Redesign

**Date:** 2026-05-08  
**Status:** Approved  
**File:** `static/pronunciation.html`

## Problem

The current results section buries phoneme data. Word chips are collapsed by default (only the worst-scoring word expands), phoneme scores display as bare numbers with no visual encoding of magnitude, and users cannot see all phonemes at a glance. The goal is to make phoneme quality immediately readable after each attempt.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Layout | Compact table (colored phrase + inline phoneme rows) | More scannable than word cards; phrase stays as visual anchor |
| Phoneme pill style | Symbol + mini score bar + number | Bar communicates magnitude at a glance; number gives precision |
| Top scores section | Keep unchanged | PronScore + Accuracy/Fluency/Completeness are useful summary |
| Phrase interactivity | Display-only (no tap-to-highlight) | Keeps interaction simple |
| Phoneme visibility | All words always expanded | User wants to see all phonemes, not just problem words |

## What Changes

### Remove

- `.word-chip` CSS class and all word chip rendering logic
- `.phoneme-row` CSS class and expandable phoneme row logic  
- The click handler that toggles phoneme rows open/closed
- The "worst word index" logic that auto-expands one word

### Add

**CSS — new phoneme table styles:**
- `.phoneme-table` — bordered container with `border-radius: 8px`
- `.phoneme-table-header` — small uppercase label row ("Phoneme breakdown")
- `.phoneme-word-row` — flex row: word column left, pills right, `border-bottom` between rows
- `.word-col` — fixed `min-width: 80px`; contains word name (color-coded) + score + error type
- `.pills` — flex-wrap container for phoneme pills
- `.phoneme-pill` — column-flex: symbol → 3px bar → score number; color-coded background + border

**JS — updated `showResults()` rendering:**

Replace the `words.forEach` block that builds word chips with a new block that builds the phoneme table:

```
for each word:
  render a .phoneme-word-row containing:
    - .word-col:
        .word-name  (text = word.word, class = scoreClass(word.accuracy))
        .word-score (text = "{accuracy} · {error_type}" if error_type !== "None", else just accuracy)
    - .pills:
        for each phoneme:
          .phoneme-pill.{scoreClass}:
            .sym  = phoneme.symbol
            .bar-wrap > .bar-fill (width = accuracy%, background = score color)
            .num  = Math.round(phoneme.accuracy)
```

### Unchanged

- Overall score badge (`eval-badge`) and sub-scores (Accuracy / Fluency / Completeness)
- "Azure heard" row (conditional display when recognized text differs)
- `renderColoredPhrase()` function — phrase still gets word-level color-coding
- Get Recommendations button and section
- Record Again / Play back buttons
- Anki rating buttons (Again / Hard / Good / Easy) and Skip link
- All recording, WAV conversion, and API logic

## Score Color Thresholds

Unchanged from current implementation:
- ≥ 80 → green (`score-green` / `#5fa875`)
- 50–79 → yellow (`score-yellow` / `#c9a040`)
- < 50 → red (`score-red` / `#c05a54`)

## Scope

Pure frontend change — `static/pronunciation.html` only. No backend, API, or schema changes required.
