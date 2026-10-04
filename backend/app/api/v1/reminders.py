from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db import DatabaseService
from app.models.dashboard_schemas import ReminderCreate, ReminderUpdate
from app.core.config import settings
from assistant_shared.hitl import (
    ConfirmationChannel,
    ConfirmationStore,
    create_hitl_conflict_exception,
)

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("")
async def list_reminders(
    status: Optional[str] = Query(None, description="Filter by status (active, completed)"),
):
    return await DatabaseService.list_reminders(status=status)


@router.post("", status_code=201)
async def create_reminder(data: ReminderCreate):
    return await DatabaseService.create_reminder(data.model_dump())


@router.get("/{reminder_id}")
async def get_reminder(reminder_id: int):
    reminder = await DatabaseService.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.put("/{reminder_id}")
async def update_reminder(reminder_id: int, data: ReminderUpdate):
    updated = await DatabaseService.update_reminder(reminder_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return updated


@router.patch("/{reminder_id}/toggle")
async def toggle_reminder(reminder_id: int):
    reminder = await DatabaseService.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    new_status = "completed" if reminder["status"] == "active" else "active"
    return await DatabaseService.update_reminder(reminder_id, {"status": new_status})


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: int):
    reminder = await DatabaseService.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    store = ConfirmationStore(settings.SQLITE_DB_PATH)
    confirmation = await store.create_confirmation(
        persona_id=settings.PERSONA_ID,
        action_type="delete_reminder",
        target_id=str(reminder_id),
        payload={"reminder_id": reminder_id, "what": reminder.get("what")},
        channel=ConfirmationChannel.WEB,
        ttl_minutes=10,
    )
    raise create_hitl_conflict_exception(confirmation)
