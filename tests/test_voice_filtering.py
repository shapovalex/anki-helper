from app.schemas import Voice


def _filter_voices(voices: list[Voice], lang_prefix: str) -> list[Voice]:
    return [v for v in voices if v.id.startswith(lang_prefix)]


def test_filter_french_voices():
    all_voices = [
        Voice(id="fr-FR-DeniseNeural", name="Denise"),
        Voice(id="en-US-JennyNeural", name="Jenny"),
        Voice(id="fr-CA-SylvieNeural", name="Sylvie"),
        Voice(id="de-DE-KatjaNeural", name="Katja"),
    ]
    result = _filter_voices(all_voices, "fr-")
    assert [v.id for v in result] == ["fr-FR-DeniseNeural", "fr-CA-SylvieNeural"]


def test_filter_english_voices():
    all_voices = [
        Voice(id="fr-FR-DeniseNeural", name="Denise"),
        Voice(id="en-US-JennyNeural", name="Jenny"),
        Voice(id="en-GB-LibbyNeural", name="Libby"),
        Voice(id="de-DE-KatjaNeural", name="Katja"),
    ]
    result = _filter_voices(all_voices, "en-")
    assert [v.id for v in result] == ["en-US-JennyNeural", "en-GB-LibbyNeural"]


def test_filter_returns_empty_when_none_match():
    all_voices = [Voice(id="de-DE-KatjaNeural", name="Katja")]
    result = _filter_voices(all_voices, "fr-")
    assert result == []
