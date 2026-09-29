from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db import DatabaseService
from app.models.dashboard_schemas import DocumentCreate, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
async def list_documents(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
):
    return await DatabaseService.list_documents(project_id=project_id)


@router.post("", status_code=201)
async def create_document(data: DocumentCreate):
    return await DatabaseService.create_document(data.model_dump())


@router.get("/{doc_id}")
async def get_document(doc_id: int):
    doc = await DatabaseService.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{doc_id}")
async def update_document(doc_id: int, data: DocumentUpdate):
    updated = await DatabaseService.update_document(doc_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Document not found")
    return updated


@router.delete("/{doc_id}")
async def delete_document(doc_id: int):
    deleted = await DatabaseService.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}
