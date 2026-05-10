# Pronunciation Translate Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Translate to Russian" button to the pronunciation practice page that uses the configured OpenRouter LLM to translate the current card text, language-aware (fr-FR or en-US).

**Architecture:** A new `PronunciationTranslationAgent` calls the OpenRouter API with a minimal prompt. A new `POST /api/pronunciation/translate` endpoint wires the agent into FastAPI with the same dependency pattern used by the recommendations endpoint. The frontend shows a button immediately on card load that reveals a panel with the Russian text on first click.

**Tech Stack:** Python 3.13, FastAPI, httpx, pytest-asyncio, vanilla JS in `static/pronunciation.html`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `app/agents/pronunciation_translation_agent.py` | Create | Calls OpenRouter, returns Russian translation |
| `app/schemas.py` | Modify | Add `PronunciationTranslateRequest`, `PronunciationTranslateResponse` |
| `app/routers/pronunciation.py` | Modify | Add `get_translation_agent` dep + `POST /translate` endpoint |
| `tests/agents/test_pronunciation_translation_agent.py` | Create | Unit tests for the agent |
| `tests/test_pronunciation_router.py` | Modify | Router tests for `/translate` endpoint |
| `static/pronunciation.html` | Modify | Translate button, translation panel, JS logic |

---

## Task 1: Add Pydantic schemas

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: Add the two new schemas at the end of `app/schemas.py`**

```python
class PronunciationTranslateRequest(BaseModel):
    text: str
    language: str  # BCP-47, e.g. "fr-FR"


class PronunciationTranslateResponse(BaseModel):
    russian_text: str
```

- [ ] **Step 2: Verify schemas import cleanly**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper && uv run python -c "from app.schemas import PronunciationTranslateRequest, PronunciationTranslateResponse; print('ok')"
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add PronunciationTranslate request/response schemas"
```

---

## Task 2: Implement `PronunciationTranslationAgent`

**Files:**
- Create: `app/agents/pronunciation_translation_agent.py`
- Create: `tests/agents/test_pronunciation_translation_agent.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/agents/test_pronunciation_translation_agent.py`:

```python
import json
import pytest
import httpx

from app.agents.pronunciation_translation_agent import PronunciationTranslationAgent


class _FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, russian_text: str):
        self._russian_text = russian_text

    async def handle_async_request(self, request):
        body = json.dumps({
            "choices": [{"message": {"content": json.dumps({"russian_text": self._russian_text})}}]
        }).encode()
        return httpx.Response(
            200,
            content=body,
            request=request,
            headers={"content-type": "application/json"},
        )


class _BadJsonTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request):
        body = json.dumps({
            "choices": [{"message": {"content": "not valid json"}}]
        }).encode()
        return httpx.Response(
            200,
            content=body,
            request=request,
            headers={"content-type": "application/json"},
        )


async def test_translate_returns_russian_text():
    transport = _FakeTransport("Привет")
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")

    result = await agent.translate(text="Bonjour", language="fr-FR")

    assert result == "Привет"


async def test_translate_includes_language_name_in_request():
    captured = {}

    class _CapturingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            captured["body"] = json.loads(request.content)
            body = json.dumps({
                "choices": [{"message": {"content": json.dumps({"russian_text": "Привет"})}}]
            }).encode()
            return httpx.Response(
                200,
                content=body,
                request=request,
                headers={"content-type": "application/json"},
            )

    client = httpx.AsyncClient(transport=_CapturingTransport())
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")
    await agent.translate(text="Bonjour", language="fr-FR")

    user_content = captured["body"]["messages"][-1]["content"]
    assert "French" in user_content
    assert "Bonjour" in user_content


async def test_translate_english_includes_english_in_request():
    captured = {}

    class _CapturingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            captured["body"] = json.loads(request.content)
            body = json.dumps({
                "choices": [{"message": {"content": json.dumps({"russian_text": "Привет"})}}]
            }).encode()
            return httpx.Response(
                200,
                content=body,
                request=request,
                headers={"content-type": "application/json"},
            )

    client = httpx.AsyncClient(transport=_CapturingTransport())
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")
    await agent.translate(text="Hello", language="en-US")

    user_content = captured["body"]["messages"][-1]["content"]
    assert "English" in user_content


