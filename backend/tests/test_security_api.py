import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db import DatabaseService
from app.main import app


@pytest.mark.anyio
async def test_security_overview():
    workspaces = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    nda_rows = [w for w in workspaces if w["clearance"] == "restricted_nda"]
    assert len(nda_rows) == 1
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/security/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["shield_active"] is True
        assert data["air_gap_enforced"] is True
        assert "projects" in data
        assert len(data["projects"]) == 4
        assert len(data["projects"]) == len(workspaces)
        # Verify the NDA workspace has restricted clearance (id taken from persona data)
        nda = next(p for p in data["projects"] if p["id"] == nda_rows[0]["id"])
        assert nda["clearance"] == "restricted_nda"


def _synthetic_workspaces(tmp_path: Path) -> list[dict]:
    """Четыре чистых пространства во временной папке (три уровня допуска), без слов NDA и секретов."""
    levels = ["public", "internal", "public", "restricted_nda"]
    rows = []
    for index, clearance in enumerate(levels):
        root = tmp_path / f"ws-{index}"
        root.mkdir()
        (root / "README.txt").write_text("synthetic\n", encoding="utf-8")
        # NDA-пространство без git не может считаться чистым (fail-closed), поэтому все каталоги - репозитории
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        rows.append({
            "id": f"ws-{index}",
            "position": index,
            "label": f"ws-{index}",
            "path": str(root),
            "clearance": clearance,
            "account": "synthetic@example.org",
            "clearance_label": clearance,
            "color": "gray",
            "remote": "https://git.example.org/ws/data.git",
            "forbidden_remote_substrings": ["git.example.org/ws-nda"] if clearance == "restricted_nda" else [],
            "forbidden_keywords": [],
            "remote_violation_message": None,
        })
    return rows


@pytest.mark.anyio
async def test_security_audit_all(tmp_path, monkeypatch):
    rows = _synthetic_workspaces(tmp_path)

    async def fake_list_workspaces(persona_id: str):
        return rows

    monkeypatch.setattr(DatabaseService, "list_workspaces", staticmethod(fake_list_workspaces))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "passed"
        assert data["audited_count"] == 4
        assert len(data["results"]) == 4


# Замороженный набор находок слов NDA на живом дереве (D-21: допусков нет, это известные находки
# публичных каталогов). Записи только удаляются; любая новая находка красит тест.
FROZEN_LIVE_KEYWORD_FINDINGS = {
    ("chat-app", ".planning/milestones/v2.0-phases/04-vladelets-shemy-bd-i-obschaya-biblioteka-bezopasnosti/04-REVIEW.md"),
    ("chat-app", "docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md"),
    ("assistant-core", "config/persona.yaml"),
}
KEYWORD_MESSAGE = "Обнаружено ключевое слово закрытого (NDA) пространства в публичном репозитории"


@pytest.mark.anyio
async def test_security_audit_all_live_tree_has_only_frozen_findings():
    workspaces = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["audited_count"] == len(workspaces) == 4
    assert len(data["results"]) == 4
    found: set[tuple[str, str]] = set()
    only_keyword_kind = True
    for item in data["results"]:
        for violation in item["data"]["violations"]:
            path, _, message = violation.partition(": ")
            found.add((item["project_id"], path))
            if message != KEYWORD_MESSAGE:
                only_keyword_kind = False
    unexpected = found - FROZEN_LIVE_KEYWORD_FINDINGS
    assert only_keyword_kind is True
    assert len(unexpected) == 0, f"новых находок: {len(unexpected)}"
    assert (data["status"] == "passed") == (len(found) == 0)


@pytest.mark.anyio
async def test_security_audit_single_project():
    workspaces = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    first_id = workspaces[0]["id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={"project_id": first_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["audited_count"] == 1
        assert data["results"][0]["project_id"] == first_id
        assert data["results"][0]["data"]["exists"] is True
