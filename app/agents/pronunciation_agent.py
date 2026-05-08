import base64
import json

import httpx

from app.schemas import OverallScore, PhonemeResult, PronunciationAssessResponse, WordResult


class PronunciationAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, region: str) -> None:
        self._client = client
        self._api_key = api_key
        self._region = region

    async def assess(
        self, audio_bytes: bytes, reference_text: str, language: str
    ) -> PronunciationAssessResponse:
        config = json.dumps({
            "ReferenceText": reference_text,
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "EnableMiscue": True,
        })
        config_b64 = base64.b64encode(config.encode()).decode()
        url = (
            f"https://{self._region}.stt.speech.microsoft.com"
            f"/speech/recognition/conversation/cognitiveservices/v1"
            f"?language={language}&format=detailed"
        )
        response = await self._client.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Pronunciation-Assessment": config_b64,
                "Content-Type": "audio/webm;codecs=opus",
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
        return self._parse(response.json())

    def _parse(self, data: dict) -> PronunciationAssessResponse:
        nbest = data.get("NBest", [{}])[0]
        pa = nbest.get("PronunciationAssessment", {})
        overall = OverallScore(
            accuracy=pa.get("AccuracyScore", 0.0),
            fluency=pa.get("FluencyScore", 0.0),
            completeness=pa.get("CompletenessScore", 0.0),
            pron_score=pa.get("PronScore", 0.0),
        )
        words = []
        for w in nbest.get("Words", []):
            wpa = w.get("PronunciationAssessment", {})
            phonemes = [
                PhonemeResult(
                    symbol=p["Phoneme"],
                    accuracy=p.get("PronunciationAssessment", {}).get("AccuracyScore", 0.0),
                )
                for p in w.get("Phonemes", [])
            ]
            words.append(WordResult(
                word=w["Word"],
                accuracy=wpa.get("AccuracyScore", 0.0),
                error_type=wpa.get("ErrorType", "None"),
                phonemes=phonemes,
            ))
        return PronunciationAssessResponse(
            overall=overall,
            recognized_text=nbest.get("Display", ""),
            words=words,
        )
