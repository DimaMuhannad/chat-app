from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.db import DatabaseService

router = APIRouter(prefix="/persona", tags=["Persona"])


def persona_public_view(config: dict[str, Any]) -> dict[str, Any]:
    """Явный белый список: API без аутентификации (OPS-05), наружу только видимое в интерфейсе."""
    persona = config["persona"] if "persona" in config else config
    return {
        "id": persona["id"],
        "display_name": persona["display_name"],
        "short_name": persona["short_name"],
        "title": persona["title"],
        "organizations": {
            key: {"name": org["name"]} for key, org in persona["organizations"].items()
        },
        "default_area": persona["default_area"],
        "task_areas": [
            {
                "value": area["value"],
                "label": area["label"],
                "filter_label": area.get("filter_label") or area["label"],
                "show_in_filter": bool(area.get("show_in_filter", True)),
            }
            for area in persona["task_areas"]
        ],
        "ui": {"texts": dict(persona["ui"]["texts"])},
    }


@router.get("/current")
async def get_current_persona() -> dict[str, Any]:
    row = await DatabaseService.get_persona(settings.PERSONA_ID)
    if row is None:
        raise HTTPException(status_code=503, detail="Персона не загружена в базу данных")
    return persona_public_view(row["config"])
