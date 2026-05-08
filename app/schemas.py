from pydantic import BaseModel


class DeckListResponse(BaseModel):
    decks: list[str]
