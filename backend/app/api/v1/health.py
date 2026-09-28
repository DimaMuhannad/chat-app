from datetime import datetime, timezone
import os
import platform
import time
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()
START_TIME = time.time()


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    version: str
    timestamp: str
    uptime_seconds: float
    environment: dict


@router.get("/health", response_model=HealthResponse)
async def get_health():
    uptime = time.time() - START_TIME
    return HealthResponse(
        status="ok",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(uptime, 2),
        environment={
            "python_version": platform.python_version(),
            "os": platform.system(),
            "kernel": platform.release(),
            "pid": os.getpid(),
        },
    )