async def test_translate_raises_on_invalid_json():
    transport = _BadJsonTransport()
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationTranslationAgent(client=client, api_key="fake", model="test")

    with pytest.raises(ValueError, match="non-JSON"):
        await agent.translate(text="Bonjour", language="fr-FR")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper && uv run pytest tests/agents/test_pronunciation_translation_agent.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — the agent file doesn't exist yet.

- [ ] **Step 3: Create `app/agents/pronunciation_translation_agent.py`**

```python
import json
import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_LANGUAGE_NAMES: dict[str, str] = {
    "fr-FR": "French",
    "en-US": "English",
}

_SYSTEM_PROMPT = (
    "Translate the given text to Russian. "
    "Respond ONLY with a JSON object (no markdown) with exactly one key: russian_text."
)


class PronunciationTranslationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def translate(self, text: str, language: str) -> str:
        language_name = _LANGUAGE_NAMES.get(language, language)
        user_message = f"Translate the following {language_name} text to Russian:\n{text}"
        response = await self._client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenRouter returned non-JSON content: {content!r}") from exc
        return data["russian_text"]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper && uv run pytest tests/agents/test_pronunciation_translation_agent.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/pronunciation_translation_agent.py tests/agents/test_pronunciation_translation_agent.py
git commit -m "feat: add PronunciationTranslationAgent with OpenRouter backend"
```

---

## Task 3: Add `/api/pronunciation/translate` endpoint

**Files:**
- Modify: `app/routers/pronunciation.py`
- Modify: `tests/test_pronunciation_router.py`

- [ ] **Step 1: Add the new tests to `tests/test_pronunciation_router.py`**

At the top of the file, extend the existing imports to add:

```python
from app.agents.pronunciation_translation_agent import PronunciationTranslationAgent
from app.routers.pronunciation import get_translation_agent
from app.schemas import PronunciationTranslateResponse
```

Add a new fixture after `mock_recommendations_agent`:

```python
@pytest.fixture
def mock_translation_agent():
    agent = MagicMock()
    agent.translate = AsyncMock(return_value="Привет")
    return agent
```

Update the existing `client` fixture to also override `get_translation_agent`:

```python
@pytest.fixture
def client(mock_anki, mock_pronunciation_agent, mock_recommendations_agent, mock_translation_agent):
    app.dependency_overrides[get_anki_client] = lambda: mock_anki
    app.dependency_overrides[get_pronunciation_agent] = lambda: mock_pronunciation_agent
    app.dependency_overrides[get_recommendations_agent] = lambda: mock_recommendations_agent
    app.dependency_overrides[get_translation_agent] = lambda: mock_translation_agent
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

Add the new test functions at the end of the file:

```python
def test_translate_returns_russian_text(client, mock_translation_agent):
    response = client.post("/api/pronunciation/translate", json={
        "text": "Bonjour le monde",
        "language": "fr-FR",
    })
    assert response.status_code == 200
    assert response.json()["russian_text"] == "Привет"
    mock_translation_agent.translate.assert_called_once_with(
        text="Bonjour le monde", language="fr-FR"
    )


def test_translate_returns_503_when_openrouter_not_configured():
    from fastapi import HTTPException

    def raise_503():
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured. Go to Settings.")

    app.dependency_overrides[get_translation_agent] = raise_503
    try:
        with TestClient(app) as c:
            response = c.post("/api/pronunciation/translate", json={
                "text": "Bonjour",
                "language": "fr-FR",
            })
        assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_translation_agent, None)


def test_translate_returns_502_on_agent_error(client, mock_translation_agent):
    mock_translation_agent.translate = AsyncMock(side_effect=ValueError("OpenRouter returned non-JSON content"))
    response = client.post("/api/pronunciation/translate", json={
        "text": "Bonjour",
        "language": "fr-FR",
    })
    assert response.status_code == 502
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper && uv run pytest tests/test_pronunciation_router.py::test_translate_returns_russian_text tests/test_pronunciation_router.py::test_translate_returns_503_when_openrouter_not_configured tests/test_pronunciation_router.py::test_translate_returns_502_on_agent_error -v
```

Expected: `ImportError` — `get_translation_agent` doesn't exist yet.

- [ ] **Step 3: Add the dependency function and endpoint to `app/routers/pronunciation.py`**

Add this import at the top of the file (with the existing agent imports):

```python
from app.agents.pronunciation_translation_agent import PronunciationTranslationAgent
```

Add this import in the schemas import block:

```python
    PronunciationTranslateRequest,
    PronunciationTranslateResponse,
