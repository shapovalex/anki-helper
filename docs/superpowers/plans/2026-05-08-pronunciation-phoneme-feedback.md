# Pronunciation Phoneme Feedback Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the collapsible word-chip UI with a compact phoneme table where every word's phonemes are always visible as color-coded pills (symbol + score bar + number).

**Architecture:** Pure frontend change to `static/pronunciation.html`. The CSS block gains new phoneme table styles; the JS `showResults()` function's words-rendering block is replaced; three old CSS classes are removed. No backend or API changes.

**Tech Stack:** Vanilla HTML/CSS/JS. No build step — edit the file and reload the browser.

---

## File Map

| File | Change |
|---|---|
| `static/pronunciation.html` | Remove 3 CSS classes, add 11 CSS rules, remove HTML label, replace ~36 JS lines |

---

> **Note on testing:** This project has no frontend test suite. Each task ends with a manual browser verification step instead of `pytest`. Start the dev server once and keep it running throughout:
> ```bash
> uv run uvicorn app.main:app --reload
> ```
> Then open `http://localhost:8000/pronunciation` in a browser.

---

## Task 1: Replace CSS — remove old classes, add phoneme table styles

**Files:**
- Modify: `static/pronunciation.html:34-58` (CSS block)

- [ ] **Step 1: Remove the three old CSS classes**

In `static/pronunciation.html`, find and delete lines 34–58 — the `.word-chip`, `.word-chip:hover`, `.phoneme-row`, and `.phoneme-chip` blocks. The exact text to remove:

```css
        .word-chip {
            display: inline-block;
            padding: 0.3rem 0.7rem;
            border-radius: var(--radius);
            font-size: 0.9rem;
            cursor: pointer;
            border: 1px solid transparent;
            margin-bottom: 0.4rem;
            transition: opacity 0.12s;
        }
        .word-chip:hover { opacity: 0.8; }
        .phoneme-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
            padding: 0.4rem 0 0.5rem 0.5rem;
        }
        .phoneme-chip {
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-family: var(--font-mono);
            border: 1px solid transparent;
        }
```

Replace that entire block with the new phoneme table styles:

```css
        .phoneme-table {
            border: 1px solid var(--border, #2a2a2a);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 1rem;
        }
        .phoneme-table-header {
            background: var(--surface-2, #222);
            padding: 0.4rem 0.9rem;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border, #2a2a2a);
        }
        .phoneme-word-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.6rem 0.9rem;
            border-bottom: 1px solid var(--surface-2, #222);
        }
        .phoneme-word-row:last-child { border-bottom: none; }
        .word-col {
            min-width: 80px;
            flex-shrink: 0;
        }
        .word-col-name {
            font-weight: 600;
            font-size: 0.9rem;
        }
        .word-col-score {
            font-size: 0.7rem;
            opacity: 0.65;
            margin-top: 0.05rem;
        }
        .pills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
        }
        .phoneme-pill {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 0.2rem 0.45rem 0.25rem;
            border-radius: 5px;
            min-width: 36px;
            gap: 0.15rem;
        }
        .phoneme-pill .pill-sym {
            font-family: var(--font-mono, monospace);
            font-size: 0.88rem;
            font-weight: 700;
            line-height: 1;
        }
        .phoneme-pill .pill-bar-wrap {
            width: 30px;
            height: 3px;
            background: rgba(255,255,255,0.08);
            border-radius: 2px;
            overflow: hidden;
        }
        .phoneme-pill .pill-bar-fill {
            height: 100%;
            border-radius: 2px;
        }
        .score-green .pill-bar-fill  { background: var(--success-text); }
        .score-yellow .pill-bar-fill { background: var(--warn-text); }
        .score-red .pill-bar-fill    { background: var(--error-text); }
        .phoneme-pill .pill-num {
            font-size: 0.62rem;
            opacity: 0.6;
            line-height: 1;
        }
```

- [ ] **Step 2: Verify CSS change doesn't break the page structure**

With the dev server running, open `http://localhost:8000/pronunciation`. The setup phase (deck selector, Start Practicing button) should look exactly the same as before — the CSS you changed only affects the results section.

- [ ] **Step 3: Commit**

```bash
git add static/pronunciation.html
git commit -m "refactor: replace word-chip/phoneme-chip CSS with phoneme table styles"
```

---

## Task 2: Remove HTML "Words" label + replace JS rendering

**Files:**
- Modify: `static/pronunciation.html:172-174` (HTML label)
- Modify: `static/pronunciation.html:642-677` (JS `showResults` words block)

- [ ] **Step 1: Remove the "Words" label from the HTML**

Find this block in the HTML (around line 172):

```html
                    <div class="field">
                        <label>Words</label>
                        <div id="words-container"></div>
                    </div>
```

Replace it with (drop the label; the phoneme table provides its own "Phoneme breakdown" header):

```html
                    <div class="field">
                        <div id="words-container"></div>
                    </div>
```

- [ ] **Step 2: Replace the JS words-rendering block in `showResults()`**

Find this block in `showResults()` (starts around line 642):

