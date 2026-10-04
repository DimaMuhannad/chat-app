from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.documents import router as documents_router
from app.api.v1.security import router as security_router
from app.api.v1.persona import router as persona_router
from app.api.v1.confirmations import router as confirmations_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(dashboard_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(reminders_router)
api_router.include_router(documents_router)
api_router.include_router(security_router)
api_router.include_router(persona_router)
api_router.include_router(confirmations_router)
