from fastapi import APIRouter, Depends, HTTPException, Request

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
        sentence_note_type=config.sentence_note_type_name,
        english_note_type=config.english_note_type_name,
        english_sentence_note_type=config.english_sentence_note_type_name,
    )


@router.post("", response_model=dict[str, bool])
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
    if body.sentence_note_type is not None:
        updates["SENTENCE_NOTE_TYPE_NAME"] = body.sentence_note_type
    if body.english_note_type is not None:
        updates["ENGLISH_NOTE_TYPE_NAME"] = body.english_note_type
    if body.english_sentence_note_type is not None:
        updates["ENGLISH_SENTENCE_NOTE_TYPE_NAME"] = body.english_sentence_note_type
    if updates:
        try:
            config.save(updates)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Failed to persist settings") from exc
    return {"ok": True}
