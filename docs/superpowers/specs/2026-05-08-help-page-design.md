# Help Page Design

**Date:** 2026-05-08

## Overview

Add a dedicated Help page to the Anki Helper app explaining the required Anki note type name and field names. The page is static HTML served by the existing FastAPI static file mount.

## Scope

- New file: `static/help.html`
- Updated file: `static/js/menu.js` — add "Help" link to nav

No backend changes required.

## Content

One section: **Anki Note Type Setup**

Explains:
- The note type name must exactly match the value configured in Settings (default: `French-Russian`)
- The note type must contain exactly these five fields:
  - `french_word`
  - `russian_word`
  - `example`
  - `french_word_audio`
  - `example_audio`

Presented as a short paragraph followed by a field list. No table needed.

## Page Structure

Follows the existing page pattern used by `settings.html` and `word-lookup.html`:

```html
<div id="menu-container"></div>
<main class="page page-sm">
  <div class="page-header">
    <h1 class="page-title">Help</h1>
    <p class="page-subtitle">…</p>
  </div>
  <!-- content -->
</main>
<script src="/static/js/menu.js"></script>
```

## Navigation

A "Help" link is appended to the existing nav in `menu.js` so it appears on every page.

## Out of Scope

- Deck setup instructions
- AnkiConnect installation guide
- Screenshots or images
