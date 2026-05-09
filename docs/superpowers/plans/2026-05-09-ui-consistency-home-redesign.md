# UI Consistency & Home Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the home page as a feature card hub, add language-group separators to the nav, expand the help page to cover all 4 note types, and fix French page title inconsistencies.

**Architecture:** Pure frontend changes — HTML and CSS only. No backend routes, agents, or schemas change. All pages use the existing `theme.css` design system; this plan adds a small set of new classes to it.

**Tech Stack:** HTML, CSS, vanilla JS (fetch for Anki status check), FastAPI static file serving.

---

## File Map

| Action | File | What changes |
|---|---|---|
| Modify | `static/css/theme.css` | Append `.feature-*`, `.banner-warn`, `.nav-sep` classes |
| Rewrite | `static/index.html` | Feature card hub + Anki status banner |
| Rewrite | `static/components/menu.html` | Shorter labels + two `nav-sep` dividers |
| Rewrite | `static/help.html` | AnkiConnect setup + all 4 note types |
| Modify | `static/word-lookup.html` | `<title>` and `<h1>`: add "(FR)" |
| Modify | `static/sentence-lookup.html` | `<title>` and `<h1>`: add "(FR)" |

---

## Task 1: Add CSS classes to theme.css

**Files:**
- Modify: `static/css/theme.css` (append after line 394)

- [ ] **Step 1: Append the new classes**

Open `static/css/theme.css` and append the following block at the very end (after `.btn-danger:hover:not(:disabled) { background: #bf5550; }`):

```css

/* ── Feature hub (home page) ────────────────────────────────── */
.feature-section { margin-bottom: 1.75rem; }

.feature-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
}

.feature-card {
  display: block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 0.9rem 1rem;
  text-decoration: none;
  transition: border-color 0.14s, background 0.14s;
}

.feature-card:hover {
  border-color: rgba(212, 168, 67, 0.35);
  background: var(--surface-2);
}

.feature-card-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 0.2rem;
}

.feature-card-desc {
  font-size: 0.78rem;
  color: var(--text-muted);
  line-height: 1.45;
}

.feature-card-full { grid-column: span 2; }

/* ── Warning banner (parallel to .banner-error) ─────────────── */
.banner-warn {
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  color: var(--warn-text);
}
.banner-warn a { color: var(--accent); }

/* ── Nav separator ──────────────────────────────────────────── */
.nav-sep {
  width: 1px;
  height: 16px;
  background: var(--border);
  margin: 0 0.3rem;
  flex-shrink: 0;
}
```

- [ ] **Step 2: Verify the dev server starts cleanly**

```bash
uv run uvicorn app.main:app --reload
```

Expected: server starts on `http://127.0.0.1:8000` with no errors. Open any existing page (e.g. `http://localhost:8000/settings`) and confirm it looks unchanged — no broken styles.

- [ ] **Step 3: Commit**

```bash
git add static/css/theme.css
git commit -m "feat: add feature-hub, banner-warn, and nav-sep CSS classes"
```

---

## Task 2: Rewrite index.html

**Files:**
- Rewrite: `static/index.html`

- [ ] **Step 1: Replace the file contents**

Replace `static/index.html` entirely with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anki Helper</title>
    <link rel="stylesheet" href="/static/css/theme.css">
