# Alternative Examples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return 5 alternative example sentences from the LLM alongside the primary example, display them as clickable buttons in the UI, and allow the user to replace the primary example (and re-generate audio) by clicking one.

**Architecture:** Add `alternative_examples: list[str]` to `TranslationResult`; extend the LLM system prompt to request 5 alternatives; add a frontend section below the primary example textarea with one button per alternative.

**Tech Stack:** Python/FastAPI (backend), Pydantic v2 (schemas), vanilla JS / HTML (frontend), pytest with httpx (tests).

---

### Task 1: Add `alternative_examples` to `TranslationResult` schema

**Files:**
- Modify: `app/schemas.py`
- Modify: `tests/test_word_lookup_router.py`

- [ ] **Step 1: Write a failing test**

In `tests/test_word_lookup_router.py`, update `test_generate_delegates_to_agent` to assert the new field:

```python
def test_generate_delegates_to_agent(client, mock_translation_agent):
    response = client.post(
        "/api/word-lookup/generate",
        json={"word": "bonjour", "cefr_level": "B1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["russian_word"] == "привет"
    assert data["is_valid"] is True
    assert len(data["alternative_examples"]) == 5
    mock_translation_agent.generate.assert_called_once_with(word="bonjour", cefr_level="B1")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper
uv run pytest tests/test_word_lookup_router.py::test_generate_delegates_to_agent -v
```

Expected: FAIL — `KeyError: 'alternative_examples'` or validation error.

- [ ] **Step 3: Add `alternative_examples` to `TranslationResult`**

In `app/schemas.py`, replace the `TranslationResult` class:

```python
class TranslationResult(BaseModel):
    russian_word: str
    example: str
    word_evaluation: str
    is_valid: bool
    alternative_examples: list[str]
```

- [ ] **Step 4: Update the mock fixture in the router test**

In `tests/test_word_lookup_router.py`, replace the `mock_translation_agent` fixture:

```python
@pytest.fixture
def mock_translation_agent():
    agent = MagicMock()
    agent.generate = AsyncMock(return_value=TranslationResult(
        russian_word="привет",
        example="Bonjour, comment allez-vous?",
        word_evaluation="Valid French interjection used as a greeting.",
        is_valid=True,
        alternative_examples=[
            "Bonjour, je m'appelle Marie.",
            "Dis bonjour à ta mère de ma part.",
            "Il faut dire bonjour quand on entre.",
            "Elle lui a dit bonjour en souriant.",
            "Bonjour tout le monde, bienvenue!",
        ],
    ))
    return agent
```

- [ ] **Step 5: Run all router tests to verify they pass**

```bash
uv run pytest tests/test_word_lookup_router.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/schemas.py tests/test_word_lookup_router.py
git commit -m "feat: add alternative_examples field to TranslationResult schema"
```

---

### Task 2: Update LLM system prompt to return 5 alternative examples

**Files:**
- Modify: `app/agents/french_word_translation_agent.py`
- Modify: `tests/agents/test_french_word_translation_agent.py`

- [ ] **Step 1: Update the integration test to assert the new field**

In `tests/agents/test_french_word_translation_agent.py`, update `test_generate_returns_translation_result`:

```python
async def test_generate_returns_translation_result(agent):
    result = await agent.generate(word="bonjour", cefr_level="B1")

    assert isinstance(result, TranslationResult)
    assert result.russian_word
    assert result.example
    assert result.word_evaluation
    assert result.is_valid is True
    assert isinstance(result.alternative_examples, list)
    assert len(result.alternative_examples) == 5
    assert all(isinstance(s, str) and s for s in result.alternative_examples)
```

- [ ] **Step 2: Run integration test to confirm current failure (skip if no key)**

```bash
uv run pytest tests/agents/test_french_word_translation_agent.py::test_generate_returns_translation_result -v
```

Expected: SKIP (if `OPENROUTER_API_KEY` not set) or FAIL with validation error on `alternative_examples`.

- [ ] **Step 3: Update the system prompt to request 5 alternative examples**

In `app/agents/french_word_translation_agent.py`, replace `_SYSTEM_PROMPT`:

```python
_SYSTEM_PROMPT = (
    "You are a French language expert. When given a French word and a CEFR level, "
    "respond ONLY with a JSON object (no markdown) with exactly these keys:\n"
    "- russian_word: Russian translation of the word\n"
    "- example: a natural French sentence using the word, appropriate for the CEFR level\n"
    "- alternative_examples: a JSON array of exactly 5 additional natural French sentences "
    "using the word, each appropriate for the CEFR level and distinct from 'example'\n"
    "- word_evaluation: brief note on whether the word is correctly spelled and valid French\n"
    "- is_valid: true if the word is a real, correctly spelled French word, false otherwise"
)
```

- [ ] **Step 4: Run integration test to verify it passes (skip if no key)**

```bash
uv run pytest tests/agents/test_french_word_translation_agent.py -v
```

Expected: PASS (or SKIP if no API key — acceptable).

- [ ] **Step 5: Run the full test suite**

```bash
uv run pytest -v
```

Expected: All non-skipped tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/agents/french_word_translation_agent.py tests/agents/test_french_word_translation_agent.py
git commit -m "feat: request 5 alternative example sentences from LLM"
```

---

### Task 3: Add alternative examples section to the frontend

**Files:**
- Modify: `static/word-lookup.html`

- [ ] **Step 1: Add the HTML section below the primary example field**

In `static/word-lookup.html`, replace:

```html
            <div class="field">
                <label>Example (French)</label>
                <textarea id="example" rows="3"></textarea>
            </div>
```

with:

```html
            <div class="field">
                <label>Example (French)</label>
                <textarea id="example" rows="3"></textarea>
            </div>

            <div id="alt-examples-section" class="field">
                <label>Alternative Examples</label>
                <div id="alt-examples-list"></div>
            </div>
```

- [ ] **Step 2: Populate alternative examples in the `generate()` function**

In `static/word-lookup.html`, inside the `generate()` function, after:

```javascript
                document.getElementById('example').value     = data.example;
```

add:

```javascript
                const altList = document.getElementById('alt-examples-list');
                altList.innerHTML = '';
                (data.alternative_examples || []).forEach(alt => {
                    const btn = document.createElement('button');
                    btn.className = 'btn-secondary btn-full';
                    btn.style.cssText = 'text-align:left; margin-bottom:0.5rem; white-space:normal; height:auto; padding:0.5rem 0.75rem;';
                    btn.textContent = alt;
                    btn.addEventListener('click', () => {
                        document.getElementById('example').value = alt;
                        regenAudio('example');
                    });
                    altList.appendChild(btn);
                });
```

- [ ] **Step 3: Start the dev server and manually test**

```bash
uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000/word-lookup` in a browser. Enter a French word (e.g. `bonjour`), click Generate, and verify:
- 5 alternative example buttons appear below the primary example textarea
- Clicking an alternative replaces the primary example textarea value
- Clicking an alternative triggers example audio re-generation

- [ ] **Step 4: Commit**

```bash
git add static/word-lookup.html
git commit -m "feat: display 5 alternative examples with click-to-use in word lookup UI"
```
