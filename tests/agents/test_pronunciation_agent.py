import base64
import json
import pytest
import httpx

from app.agents.pronunciation_agent import PronunciationAgent

SAMPLE_AZURE_RESPONSE = {
    "RecognitionStatus": "Success",
    "NBest": [{
        "Display": "Bonjour.",
        "PronunciationAssessment": {
            "AccuracyScore": 85.0,
            "FluencyScore": 90.0,
            "CompletenessScore": 95.0,
            "PronScore": 88.0,
        },
        "Words": [{
            "Word": "bonjour",
            "PronunciationAssessment": {
                "AccuracyScore": 85.0,
                "ErrorType": "None",
            },
            "Phonemes": [
                {"Phoneme": "b", "PronunciationAssessment": {"AccuracyScore": 95.0}},
                {"Phoneme": "ɔ̃", "PronunciationAssessment": {"AccuracyScore": 72.0}},
            ],
        }],
    }],
}


class _FakeAzureTransport(httpx.AsyncBaseTransport):
    def __init__(self, response_data: dict, status_code: int = 200):
        self._response_data = response_data
        self._status_code = status_code
        self.last_request = None

    async def handle_async_request(self, request):
        self.last_request = request
        body = json.dumps(self._response_data).encode()
        return httpx.Response(
            self._status_code,
            content=body,
            request=request,
            headers={"content-type": "application/json"},
        )


async def test_assess_parses_overall_scores():
    transport = _FakeAzureTransport(SAMPLE_AZURE_RESPONSE)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="fake-key", region="eastus")

    result = await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")

    assert result.overall.pron_score == 88.0
    assert result.overall.accuracy == 85.0
    assert result.overall.fluency == 90.0
    assert result.overall.completeness == 95.0


async def test_assess_parses_words_and_phonemes():
    transport = _FakeAzureTransport(SAMPLE_AZURE_RESPONSE)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="fake-key", region="eastus")

    result = await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")

    assert len(result.words) == 1
    word = result.words[0]
    assert word.word == "bonjour"
    assert word.accuracy == 85.0
    assert word.error_type == "None"
    assert len(word.phonemes) == 2
    assert word.phonemes[0].symbol == "b"
    assert word.phonemes[0].accuracy == 95.0
    assert word.phonemes[1].symbol == "ɔ̃"
    assert word.phonemes[1].accuracy == 72.0


async def test_assess_sends_correct_pronunciation_assessment_header():
    transport = _FakeAzureTransport(SAMPLE_AZURE_RESPONSE)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="fake-key", region="eastus")

    await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")

    headers = dict(transport.last_request.headers)
    assert "pronunciation-assessment" in headers
    config = json.loads(base64.b64decode(headers["pronunciation-assessment"]))
    assert config["ReferenceText"] == "bonjour"
    assert config["Granularity"] == "Phoneme"
    assert config["GradingSystem"] == "HundredMark"
    assert config["EnableMiscue"] is True


async def test_assess_raises_value_error_on_http_error():
    transport = _FakeAzureTransport({}, status_code=401)
    client = httpx.AsyncClient(transport=transport)
    agent = PronunciationAgent(client=client, api_key="bad-key", region="eastus")

    with pytest.raises(ValueError, match="Azure Speech request failed"):
        await agent.assess(audio_bytes=b"fake", reference_text="bonjour", language="fr-FR")
