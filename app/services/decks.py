from app.anki_client import AnkiClient


class DeckService:
    def __init__(self, anki: AnkiClient) -> None:
        self._anki = anki

    async def list_deck_names(self) -> list[str]:
        return await self._anki.invoke("deckNames")