</head>
<body>
    <div id="menu-container"></div>
    <main class="page">
        <div class="page-header">
            <h1 class="page-title">Anki Helper</h1>
            <p class="page-subtitle">AI-powered flashcard creation for French and English vocabulary.</p>
        </div>

        <div id="anki-banner" class="banner banner-warn" style="display:none;">
            Anki is not running. Start Anki with the AnkiConnect add-on to add cards. <a href="/help">Setup guide →</a>
        </div>

        <div class="feature-section">
            <p class="section-heading">French</p>
            <div class="feature-grid">
                <a href="/word-lookup" class="feature-card">
                    <div class="feature-card-title">Word Lookup →</div>
                    <div class="feature-card-desc">Translation, example sentence, and audio for a French word.</div>
                </a>
                <a href="/sentence-lookup" class="feature-card">
                    <div class="feature-card-title">Sentence Lookup →</div>
                    <div class="feature-card-desc">Russian translation and audio for a French sentence.</div>
                </a>
            </div>
        </div>

        <div class="feature-section">
            <p class="section-heading">English</p>
            <div class="feature-grid">
                <a href="/english-word-lookup" class="feature-card">
                    <div class="feature-card-title">Word Lookup →</div>
                    <div class="feature-card-desc">Translation, example sentence, and audio for an English word.</div>
                </a>
                <a href="/english-sentence-lookup" class="feature-card">
                    <div class="feature-card-title">Sentence Lookup →</div>
                    <div class="feature-card-desc">Russian translation and audio for an English sentence.</div>
                </a>
            </div>
        </div>

        <div class="feature-section">
            <p class="section-heading">Practice</p>
            <div class="feature-grid">
                <a href="/pronunciation" class="feature-card feature-card-full">
                    <div class="feature-card-title">Pronunciation Practice →</div>
                    <div class="feature-card-desc">Practice speaking Anki cards aloud and get phoneme-level feedback from Azure Speech.</div>
                </a>
            </div>
        </div>
    </main>

    <script src="/static/js/menu.js"></script>
    <script>
        async function checkAnkiStatus() {
            try {
                const res = await fetch('/api/decks');
                if (!res.ok) throw new Error();
            } catch {
                document.getElementById('anki-banner').style.display = 'block';
            }
        }
        checkAnkiStatus();
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify in browser**

With the dev server running, open `http://localhost:8000/`. Confirm:
- Three sections visible: French, English, Practice
- Four cards total (2 FR + 2 EN) plus the Pronunciation full-width card
- Subtitle reads "French and English vocabulary"
- If Anki is not running, the yellow warning banner appears; if Anki is running, no banner

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: rewrite home page as feature card hub with Anki status detection"
```

---

## Task 3: Update navigation menu

**Files:**
- Rewrite: `static/components/menu.html`

- [ ] **Step 1: Replace the file contents**

Replace `static/components/menu.html` entirely with:

```html
<nav>
    <a href="/" class="nav-brand">Anki Helper</a>
    <div class="nav-links">
        <a href="/">Home</a>
        <a href="/word-lookup">FR Word</a>
        <a href="/sentence-lookup">FR Sentence</a>
        <div class="nav-sep"></div>
        <a href="/english-word-lookup">EN Word</a>
        <a href="/english-sentence-lookup">EN Sentence</a>
        <div class="nav-sep"></div>
        <a href="/pronunciation">Pronunciation</a>
        <a href="/settings">Settings</a>
        <a href="/help">Help</a>
    </div>
</nav>
```

- [ ] **Step 2: Verify in browser**

Open any page (e.g. `http://localhost:8000/word-lookup`). Confirm:
- Nav shows: Home · FR Word · FR Sentence | EN Word · EN Sentence | Pronunciation · Settings · Help
- Two thin vertical separators visible between the groups
- Active page highlights correctly (FR Word is highlighted on `/word-lookup`)
- All links navigate to the correct pages

- [ ] **Step 3: Commit**

```bash
git add static/components/menu.html
git commit -m "feat: add language-group separators and shorten nav labels"
```

---

## Task 4: Expand help page

**Files:**
- Rewrite: `static/help.html`

- [ ] **Step 1: Replace the file contents**

Replace `static/help.html` entirely with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Help — Anki Helper</title>
    <link rel="stylesheet" href="/static/css/theme.css">
