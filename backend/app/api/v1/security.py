from pathlib import Path
import time
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.db import DatabaseService
from assistant_shared.security import (
    audit_path,
    nda_rule_for,
)

router = APIRouter(prefix="/security", tags=["Security Shield"])


async def _persona_workspaces() -> list[dict[str, Any]]:
    """Пространства персоны из БД; пусто - 503 (fail-closed: не «0 проектов, чисто»)."""
    workspaces = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    if not workspaces:
        raise HTTPException(status_code=503, detail="Рабочие пространства персоны не загружены в базу данных")
    return workspaces


class AuditRequest(BaseModel):
    project_id: str | None = None


@router.get("/overview")
async def get_security_overview():
    """Returns status of Security Shield, clearance levels, and Air-Gap guardrails."""
    workspaces = await _persona_workspaces()
    overview = []
    total_violations = 0

    for p in workspaces:
        p_path = Path(p["path"])
        res = audit_path(p_path, nda_rule=nda_rule_for(p))
        total_violations += len(res.get("violations", []))

        overview.append({
            "id": p["id"],
            "name": p["label"],
            "account": p["account"],
            "clearance": p["clearance"],
            "clearance_label": p["clearance_label"],
            "color": p["color"],
            "path": p["path"],
            "exists": res["exists"],
            "audit_status": res["status"],
            "violations_count": len(res.get("violations", [])),
            "origin_url": res.get("origin_url"),
            "author_email": res.get("author_email"),
        })

    return {
        "status": "clean" if total_violations == 0 else "alert",
        "shield_active": True,
        "air_gap_enforced": True,
        "total_projects": len(workspaces),
        "total_violations": total_violations,
        "projects": overview,
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S MSK"),
    }


@router.post("/audit")
async def run_security_audit(req: AuditRequest):
    """Executes on-demand live Security Shield audit for a project or all projects."""
    start_time = time.time()
    results = []

    workspaces = await _persona_workspaces()
    target_projects = [p for p in workspaces if p["id"] == req.project_id] if req.project_id else workspaces
    if req.project_id and not target_projects:
        raise HTTPException(status_code=404, detail="Рабочее пространство не найдено")

    for p in target_projects:
        p_path = Path(p["path"])
        res = audit_path(p_path, nda_rule=nda_rule_for(p))
        results.append({
            "project_id": p["id"],
            "project_name": p["label"],
            "clearance_label": p["clearance_label"],
            "data": res,
        })

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    has_violations = any(r["data"].get("violations") for r in results)

    return {
        "status": "passed" if not has_violations else "violations_found",
        "elapsed_ms": elapsed_ms,
        "audited_count": len(results),
        "results": results,
    }
