from fastapi import APIRouter
from app.db import DatabaseService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary():
    return await DatabaseService.get_dashboard_summary()