</head>
<body>
    <div id="menu-container"></div>
    <main class="page page-sm">
        <div class="page-header">
            <h1 class="page-title">Help</h1>
            <p class="page-subtitle">How to set up Anki for use with this app.</p>
        </div>

        <p class="section-heading">AnkiConnect Setup</p>

        <p>This app communicates with Anki via the <strong>AnkiConnect</strong> add-on. Install it from within Anki: go to <em>Tools → Add-ons → Get Add-ons</em> and enter code <code>2055492159</code>. Restart Anki after installing. AnkiConnect runs a local server on port 8765 — the app connects to it automatically whenever Anki is open.</p>

        <p class="section-heading">French Word Note Type</p>

        <p>Create a note type whose name exactly matches the <strong>Note Type Name</strong> configured in <a href="/settings">Settings</a> (default: <code>French-Russian</code>). The note type must have at least these five fields:</p>

        <ul>
            <li><code>french_word</code></li>
            <li><code>russian_word</code></li>
            <li><code>example</code></li>
            <li><code>french_word_audio</code></li>
            <li><code>example_audio</code></li>
        </ul>

        <p class="section-heading">French Sentence Note Type</p>

        <p>Create a note type whose name exactly matches the <strong>Sentence Note Type Name</strong> in <a href="/settings">Settings</a> (default: <code>French-Russian-Sentence</code>). Required fields:</p>

        <ul>
            <li><code>french_sentence</code></li>
            <li><code>russian_sentence</code></li>
            <li><code>audio</code></li>
        </ul>

        <p class="section-heading">English Word Note Type</p>

        <p>Create a note type whose name exactly matches the <strong>English Note Type Name</strong> in <a href="/settings">Settings</a> (default: <code>English-Russian</code>). Required fields:</p>

        <ul>
            <li><code>english_word</code></li>
            <li><code>russian_word</code></li>
            <li><code>example</code></li>
            <li><code>english_word_audio</code></li>
            <li><code>example_audio</code></li>
        </ul>

        <p class="section-heading">English Sentence Note Type</p>

        <p>Create a note type whose name exactly matches the <strong>English Sentence Note Type Name</strong> in <a href="/settings">Settings</a> (default: <code>English-Russian-Sentence</code>). Required fields:</p>

        <ul>
            <li><code>english_sentence</code></li>
            <li><code>russian_sentence</code></li>
            <li><code>audio</code></li>
        </ul>
    </main>

    <script src="/static/js/menu.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify in browser**

Open `http://localhost:8000/help`. Confirm:
- Five sections appear: AnkiConnect Setup, French Word, French Sentence, English Word, English Sentence
- Each section has a paragraph and a field list with `<code>`-styled field names
- The AnkiConnect section shows the add-on code `2055492159`
- Links to `/settings` work

- [ ] **Step 3: Commit**

```bash
git add static/help.html
git commit -m "feat: expand help page with AnkiConnect setup and all four note types"
```

---

## Task 5: Fix French page language labels

**Files:**
- Modify: `static/word-lookup.html` (lines 5, 13)
- Modify: `static/sentence-lookup.html` (lines 5, 13)

- [ ] **Step 1: Update word-lookup.html title and h1**

In `static/word-lookup.html`:

Change line 6 (the `<title>` tag):
```html
    <title>Word Lookup (FR) — Anki Helper</title>
```

Change line 13 (the `<h1>` tag):
```html
            <h1 class="page-title">Word Lookup (FR)</h1>
```

- [ ] **Step 2: Update sentence-lookup.html title and h1**

In `static/sentence-lookup.html`:

Change line 6 (the `<title>` tag):
```html
    <title>Sentence Lookup (FR) — Anki Helper</title>
```

Change line 13 (the `<h1>` tag):
```html
            <h1 class="page-title">Sentence Lookup (FR)</h1>
```

- [ ] **Step 3: Verify in browser**

- Open `http://localhost:8000/word-lookup` — browser tab and page heading both read "Word Lookup (FR)"
- Open `http://localhost:8000/sentence-lookup` — browser tab and page heading both read "Sentence Lookup (FR)"
- Open `http://localhost:8000/english-word-lookup` — still reads "Word Lookup (EN)" (unchanged)
- Open `http://localhost:8000/english-sentence-lookup` — still reads "Sentence Lookup (EN)" (unchanged)

- [ ] **Step 4: Commit**

```bash
git add static/word-lookup.html static/sentence-lookup.html
git commit -m "fix: add (FR) language label to French word and sentence lookup pages"
```
