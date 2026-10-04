from fastapi import APIRouter, HTTPException
from app.core.config import settings
from assistant_shared.hitl import ConfirmationStore

router = APIRouter(prefix="/confirmations", tags=["Confirmations"])


@router.get("/{confirmation_id}")
async def get_confirmation_status(confirmation_id: str):
    """Возвращает статус запроса подтверждения HITL (T-05-04: безопасные метаданные без приватного payload)."""
    store = ConfirmationStore(settings.SQLITE_DB_PATH)
    conf = await store.get_confirmation(confirmation_id)
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmation not found")

    return {
        "id": conf.id,
        "persona_id": conf.persona_id,
        "action_type": conf.action_type,
        "target_id": conf.target_id,
        "status": conf.status.value,
        "channel": conf.channel.value,
        "created_at": conf.created_at,
        "expires_at": conf.expires_at,
        "confirmed_by": conf.confirmed_by,
        "confirmed_at": conf.confirmed_at,
    }
