import os
from pathlib import Path

ENV_LOCAL_PATH = Path(".env.local")

_DEFAULTS: dict[str, str] = {
    "OPENROUTER_MODEL": "google/gemini-flash-1.5",
    "AZURE_TTS_REGION": "westeurope",
    "NOTE_TYPE_NAME": "French-Russian-Word",
    "SENTENCE_NOTE_TYPE_NAME": "French-Russian-Sentence",
    "ENGLISH_NOTE_TYPE_NAME": "English-Russian-Word",
    "ENGLISH_SENTENCE_NOTE_TYPE_NAME": "English-Russian-Sentence",
}

_MANAGED_KEYS = {
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "AZURE_TTS_KEY",
    "AZURE_TTS_REGION",
    "NOTE_TYPE_NAME",
    "SENTENCE_NOTE_TYPE_NAME",
    "ENGLISH_NOTE_TYPE_NAME",
    "ENGLISH_SENTENCE_NOTE_TYPE_NAME",
}


class ConfigManager:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        merged = {**_DEFAULTS, **self._read_env_file()}
        for key in _MANAGED_KEYS:
            if key in os.environ:
                merged[key] = os.environ[key]
        self._data = merged

    def _read_env_file(self) -> dict[str, str]:
        if not ENV_LOCAL_PATH.exists():
            return {}
        result: dict[str, str] = {}
        for line in ENV_LOCAL_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
        return result

    def save(self, updates: dict[str, str]) -> None:
        unknown = set(updates) - _MANAGED_KEYS
        if unknown:
            raise ValueError(f"Unknown config keys: {unknown}")
        current = self._read_env_file()
        current.update(updates)
        ENV_LOCAL_PATH.write_text(
            "\n".join(f"{k}={v}" for k, v in current.items()) + "\n"
        )
        self.reload()

    @property
    def openrouter_api_key(self) -> str:
        return self._data.get("OPENROUTER_API_KEY", "")

    @property
    def openrouter_model(self) -> str:
        return self._data["OPENROUTER_MODEL"]

    @property
    def azure_tts_key(self) -> str:
        return self._data.get("AZURE_TTS_KEY", "")

    @property
    def azure_tts_region(self) -> str:
        return self._data["AZURE_TTS_REGION"]

    @property
    def note_type_name(self) -> str:
        return self._data["NOTE_TYPE_NAME"]

    @property
    def sentence_note_type_name(self) -> str:
        return self._data["SENTENCE_NOTE_TYPE_NAME"]

    @property
    def english_note_type_name(self) -> str:
        return self._data["ENGLISH_NOTE_TYPE_NAME"]

    @property
    def english_sentence_note_type_name(self) -> str:
        return self._data["ENGLISH_SENTENCE_NOTE_TYPE_NAME"]

    @property
    def openrouter_key_set(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def azure_key_set(self) -> bool:
        return bool(self.azure_tts_key)