```javascript
            // Find worst-scoring word index
            let worstIdx = 0;
            data.words.forEach((w, i) => { if (w.accuracy < data.words[worstIdx].accuracy) worstIdx = i; });

            const container = document.getElementById('words-container');
            container.innerHTML = '';
            data.words.forEach((word, idx) => {
                const wordWrap = document.createElement('div');
                wordWrap.style.marginBottom = '0.5rem';

                const chip = document.createElement('div');
                const sc = scoreClass(word.accuracy);
                chip.className = `word-chip ${sc}`;
                const errorLabel = word.error_type !== 'None' ? ` · ${word.error_type}` : '';
                chip.textContent = `${word.word} ${Math.round(word.accuracy)}${errorLabel}`;

                const phonemeRow = document.createElement('div');
                phonemeRow.className = 'phoneme-row';
                phonemeRow.style.display = idx === worstIdx ? 'flex' : 'none';

                word.phonemes.forEach(p => {
                    const pc = document.createElement('span');
                    const psc = scoreClass(p.accuracy);
                    pc.className = `phoneme-chip ${psc}`;
                    pc.textContent = `${p.symbol} ${Math.round(p.accuracy)}`;
                    phonemeRow.appendChild(pc);
                });

                chip.addEventListener('click', () => {
                    phonemeRow.style.display = phonemeRow.style.display === 'none' ? 'flex' : 'none';
                });

                wordWrap.appendChild(chip);
                wordWrap.appendChild(phonemeRow);
                container.appendChild(wordWrap);
            });
```

Replace it with:

```javascript
            const container = document.getElementById('words-container');
            container.innerHTML = '';

            const table = document.createElement('div');
            table.className = 'phoneme-table';

            const tableHeader = document.createElement('div');
            tableHeader.className = 'phoneme-table-header';
            tableHeader.textContent = 'Phoneme breakdown';
            table.appendChild(tableHeader);

            data.words.forEach(word => {
                const row = document.createElement('div');
                row.className = 'phoneme-word-row';

                const wordCol = document.createElement('div');
                wordCol.className = 'word-col';

                const wordName = document.createElement('div');
                wordName.className = `word-col-name ${scoreClass(word.accuracy)}`;
                wordName.textContent = word.word;
                wordCol.appendChild(wordName);

                const wordScore = document.createElement('div');
                wordScore.className = 'word-col-score';
                const errorLabel = word.error_type !== 'None' ? ` · ${word.error_type}` : '';
                wordScore.textContent = `${Math.round(word.accuracy)}${errorLabel}`;
                wordCol.appendChild(wordScore);

                const pills = document.createElement('div');
                pills.className = 'pills';

                word.phonemes.forEach(p => {
                    const pill = document.createElement('div');
                    pill.className = `phoneme-pill ${scoreClass(p.accuracy)}`;

                    const sym = document.createElement('span');
                    sym.className = 'pill-sym';
                    sym.textContent = p.symbol;
                    pill.appendChild(sym);

                    const barWrap = document.createElement('div');
                    barWrap.className = 'pill-bar-wrap';
                    const barFill = document.createElement('div');
                    barFill.className = 'pill-bar-fill';
                    barFill.style.width = `${Math.round(p.accuracy)}%`;
                    barWrap.appendChild(barFill);
                    pill.appendChild(barWrap);

                    const num = document.createElement('span');
                    num.className = 'pill-num';
                    num.textContent = Math.round(p.accuracy);
                    pill.appendChild(num);

                    pills.appendChild(pill);
                });

                row.appendChild(wordCol);
                row.appendChild(pills);
                table.appendChild(row);
            });

            container.appendChild(table);
```

- [ ] **Step 3: Verify the full results flow in the browser**

With Anki running (or mock data), go through the pronunciation practice flow:

1. Select a deck and press **Start Practicing**
2. Record yourself saying the phrase (hold the button)
3. After assessment, confirm the results section shows:
   - PronScore badge and Accuracy/Fluency/Completeness sub-badges → **unchanged**
   - "Azure heard" row (if recognized text differs) → **unchanged**
   - A **"Phoneme breakdown"** table where every word has a row showing:
     - Left column: word name (color-coded by score) + score number + error type if any
     - Right: phoneme pills — each pill has IPA symbol on top, a thin colored bar in the middle, score number below
   - All words are expanded — no click required
   - **Record Again**, **Play back**, and Anki rating buttons → **unchanged**
4. Confirm word color in the phrase at top still updates (green/yellow/red per word accuracy)
5. Confirm "Record Again" resets correctly — the phoneme table disappears and plain text reappears

- [ ] **Step 4: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: replace word chips with always-expanded phoneme table

Each word row shows IPA symbols with color-coded score bars. Removes
click-to-expand interaction; all phonemes visible at a glance."
```

---

## Self-Review Checklist (done)

- **Spec coverage:** All spec items covered — CSS additions, CSS removals, HTML label removal, JS replacement, unchanged sections verified
- **No placeholders:** All steps contain complete code
- **Type consistency:** `scoreClass()`, `word.accuracy`, `word.error_type`, `p.symbol`, `p.accuracy` match the existing `WordResult`/`PhonemeResult` schema in `app/schemas.py`
