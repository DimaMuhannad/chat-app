import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db import DatabaseService
from app.main import app

from .synthetic_persona import SYNTHETIC_PERSONA

PUBLIC_KEYS = {
    "id",
    "display_name",
    "short_name",
    "title",
    "organizations",
    "default_area",
    "task_areas",
    "ui",
}
AREA_KEYS = {"value", "label", "filter_label", "show_in_filter"}


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
    assert set(data) == PUBLIC_KEYS


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


@pytest.mark.anyio
async def test_persona_current_whitelist_only():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/persona/current")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == PUBLIC_KEYS
    assert set(data["ui"]) == {"texts"}
    assert isinstance(data["ui"]["texts"], dict) and data["ui"]["texts"]
    assert all(set(item) == AREA_KEYS for item in data["task_areas"])
    assert all(set(org) == {"name"} for org in data["organizations"].values())

    # Слова NDA, подстроки remote и пути пространств читаются из источников; в вывод не попадают
    # (булевы флаги), чтобы упавший тест не печатал чувствительные строки.
    body = json.dumps(data, ensure_ascii=False)
    workspaces = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    assert workspaces, "у персоны по умолчанию нет пространств"
    remote_substrings = [s for ws in workspaces for s in ws["forbidden_remote_substrings"]]
    paths = [ws["path"] for ws in workspaces]
    # слова NDA - данные пространств персоны (forbidden_keywords), а не константа обёртки shield
    nda_words = [word for ws in workspaces for word in ws["forbidden_keywords"]]
    assert remote_substrings and paths and nda_words
    leaked_nda = any(word.casefold() in body.casefold() for word in nda_words)
    leaked_remote = any(sub.casefold() in body.casefold() for sub in remote_substrings)
    leaked_path = any(path in body for path in paths)
    assert leaked_nda is False
    assert leaked_remote is False
    assert leaked_path is False
    assert ("${" in body) is False


@pytest.mark.anyio
async def test_task_areas_roundtrip_exact_unicode():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = (await client.get("/api/v1/persona/current")).json()
        row = await DatabaseService.get_persona(settings.PERSONA_ID)
        stored = [a["value"] for a in row["config"]["task_areas"]]
        assert [a["value"] for a in data["task_areas"]] == stored
        assert len(stored) >= 2

        # значения персоны + строки с эмодзи, амперсандом и «похожими» кодовыми точками
        composed = "\u0401"
        decomposed = "\u0415\u0308"
        values = stored + ["🧪 Лаб & Ко", composed, decomposed]
        created: list[int] = []
        try:
            for index, value in enumerate(values):
                res = await client.post(
                    "/api/v1/tasks", json={"title": f"Юникод-проверка {index}", "area": value}
                )
                assert res.status_code == 201
                created.append(res.json()["id"])
                assert res.json()["area"] == value
            for index, value in enumerate(values):
                listed = await client.get("/api/v1/tasks", params={"area": value})
                assert listed.status_code == 200
                ids = {t["id"] for t in listed.json()}
                assert created[index] in ids
                assert all(t["area"] == value for t in listed.json())
            # без нормализации Unicode: «Ё» и «Е + диакритика» - разные значения
            assert composed != decomposed
            only_composed = {t["id"] for t in (await client.get("/api/v1/tasks", params={"area": composed})).json()}
            assert created[-2] in only_composed and created[-1] not in only_composed
        finally:
            for task_id in created:
                await client.delete(f"/api/v1/tasks/{task_id}")


@pytest.mark.anyio
async def test_synthetic_persona_default_area_and_areas_differ(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        default = (await client.get("/api/v1/persona/current")).json()
        monkeypatch.setattr(settings, "PERSONA_ID", SYNTHETIC_PERSONA["id"])
        synthetic = (await client.get("/api/v1/persona/current")).json()
        assert synthetic["default_area"] != default["default_area"]
        assert synthetic["default_area"] == SYNTHETIC_PERSONA["default_area"]
        assert {a["value"] for a in synthetic["task_areas"]} != {a["value"] for a in default["task_areas"]}
        assert synthetic["default_area"] in {a["value"] for a in synthetic["task_areas"]}

        res = await client.post("/api/v1/tasks", json={"title": "Задача синтетической персоны"})
        try:
            assert res.status_code == 201
            assert res.json()["area"] == synthetic["default_area"]
        finally:
            if res.status_code == 201:
                await client.delete(f"/api/v1/tasks/{res.json()['id']}")


@pytest.mark.anyio
async def test_create_without_area_and_without_persona_is_503(monkeypatch):
    monkeypatch.setattr(settings, "PERSONA_ID", "net-takoy-persony")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for payload in ({"title": "Без персоны"}, {"title": "Без персоны", "area": ""}):
            res = await client.post("/api/v1/tasks", json=payload)
            assert res.status_code == 503
        res = await client.post("/api/v1/projects", json={"name": "Проект без персоны"})
        assert res.status_code == 503

        # явная область не требует персоны: строка владельца не подставляется, а заданная сохраняется
        res = await client.post("/api/v1/tasks", json={"title": "С явной областью", "area": "Своя"})
        try:
            assert res.status_code == 201
            assert res.json()["area"] == "Своя"
        finally:
            if res.status_code == 201:
                await client.delete(f"/api/v1/tasks/{res.json()['id']}")
