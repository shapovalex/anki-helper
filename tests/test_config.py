import os
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    fake_env = tmp_path / ".env.local"
    monkeypatch.setattr("app.config.ENV_LOCAL_PATH", fake_env)
    for key in ["OPENROUTER_API_KEY", "OPENROUTER_MODEL", "AZURE_TTS_KEY", "AZURE_TTS_REGION", "NOTE_TYPE_NAME"]:
        monkeypatch.delenv(key, raising=False)
    return fake_env


def test_defaults_when_no_file():
    from app.config import ConfigManager
    config = ConfigManager()
    assert config.openrouter_model == "google/gemini-flash-1.5"
    assert config.azure_tts_region == "westeurope"
    assert config.note_type_name == "French-Russian"
    assert not config.openrouter_key_set
    assert not config.azure_key_set


def test_reads_env_file(isolated_env):
    from app.config import ConfigManager
    isolated_env.write_text("OPENROUTER_API_KEY=sk-test\nOPENROUTER_MODEL=gpt-4o\n")
    config = ConfigManager()
    assert config.openrouter_api_key == "sk-test"
    assert config.openrouter_model == "gpt-4o"
    assert config.openrouter_key_set


def test_env_var_overrides_file(isolated_env, monkeypatch):
    from app.config import ConfigManager
    isolated_env.write_text("OPENROUTER_API_KEY=from-file\n")
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-env")
    config = ConfigManager()
    assert config.openrouter_api_key == "from-env"


def test_save_writes_to_file(isolated_env):
    from app.config import ConfigManager
    config = ConfigManager()
    config.save({"OPENROUTER_API_KEY": "new-key", "OPENROUTER_MODEL": "claude-opus"})
    assert config.openrouter_api_key == "new-key"
    assert config.openrouter_model == "claude-opus"
    content = isolated_env.read_text()
    assert "OPENROUTER_API_KEY=new-key" in content
    assert "OPENROUTER_MODEL=claude-opus" in content


def test_save_preserves_existing_keys(isolated_env):
    from app.config import ConfigManager
    isolated_env.write_text("AZURE_TTS_KEY=azure-key\n")
    config = ConfigManager()
    config.save({"OPENROUTER_API_KEY": "or-key"})
    assert config.azure_tts_key == "azure-key"
    assert config.openrouter_api_key == "or-key"


def test_reload_picks_up_file_changes(isolated_env):
    from app.config import ConfigManager
    config = ConfigManager()
    assert not config.openrouter_key_set
    isolated_env.write_text("OPENROUTER_API_KEY=late-key\n")
    config.reload()
    assert config.openrouter_api_key == "late-key"
