import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_security_overview():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/security/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["shield_active"] is True
        assert data["air_gap_enforced"] is True
        assert "projects" in data
        assert len(data["projects"]) == 4
        # Verify Tydex project has restricted clearance
        tydex = next(p for p in data["projects"] if p["id"] == "tydex-optics")
        assert tydex["clearance"] == "restricted_nda"


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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={"project_id": "chat-app"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["audited_count"] == 1
        assert data["results"][0]["project_id"] == "chat-app"
        assert data["results"][0]["data"]["exists"] is True
