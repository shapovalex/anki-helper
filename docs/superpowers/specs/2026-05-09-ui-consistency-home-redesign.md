# UI Consistency & Home Page Redesign

**Date:** 2026-05-09

## Overview

The app has grown from a French-only word lookup tool into a bilingual (French + English) flashcard creation suite with pronunciation practice. The home page, navigation, and help page no longer reflect reality. This spec covers a focused UI pass to align all three with the current feature set.

## Scope

Four files change:

| File | Change |
|---|---|
| `static/index.html` | Full rewrite — feature card hub |
| `static/components/menu.html` | Add language-group separators, shorten labels |
| `static/help.html` | Expand to cover all 4 note types + AnkiConnect setup |
| `static/word-lookup.html`, `static/sentence-lookup.html` | Add "(FR)" to h1 and title for consistency |

No backend changes.

---

## 1. Home Page (`static/index.html`)

### Layout

Replace the current minimal hero with a feature card hub. Three sections with `section-heading` labels:

- **French** — 2-column grid: Word Lookup card + Sentence Lookup card
- **English** — 2-column grid: Word Lookup card + Sentence Lookup card
- **Practice** — full-width card: Pronunciation Practice

Each card uses the existing `.feature-card` pattern (surface background, border, hover state, accent title, muted description).

### Page header

- Title: `Anki Helper` (unchanged)
- Subtitle: `AI-powered flashcard creation for French and English vocabulary.` (was French-only)

### Anki status banner

On page load, call `GET /api/decks`. If the request fails or returns non-ok, show a warning banner:

> Anki is not running. Start Anki with the AnkiConnect add-on to add cards. [Setup guide →](/help)

Use the existing `.banner` and `.banner-warn` classes (warn style, not error). The banner is hidden by default and shown only on failure — silent success.

### Removed

- The broken `<a href="/decks">View Decks</a>` button (no `/decks` route exists).
- The old `.home-hero` block and its inline description.

### CSS additions to `theme.css`

Add to `theme.css` (all classes are currently absent):

```css
/* Feature hub */
.feature-section { margin-bottom: 1.75rem; }
.feature-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }
.feature-card {
  display: block; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 0.9rem 1rem; text-decoration: none;
  transition: border-color 0.14s, background 0.14s;
}
.feature-card:hover { border-color: rgba(212, 168, 67, 0.35); background: var(--surface-2); }
.feature-card-title { font-size: 0.88rem; font-weight: 600; color: var(--accent); margin-bottom: 0.2rem; }
.feature-card-desc { font-size: 0.78rem; color: var(--text-muted); line-height: 1.45; }
.feature-card-full { grid-column: span 2; }

/* Warning banner (parallel to .banner-error, uses warn tokens) */
.banner-warn {
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  color: var(--warn-text);
}
.banner-warn a { color: var(--accent); }
```

---

## 2. Navigation (`static/components/menu.html`)

### Label changes

| Old label | New label |
|---|---|
| Word Lookup (FR) | FR Word |
| Sentence Lookup (FR) | FR Sentence |
| Word Lookup (EN) | EN Word |
| Sentence Lookup (EN) | EN Sentence |

Home, Pronunciation, Settings, Help — unchanged.

### Separators

Add two `<div class="nav-sep"></div>` elements:
1. Between "FR Sentence" and "EN Word" — separates French group from English group
2. Between "EN Sentence" and "Pronunciation" — separates lookup tools from utility pages

### CSS addition to `theme.css`

```css
.nav-sep {
  width: 1px;
  height: 16px;
  background: var(--border);
  margin: 0 0.3rem;
  flex-shrink: 0;
}
```

---

## 3. Help Page (`static/help.html`)

### Structure

Five sections using `.section-heading`:

**AnkiConnect Setup**

Short paragraph: install the AnkiConnect add-on (code `2055492159`) from the Anki add-on browser, restart Anki, and confirm it runs on port 8765. This is required for the app to add cards to Anki.

**French Word Note Type**

Note type name must match the value set in Settings (default: `French-Russian`). Required fields:
- `french_word`
- `russian_word`
- `example`
- `french_word_audio`
- `example_audio`

**French Sentence Note Type**

Note type name must match Settings (default: `French-Russian-Sentence`). Required fields:
- `french_sentence`
- `russian_sentence`
- `audio`

**English Word Note Type**

Note type name must match Settings (default: `English-Russian`). Required fields:
- `english_word`
- `russian_word`
- `example`
- `english_word_audio`
- `example_audio`

**English Sentence Note Type**

Note type name must match Settings (default: `English-Russian-Sentence`). Required fields:
- `english_sentence`
- `russian_sentence`
- `audio`

Each section: one short paragraph explaining the note type name requirement, followed by a `<ul>` of field names in `<code>` tags.

---

## 4. French Page Label Consistency

The French lookup pages lack a language indicator in their titles and headings, while their English counterparts include "(EN)". Add "(FR)" for symmetry.

| File | Element | Before | After |
|---|---|---|---|
| `static/word-lookup.html` | `<title>` | `Word Lookup — Anki Helper` | `Word Lookup (FR) — Anki Helper` |
| `static/word-lookup.html` | `<h1>` | `Word Lookup` | `Word Lookup (FR)` |
| `static/sentence-lookup.html` | `<title>` | `Sentence Lookup — Anki Helper` | `Sentence Lookup (FR) — Anki Helper` |
| `static/sentence-lookup.html` | `<h1>` | `Sentence Lookup` | `Sentence Lookup (FR)` |

Subtitles (`page-subtitle`) are already accurate and do not change.

---

## Out of Scope

- No changes to any backend router or agent
- No changes to pronunciation, settings, English lookup pages (already consistent)
- No decks page (the `/decks` link is simply removed)
- No mobile/responsive nav changes
- No changes to existing page scripts or API calls
