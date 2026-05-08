import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.routers.settings import get_config


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.openrouter_model = "google/gemini-flash-1.5"
    config.azure_tts_region = "westeurope"
    config.openrouter_key_set = True
    config.azure_key_set = False
    config.note_type_name = "French-Russian"
    return config


@pytest.fixture
def client(mock_config):
    app.dependency_overrides[get_config] = lambda: mock_config
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_settings_returns_status_and_model(client, mock_config):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "google/gemini-flash-1.5"
    assert data["azure_region"] == "westeurope"
    assert data["openrouter_key_set"] is True
    assert data["azure_key_set"] is False
    assert data["note_type"] == "French-Russian"
    assert "openrouter_api_key" not in data
    assert "azure_api_key" not in data


def test_post_settings_saves_provided_fields(client, mock_config):
    response = client.post("/api/settings", json={
        "openrouter_api_key": "sk-new",
        "model": "claude-opus",
    })
    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_config.save.assert_called_once_with({
        "OPENROUTER_API_KEY": "sk-new",
        "OPENROUTER_MODEL": "claude-opus",
    })


def test_post_settings_ignores_none_fields(client, mock_config):
    response = client.post("/api/settings", json={"azure_region": "eastus"})
    assert response.status_code == 200
    mock_config.save.assert_called_once_with({"AZURE_TTS_REGION": "eastus"})


def test_post_settings_empty_body_does_not_call_save(client, mock_config):
    response = client.post("/api/settings", json={})
    assert response.status_code == 200
    mock_config.save.assert_not_called()
