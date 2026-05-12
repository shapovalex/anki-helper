import logging
import re
import unicodedata
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.audio_agent import AudioAgent
from app.agents.english_sentence_translation_agent import EnglishSentenceTranslationAgent
from app.anki_client import AnkiClient, AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    AddEnglishSentenceToAnkiRequest,
    AddToAnkiResponse,
    AudioRequest,
    AudioResponse,
    SentenceGenerateRequest,
    SentenceTranslationResult,
    Voice,
    VoicesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/english-sentence-lookup", tags=["english-sentence-lookup"])


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", text).strip("_")
    return slug or "sentence"


def _filter_voices(voices: list[Voice], lang_prefix: str) -> list[Voice]:
    return [v for v in voices if v.id.startswith(lang_prefix)]


def get_translation_agent(request: Request) -> EnglishSentenceTranslationAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return EnglishSentenceTranslationAgent(
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
        voices = await agent.list_voices(locale_prefix="en-US")
        return VoicesResponse(voices=_filter_voices(voices, "en-"))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Azure TTS error: {e.response.status_code}")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Azure TTS.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Azure TTS timed out.")


@router.post("/generate", response_model=SentenceTranslationResult)
async def generate(
    body: SentenceGenerateRequest,
    agent: EnglishSentenceTranslationAgent = Depends(get_translation_agent),
) -> SentenceTranslationResult:
    try:
        return await agent.generate(sentence=body.sentence)
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
    body: AddEnglishSentenceToAnkiRequest,
    anki_client=Depends(get_anki_client),
) -> AddToAnkiResponse:
    filename = f"{_slugify(body.english_sentence[:40])}.mp3"
    try:
        await anki_client.invoke(
            "storeMediaFile",
            filename=filename,
            data=body.audio_base64,
        )
        note_id = await anki_client.invoke(
            "addNote",
            note={
                "deckName": body.deck,
                "modelName": body.note_type,
                "fields": {
                    "english_sentence": body.english_sentence,
                    "russian_sentence": body.russian_sentence,
                    "audio": f"[sound:{filename}]",
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
