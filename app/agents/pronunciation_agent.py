import base64
import json
import logging

import httpx

from app.schemas import OverallScore, PhonemeResult, PronunciationAssessResponse, WordResult

log = logging.getLogger(__name__)


class PronunciationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, region: str) -> None:
        self._client = client
        self._api_key = api_key
        self._region = region

    async def assess(
        self,
        audio_bytes: bytes,
        reference_text: str,
        language: str,
        audio_mime_type: str = "audio/webm;codecs=opus",
    ) -> PronunciationAssessResponse:
        config = json.dumps({
            "ReferenceText": reference_text,
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "Dimension": "Comprehensive",
            "EnableMiscue": True,
        })
        config_b64 = base64.b64encode(config.encode()).decode()
        url = (
            f"https://{self._region}.stt.speech.microsoft.com"
            f"/speech/recognition/conversation/cognitiveservices/v1"
            f"?language={language}&format=detailed"
        )
        # Azure requires the exact codec/samplerate MIME for pronunciation assessment.
        # Plain "audio/wav" is accepted for STT but silently disables PA scoring.
        if audio_mime_type == "audio/wav":
            audio_mime_type = "audio/wav; codecs=audio/pcm; samplerate=16000"
        log.info(
            "Azure STT request: reference_text=%r language=%s mime=%s audio_bytes=%d",
            reference_text, language, audio_mime_type, len(audio_bytes),
        )
        response = await self._client.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Pronunciation-Assessment": config_b64,
                "Content-Type": audio_mime_type,
            },
            content=audio_bytes,
            timeout=30.0,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"Azure Speech request failed ({exc.response.status_code}): "
                f"{exc.response.text[:200]}"
            ) from exc
        data = response.json()
        log.info("Azure STT response: %s", json.dumps(data))
        return self._parse(data)

    def _parse(self, data: dict) -> PronunciationAssessResponse:
        status = data.get("RecognitionStatus", "")
        if status not in ("Success", ""):
            raise ValueError(f"Azure recognition failed: {status}")
        nbest = data.get("NBest", [{}])[0]
        # REST API returns scores flat in each object, not nested under "PronunciationAssessment"
        overall = OverallScore(
            accuracy=nbest.get("AccuracyScore", 0.0),
            fluency=nbest.get("FluencyScore", 0.0),
            completeness=nbest.get("CompletenessScore", 0.0),
            pron_score=nbest.get("PronScore", 0.0),
        )
        words = []
        for w in nbest.get("Words", []):
            phonemes = [
                PhonemeResult(
                    symbol=p["Phoneme"],
                    accuracy=p.get("AccuracyScore", 0.0),
                )
                for p in w.get("Phonemes", [])
            ]
            words.append(WordResult(
                word=w["Word"],
                accuracy=w.get("AccuracyScore", 0.0),
                error_type=w.get("ErrorType", "None"),
                phonemes=phonemes,
            ))
        return PronunciationAssessResponse(
            overall=overall,
            recognized_text=nbest.get("Display", ""),
            words=words,
        )
