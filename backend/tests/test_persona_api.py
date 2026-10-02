import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db import DatabaseService
from app.main import app

PUBLIC_KEYS = {"id", "display_name", "short_name", "title", "organizations", "default_area"}


@pytest.mark.anyio
async def test_persona_current_returns_seeded_persona():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/persona/current")
    assert resp.status_code == 200
    data = resp.json()
    row = await DatabaseService.get_persona(settings.PERSONA_ID)
    assert row is not None
    assert data["id"] == settings.PERSONA_ID
    assert data["display_name"] == row["display_name"]
    assert set(data) <= PUBLIC_KEYS


@pytest.mark.anyio
async def test_persona_current_503_without_persona(monkeypatch):
    monkeypatch.setattr(settings, "PERSONA_ID", "net-takoy-persony")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/persona/current")
    assert resp.status_code == 503
