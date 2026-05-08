import os
import pytest
import httpx
from app.agents.french_word_translation_agent import FrenchWordTranslationAgent
from app.schemas import TranslationResult

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")


@pytest.fixture
def require_openrouter_key():
    if not OPENROUTER_KEY:
        pytest.skip("OPENROUTER_API_KEY not set")


@pytest.fixture
async def agent(require_openrouter_key):
    async with httpx.AsyncClient() as client:
        yield FrenchWordTranslationAgent(
            client=client,
            api_key=OPENROUTER_KEY,
            model="google/gemini-flash-1.5",
        )


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


async def test_generate_flags_misspelled_word(agent):
    result = await agent.generate(word="bonjore", cefr_level="A1")

    assert isinstance(result, TranslationResult)
    assert result.is_valid is False
