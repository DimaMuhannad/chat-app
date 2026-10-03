from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db import DatabaseService
from app.models.dashboard_schemas import TaskCreate, TaskUpdate, TaskStatusUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status (todo, in_progress, done)"),
    area: Optional[str] = Query(None, description="Filter by life area"),
    priority: Optional[str] = Query(None, description="Filter by priority (P1, P2, P3)"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
):
    return await DatabaseService.list_tasks(status=status, area=area, priority=priority, project_id=project_id)


@router.post("", status_code=201)
async def create_task(data: TaskCreate):
    return await DatabaseService.create_task(data.model_dump())


@router.get("/{task_id}")
async def get_task(task_id: int):
    task = await DatabaseService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}")
async def update_task(task_id: int, data: TaskUpdate):
    changes = data.model_dump(exclude_unset=True)
    if not changes.get("area"):
        changes.pop("area", None)  # пустая область не должна затирать существующую
    updated = await DatabaseService.update_task(task_id, changes)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.patch("/{task_id}/status")
async def update_task_status(task_id: int, data: TaskStatusUpdate):
    updated = await DatabaseService.update_task(task_id, {"status": data.status})
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    deleted = await DatabaseService.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}
