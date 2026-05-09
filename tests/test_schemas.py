import pytest
from pydantic import ValidationError
from app.schemas import (
    AddEnglishWordToAnkiRequest,
    AddEnglishSentenceToAnkiRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)


def test_add_english_word_to_anki_request_valid():
    req = AddEnglishWordToAnkiRequest(
        deck="Default",
        note_type="English-Russian",
        english_word="hello",
        russian_word="привет",
        example="Hello, how are you?",
        english_word_audio_base64="abc123",
        example_audio_base64="def456",
    )
    assert req.english_word == "hello"


def test_add_english_word_to_anki_request_empty_word():
    with pytest.raises(ValidationError):
        AddEnglishWordToAnkiRequest(
            deck="Default",
            note_type="English-Russian",
            english_word="",
            russian_word="привет",
            example="Hello!",
            english_word_audio_base64="abc",
            example_audio_base64="def",
        )


def test_add_english_sentence_to_anki_request_valid():
    req = AddEnglishSentenceToAnkiRequest(
        deck="Default",
        note_type="English-Russian-Sentence",
        english_sentence="How are you?",
        russian_sentence="Как дела?",
        audio_base64="abc123",
    )
    assert req.english_sentence == "How are you?"


def test_settings_response_includes_english_fields():
    s = SettingsResponse(
        model="gpt-4",
        azure_region="westeurope",
        openrouter_key_set=True,
        azure_key_set=True,
        note_type="French-Russian",
        sentence_note_type="French-Russian-Sentence",
        english_note_type="English-Russian",
        english_sentence_note_type="English-Russian-Sentence",
    )
    assert s.english_note_type == "English-Russian"
    assert s.english_sentence_note_type == "English-Russian-Sentence"


def test_settings_update_request_english_fields():
    req = SettingsUpdateRequest(
        english_note_type="My-English",
        english_sentence_note_type="My-English-Sentence",
    )
    assert req.english_note_type == "My-English"
