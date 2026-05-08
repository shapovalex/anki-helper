import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.anki_client import AnkiConnectError
from app.schemas import DeckListResponse
from app.services.decks import DeckService

router = APIRouter(prefix="/api/decks", tags=["decks"])


def get_deck_service(request: Request) -> DeckService:
    return DeckService(request.app.state.anki_client)


@router.get("", response_model=DeckListResponse)
async def list_decks(service: DeckService = Depends(get_deck_service)) -> DeckListResponse:
    try:
        names = await service.list_deck_names()
    except AnkiConnectError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Anki. Make sure Anki is running with Anki-Connect enabled.",
        )
    return DeckListResponse(decks=names)
