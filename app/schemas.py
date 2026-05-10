from pydantic import BaseModel, Field


class DeckListResponse(BaseModel):
    decks: list[str]


class TranslationResult(BaseModel):
    russian_word: str
    example: str
    word_evaluation: str
    is_valid: bool
    alternative_examples: list[str]


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
    french_word: str = Field(min_length=1, max_length=100)
    russian_word: str
    example: str
    french_word_audio_base64: str
    example_audio_base64: str


class AddToAnkiResponse(BaseModel):
    note_id: int


class SentenceTranslationResult(BaseModel):
    russian_sentence: str
    sentence_evaluation: str
    is_valid: bool


class SentenceGenerateRequest(BaseModel):
    sentence: str


class AddSentenceToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    french_sentence: str = Field(min_length=1, max_length=500)
    russian_sentence: str
    audio_base64: str


class AddEnglishWordToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    english_word: str = Field(min_length=1, max_length=100)
    russian_word: str
    example: str
    english_word_audio_base64: str
    example_audio_base64: str


class AddEnglishSentenceToAnkiRequest(BaseModel):
    deck: str
    note_type: str
    english_sentence: str = Field(min_length=1, max_length=500)
    russian_sentence: str
    audio_base64: str


class SettingsResponse(BaseModel):
    model: str
    azure_region: str
    openrouter_key_set: bool
    azure_key_set: bool
    note_type: str
    sentence_note_type: str
    english_note_type: str
    english_sentence_note_type: str


class SettingsUpdateRequest(BaseModel):
    model: str | None = Field(default=None, min_length=1)
    azure_region: str | None = Field(default=None, min_length=1)
    openrouter_api_key: str | None = Field(default=None, min_length=1)
    azure_api_key: str | None = Field(default=None, min_length=1)
    note_type: str | None = Field(default=None, min_length=1)
    sentence_note_type: str | None = Field(default=None, min_length=1)
    english_note_type: str | None = Field(default=None, min_length=1)
    english_sentence_note_type: str | None = Field(default=None, min_length=1)


class PronunciationFieldsResponse(BaseModel):
    fields: list[str]


class PronunciationCardResponse(BaseModel):
    card_id: int
    text: str
    audio_base64: str | None


class PronunciationAssessRequest(BaseModel):
    audio_base64: str
    audio_mime_type: str = "audio/webm;codecs=opus"
    reference_text: str
    language: str


class PhonemeResult(BaseModel):
    symbol: str
    accuracy: float


class SyllableResult(BaseModel):
    grapheme: str
    accuracy: float


class WordResult(BaseModel):
    word: str
    accuracy: float
    error_type: str
    phonemes: list[PhonemeResult]
    syllables: list[SyllableResult] = []


class OverallScore(BaseModel):
    accuracy: float
    fluency: float
    completeness: float
    pron_score: float


class PronunciationAssessResponse(BaseModel):
    overall: OverallScore
    recognized_text: str
    words: list[WordResult]


class PronunciationRecommendRequest(BaseModel):
    reference_text: str
    language: str
    words: list[WordResult]


class PronunciationRecommendResponse(BaseModel):
    tips: list[str]


class PronunciationAnswerRequest(BaseModel):
    card_id: int
    ease: int = Field(ge=1, le=4)


class PronunciationAnswerResponse(BaseModel):
    ok: bool


class PronunciationTranslateRequest(BaseModel):
    text: str
    language: str  # BCP-47, e.g. "fr-FR"


class PronunciationTranslateResponse(BaseModel):
    russian_text: str
