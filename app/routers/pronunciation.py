import base64
import random
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.pronunciation_agent import PronunciationAgent
from app.agents.recommendations_agent import RecommendationsAgent
from app.anki_client import AnkiClient, AnkiConnectError
from app.config import ConfigManager
from app.schemas import (
    PronunciationAnswerRequest,
    PronunciationAnswerResponse,
    PronunciationAssessRequest,
    PronunciationAssessResponse,
    PronunciationCardResponse,
    PronunciationFieldsResponse,
    PronunciationRecommendRequest,
    PronunciationRecommendResponse,
)

router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])

_SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")


def get_anki_client(request: Request) -> AnkiClient:
    return request.app.state.anki_client


def get_pronunciation_agent(request: Request) -> PronunciationAgent:
    config: ConfigManager = request.app.state.config
    if not config.azure_key_set:
        raise HTTPException(
            status_code=503,
            detail="Azure key not configured. Go to Settings.",
        )
    return PronunciationAgent(
        client=request.app.state.http_client,
        api_key=config.azure_tts_key,
        region=config.azure_tts_region,
    )


def get_recommendations_agent(request: Request) -> RecommendationsAgent:
    config: ConfigManager = request.app.state.config
    if not config.openrouter_key_set:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured. Go to Settings.",
        )
    return RecommendationsAgent(
        client=request.app.state.http_client,
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
    )


@router.get("/fields", response_model=PronunciationFieldsResponse)
async def get_fields(
    deck: str,
    anki_client: AnkiClient = Depends(get_anki_client),
) -> PronunciationFieldsResponse:
    try:
        card_ids = await anki_client.invoke("findCards", query=f'deck:"{deck}"')
        if not card_ids:
            raise HTTPException(status_code=404, detail="No cards found in deck.")
        cards_info = await anki_client.invoke("cardsInfo", cards=[card_ids[0]])
        fields = list(cards_info[0]["fields"].keys())
        return PronunciationFieldsResponse(fields=fields)
    except AnkiConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )


@router.get("/card", response_model=PronunciationCardResponse)
async def get_card(
    deck: str,
    field: str,
    audio_field: str,
    exclude_card_id: int | None = None,
    anki_client: AnkiClient = Depends(get_anki_client),
) -> PronunciationCardResponse:
    try:
        card_ids = await anki_client.invoke(
            "findCards", query=f'deck:"{deck}" (is:due OR is:new)'
        )
        if not card_ids:
            raise HTTPException(status_code=404, detail="No due or new cards in deck.")
        candidates = [c for c in card_ids if c != exclude_card_id] or card_ids
        card_id = random.choice(candidates)
        cards_info = await anki_client.invoke("cardsInfo", cards=[card_id])
        card = cards_info[0]
        text = card["fields"].get(field, {}).get("value", "")
        audio_field_value = card["fields"].get(audio_field, {}).get("value", "")
        audio_base64 = None
        m = _SOUND_RE.search(audio_field_value)
        if m:
            filename = m.group(1)
            audio_base64 = await anki_client.invoke("retrieveMediaFile", filename=filename)
        return PronunciationCardResponse(
            card_id=card_id, text=text, audio_base64=audio_base64
        )
    except AnkiConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )


@router.post("/assess", response_model=PronunciationAssessResponse)
async def assess(
    body: PronunciationAssessRequest,
    agent: PronunciationAgent = Depends(get_pronunciation_agent),
) -> PronunciationAssessResponse:
    audio_bytes = base64.b64decode(body.audio_base64)
    try:
        return await agent.assess(
            audio_bytes=audio_bytes,
            reference_text=body.reference_text,
            language=body.language,
            audio_mime_type=body.audio_mime_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/recommendations", response_model=PronunciationRecommendResponse)
async def recommendations(
    body: PronunciationRecommendRequest,
    agent: RecommendationsAgent = Depends(get_recommendations_agent),
) -> PronunciationRecommendResponse:
    try:
        return await agent.recommend(
            reference_text=body.reference_text,
            language=body.language,
            words=body.words,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/answer", response_model=PronunciationAnswerResponse)
async def answer(
    body: PronunciationAnswerRequest,
    anki_client: AnkiClient = Depends(get_anki_client),
) -> PronunciationAnswerResponse:
    try:
        result = await anki_client.invoke(
            "answerCards", answers=[{"cardId": body.card_id, "ease": body.ease}]
        )
        return PronunciationAnswerResponse(ok=bool(result and result[0]))
    except AnkiConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )
