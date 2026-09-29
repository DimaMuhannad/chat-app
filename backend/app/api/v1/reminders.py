from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db import DatabaseService
from app.models.dashboard_schemas import ReminderCreate, ReminderUpdate

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
    deleted = await DatabaseService.delete_reminder(reminder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"ok": True}
