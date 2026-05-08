import httpx
from typing import Any

ANKI_CONNECT_URL = "http://localhost:8765"
ANKI_CONNECT_VERSION = 6


class AnkiConnectError(Exception):
    """Raised when Anki Connect returns a non-null error field."""


class AnkiClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def invoke(self, action: str, **params: Any) -> Any:
        payload: dict[str, Any] = {"action": action, "version": ANKI_CONNECT_VERSION}
        if params:
            payload["params"] = params
        response = await self._client.post(ANKI_CONNECT_URL, json=payload)
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise AnkiConnectError(body["error"])
        return body["result"]
