import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.db import DatabaseService

router = APIRouter(prefix="/security", tags=["Security Shield"])

# Common high-risk secret patterns
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Private Key", re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA|PGP)?\s*PRIVATE KEY-----")),
    ("GitHub Personal Access Token", re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})")),
    ("Google API Key", re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}")),
    ("Telegram Bot Token", re.compile(r"\b[0-9]{8,10}:[a-zA-Z0-9_-]{35}\b")),
    ("OpenAI/Anthropic API Key", re.compile(r"(sk-[a-zA-Z0-9]{20,}|sk-ant-[a-zA-Z0-9]{20,})")),
    ("Notion API Token", re.compile(r"(ntn_[a-zA-Z0-9]{40,}|secret_[a-zA-Z0-9]{40,})")),
]

FORBIDDEN_FILES: list[re.Pattern] = [
    re.compile(r"(^|/)\.env(\.(local|dev|development|prod|production|staging|secrets))?$"),
    re.compile(r"(^|/)credentials\.json$"),
    re.compile(r"(^|/)token\.json$"),
    re.compile(r".+\.session$"),
    re.compile(r".+\.session-journal$"),
    re.compile(r".+\.(pem|key|pkcs12|pfx)$"),
]

# Нейтральное сообщение, если у NDA-пространства не задан свой текст нарушения (без названий организаций).
DEFAULT_REMOTE_VIOLATION = "CRITICAL: remote рабочего пространства указывает на запрещённый аккаунт!"


@dataclass(frozen=True)
class NdaRemoteRule:
    """Правило remote для NDA-пространства: запрещённые подстроки origin и текст нарушения (данные пространства)."""

    forbidden_remote_substrings: tuple[str, ...]
    violation_message: str


def nda_rule_for(ws: dict[str, Any]) -> NdaRemoteRule | None:
    """Правило NDA только для пространства с допуском restricted_nda (признак - допуск, не id и не префикс)."""
    if ws.get("clearance") != "restricted_nda":
        return None
    return NdaRemoteRule(
        forbidden_remote_substrings=tuple(s for s in (ws.get("forbidden_remote_substrings") or ()) if s),
        violation_message=ws.get("remote_violation_message") or DEFAULT_REMOTE_VIOLATION,
    )


async def _persona_workspaces() -> list[dict[str, Any]]:
    """Пространства персоны из БД; пусто - 503 (fail-closed: не «0 проектов, чисто»)."""
    workspaces = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    if not workspaces:
        raise HTTPException(status_code=503, detail="Рабочие пространства персоны не загружены в базу данных")
    return workspaces


def normalize_remote(url: str) -> str:
    """Привести адрес remote к виду host/owner/repo в нижнем регистре (WR-07).

    Адреса GitHub регистронезависимы, а один репозиторий записывается по-разному:
    https://host/owner/repo.git, ssh://git@host/owner/repo, git@host:owner/repo (scp-форма).
    """
    value = url.strip().casefold()
    scheme_form = "://" in value
    if scheme_form:
        value = value.split("://", 1)[1]
    value = value.rsplit("@", 1)[-1] if "@" in value.split("/", 1)[0] else value
    if not scheme_form:
        value = value.replace(":", "/", 1)  # scp-форма host:owner/repo
    return value.rstrip("/").removesuffix(".git").rstrip("/")


def run_cmd(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    try:
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return res.returncode, res.stdout.strip()
    except Exception as e:
        return 1, str(e)


def audit_path(target_path: Path, nda_rule: NdaRemoteRule | None = None) -> dict[str, Any]:
    if not target_path.exists():
        return {
            "exists": False,
            "status": "virtual_airgap",
            "message": "Директория изолирована или еще не склонирована на данном сервере (Air-gap активен)",
            "scanned_files": 0,
            "violations": [],
            "origin_url": "N/A",
            "author_email": "N/A",
        }

    code, origin_url = run_cmd(["git", "remote", "get-url", "origin"], cwd=str(target_path))
    code_user, user_email = run_cmd(["git", "config", "user.email"], cwd=str(target_path))

    violations = []
    if nda_rule is not None and not nda_rule.forbidden_remote_substrings:
        # Fail-closed: NDA-пространство без правил remote не может считаться чистым.
        violations.append("CRITICAL: у NDA-пространства не заданы правила remote (fail-closed)")
    if nda_rule is not None and code == 0:
        origin_norm = normalize_remote(origin_url)
        if any(
            norm_sub and norm_sub in origin_norm
            for norm_sub in (normalize_remote(sub) for sub in nda_rule.forbidden_remote_substrings)
        ):
            violations.append(nda_rule.violation_message)

    # Scan tracked and modified files
    code_files, out_files = run_cmd(["git", "ls-files"], cwd=str(target_path))
    files_to_scan = [line.strip() for line in out_files.splitlines() if line.strip()][:100]  # Limit to 100 files for fast API

    for rel_path in files_to_scan:
        full_path = target_path / rel_path
        str_path = str(full_path).replace("\\", "/")
        for pattern in FORBIDDEN_FILES:
            if pattern.search(str_path):
                violations.append(f"Запрещенный файл обнаружен в репозитории: {rel_path}")

        if full_path.is_file():
            try:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                for name, pat in SECRET_PATTERNS:
                    if pat.search(content):
                        violations.append(f"{rel_path}: Обнаружен потенциальный секрет ({name})")
            except Exception:
                pass

    return {
        "exists": True,
        "status": "passed" if not violations else "violations",
        "scanned_files": len(files_to_scan),
        "violations": violations,
        "origin_url": origin_url if code == 0 else "None",
        "author_email": user_email if code_user == 0 else "Not configured",
    }


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
