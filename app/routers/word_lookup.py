import logging
import re
import unicodedata
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.audio_agent import AudioAgent
from app.agents.french_word_translation_agent import FrenchWordTranslationAgent
from app.anki_client import AnkiClient, AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    AddToAnkiRequest,
    AddToAnkiResponse,
    AudioRequest,
    AudioResponse,
    GenerateRequest,
    TranslationResult,
    Voice,
    VoicesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/word-lookup", tags=["word-lookup"])


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", text).strip("_")
    return slug or "word"


def get_translation_agent(request: Request) -> FrenchWordTranslationAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return FrenchWordTranslationAgent(
        client=request.app.state.http_client,
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
    )


def get_audio_agent(request: Request) -> AudioAgent:
    config: ConfigManager = request.app.state.config
    if not config.azure_key_set:
        raise HTTPException(
            status_code=503,
            detail="Azure TTS API key not configured. Go to Settings.",
        )
    return AudioAgent(
        client=request.app.state.http_client,
        api_key=config.azure_tts_key,
        region=config.azure_tts_region,
    )


def get_anki_client(request: Request) -> AnkiClient:
    return request.app.state.anki_client


@router.get("/voices", response_model=VoicesResponse)
async def list_voices(
    agent: AudioAgent = Depends(get_audio_agent),
) -> VoicesResponse:
    try:
        voices = await agent.list_voices()
        return VoicesResponse(voices=voices)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")


@router.post("/generate", response_model=TranslationResult)
async def generate(
    body: GenerateRequest,
    agent: FrenchWordTranslationAgent = Depends(get_translation_agent),
) -> TranslationResult:
    try:
        return await agent.generate(word=body.word, cefr_level=body.cefr_level)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Unexpected error in generate endpoint")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/audio", response_model=AudioResponse)
async def generate_audio(
    body: AudioRequest,
    agent: AudioAgent = Depends(get_audio_agent),
) -> AudioResponse:
    try:
        audio_b64 = await agent.synthesize(text=body.text, voice=body.voice)
        filename = f"{_slugify(body.text[:40])}.mp3"
        return AudioResponse(audio_base64=audio_b64, filename=filename)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
    except Exception as e:
        logger.exception("Unexpected error in generate_audio endpoint")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/add-to-anki", response_model=AddToAnkiResponse)
async def add_to_anki(
    body: AddToAnkiRequest,
    anki_client=Depends(get_anki_client),
) -> AddToAnkiResponse:
    word_slug = _slugify(body.french_word)
    word_filename = f"{word_slug}.mp3"
    example_filename = f"{word_slug}_example.mp3"
    try:
        await anki_client.invoke(
            "storeMediaFile",
            filename=word_filename,
            data=body.french_word_audio_base64,
        )
        await anki_client.invoke(
            "storeMediaFile",
            filename=example_filename,
            data=body.example_audio_base64,
        )
        note_id = await anki_client.invoke(
            "addNote",
            note={
                "deckName": body.deck,
                "modelName": body.note_type,
                "fields": {
                    "french_word": body.french_word,
                    "russian_word": body.russian_word,
                    "example": body.example,
                    "french_word_audio": f"[sound:{word_filename}]",
                    "example_audio": f"[sound:{example_filename}]",
                },
                "options": {"allowDuplicate": False},
                "tags": [],
            },
        )
        return AddToAnkiResponse(note_id=note_id)
    except AnkiConnectError as e:
        msg = str(e)
        if "model" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Note type '{body.note_type}' not found in Anki. Check Settings.",
            )
        raise HTTPException(status_code=502, detail=msg)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )
