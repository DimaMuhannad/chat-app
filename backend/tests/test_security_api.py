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


@pytest.mark.anyio
async def test_security_audit_all():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "passed"
        assert data["audited_count"] == 4
        assert len(data["results"]) == 4


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
