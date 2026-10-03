"""Эталон вывода Security Tile (BCK-01, D-14): 4 записи в порядке сегодняшнего реестра.

Значения дословно из реестра backend/app/api/v1/security.py до перевода на данные. Файл не меняется
после коммита характеризации: он доказывает, что вывод из данных персоны совпадает с прежним.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

GOLDEN = [
    (
        "chat-app",
        "🤖 Antigravity Web Studio (chat-app)",
        "DimaMuhannad (Personal / Academic)",
        "public",
        "🌐 Public / Open Source",
        "blue",
        "/opt/chat-app",
    ),
    (
        "assistant-core",
        "⚙️ Assistant Core Daemon",
        "DimaMuhannad (Personal / Academic)",
        "public",
        "🌐 Public / Academic",
        "green",
        "/opt/assistant-core",
    ),
    (
        "tydex-optics",
        "🔬 Оптические приборы и измерения (ООО «Тидекс»)",
        "ООО «Тидекс» (Corporate Organization)",
        "restricted_nda",
        "🔴 Restricted NDA / Air-gap",
        "red",
        "/opt/work-tydex",
    ),
    (
        "guap-physics",
        "🏛️ Кафедра физики ГУАП (Лабораторные и LMS)",
        "DimaMuhannad (ГУАП)",
        "internal",
        "🟡 Internal Academic",
        "yellow",
        "/opt/personal/guap-physics",
    ),
]

RECORD_KEYS = {
    "id",
    "name",
    "account",
    "clearance",
    "clearance_label",
    "color",
    "path",
    "exists",
    "audit_status",
    "violations_count",
    "origin_url",
    "author_email",
}
TOP_KEYS = {
    "status",
    "shield_active",
    "air_gap_enforced",
    "total_projects",
    "total_violations",
    "projects",
    "last_checked",
}


@pytest.mark.anyio
async def test_overview_golden_matches_today():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/security/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == TOP_KEYS
    assert data["total_projects"] == 4
    projects = data["projects"]
    assert len(projects) == 4
    for record in projects:
        assert set(record) == RECORD_KEYS
    projection = [
        (p["id"], p["name"], p["account"], p["clearance"], p["clearance_label"], p["color"], p["path"])
        for p in projects
    ]
    assert projection == GOLDEN
    by_id = {p["id"]: p for p in projects}
    for airgap_id in ("tydex-optics", "guap-physics"):
        assert by_id[airgap_id]["exists"] is False
        assert by_id[airgap_id]["audit_status"] == "virtual_airgap"
    for present_id in ("chat-app", "assistant-core"):
        assert by_id[present_id]["exists"] is True


@pytest.mark.anyio
async def test_audit_all_golden_order():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={})
    assert resp.status_code == 200
    data = resp.json()
    results = data["results"]
    assert [r["project_id"] for r in results] == [row[0] for row in GOLDEN]
    assert [r["clearance_label"] for r in results] == [row[4] for row in GOLDEN]
    assert [r["project_name"] for r in results] == [row[1] for row in GOLDEN]
    assert data["audited_count"] == 4
