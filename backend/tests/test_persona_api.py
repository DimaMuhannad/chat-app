import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db import DatabaseService
from app.main import app

from .synthetic_persona import SYNTHETIC_PERSONA

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


@pytest.mark.anyio
async def test_synthetic_persona_current_differs(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        default = await client.get("/api/v1/persona/current")
        monkeypatch.setattr(settings, "PERSONA_ID", SYNTHETIC_PERSONA["id"])
        synthetic = await client.get("/api/v1/persona/current")
    assert default.status_code == 200
    assert synthetic.status_code == 200
    data = synthetic.json()
    assert data["id"] == SYNTHETIC_PERSONA["id"]
    assert data["display_name"] == SYNTHETIC_PERSONA["display_name"]
    assert data["display_name"] != default.json()["display_name"]
    assert data["default_area"] == SYNTHETIC_PERSONA["default_area"]
