from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db import DatabaseService
from app.models.dashboard_schemas import ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("")
async def list_projects(
    area: Optional[str] = Query(None, description="Filter by life area"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    return await DatabaseService.list_projects(area=area, status=status)


@router.post("", status_code=201)
async def create_project(data: ProjectCreate):
    return await DatabaseService.create_project(data.model_dump())


@router.get("/{project_id}")
async def get_project(project_id: int):
    project = await DatabaseService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate):
    updated = await DatabaseService.update_project(project_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated


@router.delete("/{project_id}")
async def delete_project(project_id: int):
    deleted = await DatabaseService.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}
