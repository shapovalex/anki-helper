import base64
from xml.sax.saxutils import escape

import httpx

from app.schemas import Voice

_SSML_TEMPLATE = (
    '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">'
    '<voice name="{voice}">{text}</voice>'
    "</speak>"
)


def _lang_from_voice(voice: str) -> str:
    parts = voice.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return "fr-FR"  # safe fallback


class AudioAgent:
    def __init__(self, client: httpx.AsyncClient, api_key: str, region: str) -> None:
        self._client = client
        self._api_key = api_key
        self._region = region

    async def synthesize(self, text: str, voice: str) -> str:
        url = f"https://{self._region}.tts.speech.microsoft.com/cognitiveservices/v1"
        lang = _lang_from_voice(voice)
        ssml = _SSML_TEMPLATE.format(lang=escape(lang), voice=escape(voice), text=escape(text))
        response = await self._client.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            },
            content=ssml.encode(),
            timeout=30.0,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"Azure TTS request failed ({exc.response.status_code}): {exc.response.text[:200]}"
            ) from exc
        return base64.b64encode(response.content).decode()

    async def list_voices(self, locale_prefix: str = "fr-") -> list[Voice]:
        url = f"https://{self._region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
        response = await self._client.get(
            url,
            headers={"Ocp-Apim-Subscription-Key": self._api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        voices = [
            Voice(
                id=v["ShortName"],
                name=f"{v['DisplayName']} ({v['Gender']})",
            )
            for v in response.json()
            if v.get("Locale", "").startswith(locale_prefix)
        ]
        return sorted(voices, key=lambda v: v.name)
