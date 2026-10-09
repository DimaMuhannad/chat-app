from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.db import PersonaNotLoadedError
import app.hitl_handlers  # noqa: F401 - регистрация обработчиков HITL при запуске

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("chat-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    @app.exception_handler(PersonaNotLoadedError)
    async def persona_not_loaded_handler(request: Request, exc: PersonaNotLoadedError):
        return JSONResponse(
            status_code=503, content={"detail": "Персона не загружена в базу данных"}
        )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        # Куки-авторизации нет, а credentials вместе с wildcard-origin отражают любой Origin: включаем
        # их только при явном списке источников
        allow_credentials="*" not in settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health endpoint and API v1 endpoints
    app.include_router(health_router, tags=["Health"])
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/api", tags=["API Root"])
    async def api_info():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME} API",
            "version": settings.VERSION,
            "docs": f"{settings.API_V1_STR}/docs",
            "health": "/health",
        }

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/", tags=["Dashboard"])
        async def dashboard_spa():
            return FileResponse(os.path.join(static_dir, "index.html"))

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
