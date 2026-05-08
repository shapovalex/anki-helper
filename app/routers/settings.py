from fastapi import APIRouter, Depends, Request

from app.config import ConfigManager
from app.schemas import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_config(request: Request) -> ConfigManager:
    return request.app.state.config


@router.get("", response_model=SettingsResponse)
async def get_settings(
    config: ConfigManager = Depends(get_config),
) -> SettingsResponse:
    return SettingsResponse(
        model=config.openrouter_model,
        azure_region=config.azure_tts_region,
        openrouter_key_set=config.openrouter_key_set,
        azure_key_set=config.azure_key_set,
        note_type=config.note_type_name,
    )


@router.post("", response_model=dict)
async def update_settings(
    body: SettingsUpdateRequest,
    config: ConfigManager = Depends(get_config),
) -> dict:
    updates: dict[str, str] = {}
    if body.openrouter_api_key is not None:
        updates["OPENROUTER_API_KEY"] = body.openrouter_api_key
    if body.azure_api_key is not None:
        updates["AZURE_TTS_KEY"] = body.azure_api_key
    if body.model is not None:
        updates["OPENROUTER_MODEL"] = body.model
    if body.azure_region is not None:
        updates["AZURE_TTS_REGION"] = body.azure_region
    if body.note_type is not None:
        updates["NOTE_TYPE_NAME"] = body.note_type
    if updates:
        config.save(updates)
    return {"ok": True}
