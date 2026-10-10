"""Web-аудит ищет слова NDA других пространств в каталогах НЕ-NDA пространств (SECF-02, D-12).

Пространства подменяются синтетическим набором из двух каталогов во временной папке: публичное (без слов)
и NDA (слова из данных копии БД). Слово NDA собирается в рантайме из данных и в файл теста не пишется;
assert сравнивает только числа и булевы флаги, слова в сообщения не попадают.
"""

import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import DatabaseService
from app.main import app

from .nda_helpers import owner_nda_keywords

PUBLIC_ID = "ws-pub"
NDA_ID = "ws-nda"


def _git_repo_with_keyword(root: Path, word: str) -> Path:
    """Git-репозиторий без remote: один отслеживаемый файл со словом NDA (индекс заполнен)."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "synthetic@example.org"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "synthetic"], cwd=root, check=True)
    (root / "notes.txt").write_text("line with " + word + " inside\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def _workspace(ws_id: str, path: Path, clearance: str, keywords: list[str], substrings: list[str]) -> dict:
    return {
        "id": ws_id,
        "position": 0,
        "label": ws_id,
        "path": str(path),
        "clearance": clearance,
        "account": "synthetic@example.org",
        "clearance_label": clearance,
        "color": "gray",
        "remote": "https://git.example.org/ws/data.git",
        "forbidden_remote_substrings": substrings,
        "forbidden_keywords": keywords,
        "remote_violation_message": None,
    }


@pytest.fixture
def two_workspaces(tmp_path, monkeypatch):
    """Публичное пространство (слов нет) и NDA (слова из данных); в обоих каталогах файл со словом NDA."""
    keywords = owner_nda_keywords()
    pub = _git_repo_with_keyword(tmp_path / "pub", keywords[0])
    nda = _git_repo_with_keyword(tmp_path / "nda", keywords[0])
    rows = [
        _workspace(PUBLIC_ID, pub, "public", [], []),
        _workspace(NDA_ID, nda, "restricted_nda", keywords, ["git.example.org/ws-nda"]),
    ]

    async def fake_list_workspaces(persona_id: str):
        return rows

    monkeypatch.setattr(DatabaseService, "list_workspaces", staticmethod(fake_list_workspaces))
    return keywords


def _by_id(results: list[dict]) -> dict[str, dict]:
    return {item["project_id"]: item["data"] for item in results}


@pytest.mark.anyio
async def test_audit_finds_nda_keyword_in_public_workspace_only(two_workspaces):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={})
    assert resp.status_code == 200
    body = resp.json()
    data = _by_id(body["results"])
    assert body["status"] == "violations_found"
    assert body["audited_count"] == 2
    assert len(data[PUBLIC_ID]["violations"]) == 1
    assert data[PUBLIC_ID]["status"] == "violations"
    # в NDA-каталоге те же слова законны
    assert data[NDA_ID]["violations"] == []
    leaked = any(word.casefold() in resp.text.casefold() for word in two_workspaces)
    assert leaked is False


@pytest.mark.anyio
async def test_audit_of_public_project_uses_keywords_of_all_workspaces(two_workspaces):
    # выбрано только публичное пространство, у него своих слов нет: слова берутся по ВСЕМ пространствам
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/security/audit", json={"project_id": PUBLIC_ID})
    assert resp.status_code == 200
    body = resp.json()
    assert body["audited_count"] == 1
    data = _by_id(body["results"])
    assert len(data[PUBLIC_ID]["violations"]) == 1
    leaked = any(word.casefold() in resp.text.casefold() for word in two_workspaces)
    assert leaked is False


@pytest.mark.anyio
async def test_overview_counts_nda_keyword_in_public_workspace(two_workspaces):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/security/overview")
    assert resp.status_code == 200
    data = resp.json()
    counts = {p["id"]: p["violations_count"] for p in data["projects"]}
    assert counts[PUBLIC_ID] == 1
    assert counts[NDA_ID] == 0
    assert data["total_violations"] == 1
    assert data["status"] == "alert"
    leaked = any(word.casefold() in resp.text.casefold() for word in two_workspaces)
    assert leaked is False