```

Add the dependency function after `get_recommendations_agent`:

```python
def get_translation_agent(request: Request) -> PronunciationTranslationAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return PronunciationTranslationAgent(
        client=request.app.state.http_client,
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
    )
```

Add the endpoint at the end of the router (before or after `answer`):

```python
@router.post("/translate", response_model=PronunciationTranslateResponse)
async def translate(
    body: PronunciationTranslateRequest,
    agent: PronunciationTranslationAgent = Depends(get_translation_agent),
) -> PronunciationTranslateResponse:
    try:
        russian_text = await agent.translate(text=body.text, language=body.language)
        return PronunciationTranslateResponse(russian_text=russian_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
```

- [ ] **Step 4: Run all pronunciation router tests**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper && uv run pytest tests/test_pronunciation_router.py -v
```

Expected: all tests PASS (including the original ones, which must still pass).

- [ ] **Step 5: Commit**

```bash
git add app/routers/pronunciation.py tests/test_pronunciation_router.py
git commit -m "feat: add POST /api/pronunciation/translate endpoint"
```

---

## Task 4: Frontend — translate button and panel

**Files:**
- Modify: `static/pronunciation.html`

- [ ] **Step 1: Add the HTML for the button and panel**

In `static/pronunciation.html`, locate the `#pronounce-text` div (line ~200):

```html
<div class="pronounce-text" id="pronounce-text"></div>
```

Insert the following immediately after it:

```html
<button id="translate-btn" class="btn-secondary btn-full" style="margin-bottom:0.5rem;">Translate to Russian</button>
<div id="translate-error" class="inline-error"></div>
<div id="translation-panel" style="display:none; background:var(--surface-2,#222); border:1px solid var(--border,#2a2a2a); border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.75rem;">
    <p id="translation-text" style="margin:0; font-size:1rem; color:var(--text); line-height:1.4;"></p>
</div>
```

- [ ] **Step 2: Add the `translateCard` JS function**

In the `<script>` block, add this function after `getRecommendations()`:

```javascript
async function translateCard() {
    const btn = document.getElementById('translate-btn');
    const errorEl = document.getElementById('translate-error');
    btn.disabled = true;
    btn.textContent = 'Translating…';
    errorEl.textContent = '';

    try {
        const res = await fetch('/api/pronunciation/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: currentCardText, language: selectedLang }),
        });
        if (!res.ok) {
            const { detail } = await res.json().catch(() => ({}));
            errorEl.textContent = detail ?? `Error ${res.status}`;
            btn.disabled = false;
            btn.textContent = 'Retry Translation';
            return;
        }
        const { russian_text } = await res.json();
        document.getElementById('translation-text').textContent = russian_text;
        show('translation-panel');
        btn.style.display = 'none';
    } catch {
        errorEl.textContent = 'Network error.';
        btn.disabled = false;
        btn.textContent = 'Retry Translation';
    }
}
```

- [ ] **Step 3: Wire up the button event listener**

In the `init()` function, add this line alongside the existing button listeners (e.g. near `start-btn` event listener):

```javascript
document.getElementById('translate-btn').addEventListener('click', translateCard);
```

- [ ] **Step 4: Reset translation state in `loadCard()`**

In the `loadCard()` function, add these lines at the top of the function body (after `resetForRecording()`):

```javascript
hide('translation-panel');
document.getElementById('translate-error').textContent = '';
const translateBtn = document.getElementById('translate-btn');
translateBtn.disabled = false;
translateBtn.textContent = 'Translate to Russian';
translateBtn.style.display = '';
```

- [ ] **Step 5: Run all tests to confirm nothing is broken**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper && uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Start the dev server and manually verify**

```bash
cd /Users/Oleksii_Shapovalov/projects/anki-helper && uv run uvicorn app.main:app --reload
```

Open http://localhost:8000/pronunciation.html in a browser. Verify:
- "Translate to Russian" button appears as soon as a card loads
- Clicking it shows "Translating…" then reveals the Russian text in the panel
- Button disappears after successful translation
- Loading the next card resets the button and hides the panel

- [ ] **Step 7: Commit**

```bash
git add static/pronunciation.html
git commit -m "feat: add translate-to-Russian button to pronunciation practice"
```
