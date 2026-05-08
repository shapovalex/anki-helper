from pydantic import BaseModel


class DeckListResponse(BaseModel):
    decks: list[str]


class TranslationResult(BaseModel):
    russian_word: str
    example: str
    word_evaluation: str
    is_valid: bool


class GenerateRequest(BaseModel):
    word: str
    cefr_level: str


class AudioRequest(BaseModel):
    text: str
    voice: str


class AudioResponse(BaseModel):
    audio_base64: str
    filename: str


class Voice(BaseModel):
    id: str
    name: str


class VoicesResponse(BaseModel):
    voices: list[Voice]


class AddToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    french_word: str
    russian_word: str
    example: str
    french_word_audio_base64: str
    example_audio_base64: str


class AddToAnkiResponse(BaseModel):
    note_id: int


class SettingsResponse(BaseModel):
    model: str
    azure_region: str
    openrouter_key_set: bool
    azure_key_set: bool
    note_type: str


class SettingsUpdateRequest(BaseModel):
    model: str | None = None
    azure_region: str | None = None
    openrouter_api_key: str | None = None
    azure_api_key: str | None = None
    note_type: str | None = None
