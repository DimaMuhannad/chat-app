"""Характеризация NDA-чек-листа (PER-04, D-14, D-15): явный перечень проверок Web-аудита и shield.

Тесты работают на настоящих временных git-репозиториях. Правила NDA владельца читаются из таблицы
workspaces копии БД (литерал аккаунта в файл не пишется), слова NDA - из scripts/security_shield.py
во время теста. Секретные строки собираются из частей в рантайме: файл теста сам не содержит
совпадений с шаблонами секретов (Web-аудит сканирует первые 100 файлов, shield --all - все).

Правило вывода: assert сравнивает только числа, булевы флаги и префиксы; слова NDA и списки
нарушений в сообщения pytest не попадают. Идентификаторы пунктов (N01..N09, S01..S09, P02, P03)
соответствуют разделу «NDA-чек-лист» в 03-RESEARCH.md.

Известное расхождение, зафиксированное без выравнивания (закрывает Фаза 4, SEC-01/02): Web-аудит не
проверяет слова NDA, скрипты проверяют их во всех НЕ-NDA репозиториях.
"""

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import security
from app.core.config import settings
from app.db import DatabaseService
from app.main import app

from .synthetic_persona import SYNTHETIC_PERSONA

SHIELD_PATH = Path(__file__).resolve().parents[2] / "scripts" / "security_shield.py"
GENERIC_BEARER = "Generic Bearer Secret"


def make_repo(root: Path, remote: str | None, files: dict[str, str]) -> Path:
    """Настоящий временный git-репозиторий: init, автор, origin (если задан), файлы в индексе."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "synthetic@example.org"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "synthetic"], cwd=root, check=True)
    if remote:
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=root, check=True)
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def _load_shield():
    spec = importlib.util.spec_from_file_location("_nda_equivalence_shield", SHIELD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _owner_nda_workspace() -> dict:
    """Строка restricted_nda персоны settings.PERSONA_ID из workspaces копии БД (списки декодированы)."""
    uri = Path(settings.SQLITE_DB_PATH).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, label, path, clearance, account, clearance_label, color, remote, "
            "forbidden_remote_substrings, forbidden_keywords, remote_violation_message "
            "FROM workspaces WHERE persona_id = ? AND clearance = 'restricted_nda' "
            "ORDER BY position LIMIT 1;",
            (settings.PERSONA_ID,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "у персоны нет NDA-пространства в копии БД"
    ws = dict(row)
    ws["forbidden_remote_substrings"] = json.loads(ws["forbidden_remote_substrings"] or "[]")
    ws["forbidden_keywords"] = json.loads(ws["forbidden_keywords"] or "[]")
    return ws


def _owner_remote() -> str:
    """Remote, содержащий запрещённую подстроку владельца (берётся из данных пространства)."""
    substring = _owner_nda_workspace()["forbidden_remote_substrings"][0]
    return "https://" + substring + "/synthetic-repo.git"


OTHER_REMOTE = "https://git.synthetic.example/other/repo.git"


# --- адаптер к API security.py: единственное место, меняемое при переходе на данные ---
def _audit(path: Path, nda: bool) -> dict:
    rule = security.nda_rule_for(_owner_nda_workspace()) if nda else None
    return security.audit_path(path, nda_rule=rule)
# --- конец адаптера ---


def _secret_samples() -> dict[str, str]:
    """Строки секретов для шаблонов Web-аудита; собираются из частей, литералов-совпадений нет."""
    return {
        "Private Key": "-----BEGIN " + "RSA" + " PRIVATE KEY" + "-----",
        "GitHub Personal Access Token": "ghp_" + "a" * 36,
        "Google API Key": "AIzaSy" + "a" * 33,
        "Telegram Bot Token": "123456789" + ":" + "a" * 35,
        "OpenAI/Anthropic API Key": "sk-" + "a" * 24,
        "Notion API Token": "ntn_" + "a" * 44,
    }


# --------------------------- Web (security.py): N01-N09 ---------------------------


@pytest.mark.parametrize("nda", [True, False])
def test_n01_missing_dir_is_virtual_airgap(tmp_path, nda):
    res = _audit(tmp_path / "net-takogo-kataloga", nda)
    assert res["exists"] is False
    assert res["status"] == "virtual_airgap"
    assert res["scanned_files"] == 0
    assert res["origin_url"] == "N/A"
    assert res["author_email"] == "N/A"
    assert "изолирована" in res["message"]
    assert res["violations"] == []


def test_n02_nda_remote_with_forbidden_substring_is_violation(tmp_path):
    repo = make_repo(tmp_path / "repo", _owner_remote(), {"README.txt": "synthetic\n"})
    res = _audit(repo, True)
    count = len(res["violations"])
    starts = res["violations"][0].startswith("CRITICAL:")
    assert count == 1
    assert starts
    assert res["status"] == "violations"


def test_n03_nda_remote_without_substring_is_clean(tmp_path):
    repo = make_repo(tmp_path / "repo", OTHER_REMOTE, {"README.txt": "synthetic\n"})
    res = _audit(repo, True)
    assert res["violations"] == []
    assert res["status"] == "passed"


def test_n04_non_nda_with_same_remote_is_clean(tmp_path):
    repo = make_repo(tmp_path / "repo", _owner_remote(), {"README.txt": "synthetic\n"})
    res = _audit(repo, False)
    assert res["violations"] == []
    assert res["status"] == "passed"


def test_n05_nda_without_origin_is_clean(tmp_path):
    repo = make_repo(tmp_path / "repo", None, {"README.txt": "synthetic\n"})
    res = _audit(repo, True)
    assert res["violations"] == []
    assert res["origin_url"] == "None"


@pytest.mark.parametrize(
    "name",
    [".env", ".env.local", "credentials.json", "token.json", "x.session", "x.session-journal", "k.pem", "k.key"],
)
def test_n06_forbidden_file_names_flagged(tmp_path, name):
    repo = make_repo(tmp_path / "repo", None, {name: "synthetic\n"})
    res = _audit(repo, False)
    count = len(res["violations"])
    flagged = res["violations"][0].startswith("Запрещенный файл обнаружен в репозитории:")
    assert count == 1
    assert flagged
    assert res["status"] == "violations"


@pytest.mark.parametrize("name", [n for n, _ in security.SECRET_PATTERNS])
def test_n07_secret_patterns_flagged(tmp_path, name):
    samples = _secret_samples()
    assert name in samples
    repo = make_repo(tmp_path / "repo", None, {"notes.txt": samples[name] + "\n"})
    res = _audit(repo, False)
    count = len(res["violations"])
    named = f"({name})" in res["violations"][0]
    assert count == 1
    assert named
    assert res["status"] == "violations"


def test_n08_web_scans_only_first_100_files(tmp_path):
    secret = _secret_samples()["GitHub Personal Access Token"]
    files = {f"f{i:03d}.txt": "synthetic\n" for i in range(100)}
    files["f100.txt"] = secret + "\n"  # последний по сортировке git ls-files, за окном в 100 файлов
    repo = make_repo(tmp_path / "repo", None, files)
    res = _audit(repo, False)
    assert res["scanned_files"] == 100
    assert res["violations"] == []
    assert res["status"] == "passed"


def test_n09_git_timeout_returns_error_tuple(monkeypatch):
    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=10)

    monkeypatch.setattr(security.subprocess, "run", boom)
    code, text = security.run_cmd(["git", "status"])
    assert code == 1
    assert isinstance(text, str)


# --------------------------- скрипты (security_shield.py): S01-S09 ---------------------------


def test_s01_script_detects_nda_by_path_substring(tmp_path, capsys):
    shield = _load_shield()
    nda_repo = make_repo(tmp_path / "Tydex-X" / "repo", _owner_remote(), {"README.txt": "synthetic\n"})
    code = shield.audit_repository(nda_repo)
    out = capsys.readouterr().out
    restricted = "RESTRICTED" in out
    critical = "CRITICAL" in out
    assert code == 1
    assert restricted
    assert critical
    plain_repo = make_repo(tmp_path / "plain" / "repo", OTHER_REMOTE, {"README.txt": "synthetic\n"})
    plain_code = shield.audit_repository(plain_repo)
    plain_out = capsys.readouterr().out
    public = "PUBLIC" in plain_out
    assert plain_code == 0
    assert public


def test_s02_script_nda_remote_violation(tmp_path, capsys):
    shield = _load_shield()
    repo = make_repo(tmp_path / "tydex-work" / "repo", _owner_remote(), {"README.txt": "synthetic\n"})
    code = shield.audit_repository(repo)
    out = capsys.readouterr().out
    critical = "CRITICAL" in out
    assert code == 1
    assert critical


def test_s03_script_non_nda_same_remote_is_clean(tmp_path):
    shield = _load_shield()
    repo = make_repo(tmp_path / "plain" / "repo", _owner_remote(), {"README.txt": "synthetic\n"})
    assert shield.audit_repository(repo) == 0


def test_s04_script_flags_each_keyword_in_public_repo(tmp_path):
    shield = _load_shield()
    keywords = list(shield.CORPORATE_NDA_KEYWORDS)
    total = len(keywords)
    assert total >= 1, "список слов shield пуст"
    for index, word in enumerate(keywords):
        target = tmp_path / f"kw{index}.txt"
        target.write_text("line with " + word + " inside\n", encoding="utf-8")
        found = shield.check_file_content(target, is_public_repo=True)
        count = len(found)
        flagged = "Found proprietary corporate keyword" in found[0]
        assert count == 1, f"слово с номером {index}: нарушений {count}"
        assert flagged, f"слово с номером {index}: нет сообщения о ключевом слове"


def test_s05_script_ignores_keywords_in_nda_repo(tmp_path):
    shield = _load_shield()
    for index, word in enumerate(shield.CORPORATE_NDA_KEYWORDS):
        target = tmp_path / f"kw{index}.txt"
        target.write_text("line with " + word + " inside\n", encoding="utf-8")
        found = shield.check_file_content(target, is_public_repo=False)
        count = len(found)
        assert count == 0, f"слово с номером {index}: нарушений {count}"


def test_s06_script_secret_patterns_include_generic_bearer(tmp_path):
    shield = _load_shield()
    names = [n for n, _ in shield.SECRET_PATTERNS]
    assert len(names) == 7
    assert GENERIC_BEARER in names
    quote = "'"
    for key in ("API" + "_KEY", "api" + "_key"):
        line = key + " = " + quote + "a" * 20 + quote + "\n"
        target = tmp_path / "cfg.txt"
        target.write_text(line, encoding="utf-8")
        found = shield.check_file_content(target, is_public_repo=False)
        count = len(found)
        named = GENERIC_BEARER in found[0]
        assert count == 1
        assert named


def test_s07_script_forbidden_file_short_circuits(tmp_path):
    shield = _load_shield()
    target = tmp_path / ".env"
    target.write_text(_secret_samples()["GitHub Personal Access Token"] + "\n", encoding="utf-8")
    found = shield.check_file_content(target, is_public_repo=True)
    count = len(found)
    flagged = found[0].startswith("Forbidden file pattern committed")
    assert count == 1
    assert flagged


def test_s08_script_all_mode_reads_all_tracked_files(tmp_path):
    shield = _load_shield()
    files = {f"f{i:03d}.txt": "synthetic\n" for i in range(101)}
    repo = make_repo(tmp_path / "repo", None, files)
    assert len(shield.get_staged_or_tracked_files(repo, check_staged_only=False)) == 101
    assert len(shield.get_staged_or_tracked_files(repo, check_staged_only=True)) == 101
    subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    (repo / "g000.txt").write_text("synthetic\n", encoding="utf-8")
    subprocess.run(["git", "add", "g000.txt"], cwd=repo, check=True)
    (repo / "f001.txt").write_text("changed\n", encoding="utf-8")
    # staged имеет приоритет над modified; режим all видит все отслеживаемые файлы без лимита
    assert shield.get_staged_or_tracked_files(repo, check_staged_only=True) == ["g000.txt"]
    assert len(shield.get_staged_or_tracked_files(repo, check_staged_only=False)) == 102
    subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "next"], cwd=repo, check=True)
    (repo / "f001.txt").write_text("changed again\n", encoding="utf-8")
    assert shield.get_staged_or_tracked_files(repo, check_staged_only=True) == ["f001.txt"]


def test_s09_script_read_error_is_violation(tmp_path, monkeypatch):
    shield = _load_shield()
    target = tmp_path / "plain.txt"
    target.write_text("synthetic\n", encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("synthetic denied")

    monkeypatch.setattr(shield, "open", boom, raising=False)
    found = shield.check_file_content(target, is_public_repo=True)
    count = len(found)
    flagged = "Read error" in found[0]
    assert count == 1
    assert flagged


# --------------------------- паритет и дрейф: P02, P03 ---------------------------


def test_p02_web_patterns_subset_of_script():
    shield = _load_shield()
    web = {n: p.pattern for n, p in security.SECRET_PATTERNS}
    script = {n: p.pattern for n, p in shield.SECRET_PATTERNS}
    assert set(web) <= set(script)
    assert set(script) - set(web) == {GENERIC_BEARER}
    same = all(web[n] == script[n] for n in web)
    assert same
    assert [p.pattern for p in security.FORBIDDEN_FILES] == [p.pattern for p in shield.FORBIDDEN_FILES]


def test_p03_shield_copies_identical():
    core = Path(os.environ.get("ASSISTANT_CORE_DIR", "/opt/assistant-core"))
    if not core.is_dir():
        pytest.skip("assistant-core not available in isolated test mode")
    other = core / "scripts" / "security_shield.py"
    assert other.is_file(), "копия shield в assistant-core не найдена"
    mine = hashlib.sha256(SHIELD_PATH.read_bytes()).hexdigest()
    theirs = hashlib.sha256(other.read_bytes()).hexdigest()
    assert mine == theirs


# --------------------------- правила из данных: D01, D02, 503 ---------------------------


def _synthetic_ids() -> list[str]:
    return [ws["id"] for ws in SYNTHETIC_PERSONA["workspaces"]]


@pytest.mark.anyio
async def test_d01_owner_rules_come_from_data():
    rows = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    assert len(rows) == 4
    owner = _owner_nda_workspace()
    rule = security.nda_rule_for(owner)
    assert rule is not None
    assert set(rule.forbidden_remote_substrings) == set(owner["forbidden_remote_substrings"])
    assert len(rule.forbidden_remote_substrings) == len(owner["forbidden_remote_substrings"])
    same_message = rule.violation_message == (owner["remote_violation_message"] or security.DEFAULT_REMOTE_VIOLATION)
    assert same_message
    # признак NDA - допуск пространства: у остальных пространств правила нет
    for row in rows:
        has_rule = security.nda_rule_for(row) is not None
        assert has_rule == (row["clearance"] == "restricted_nda")


@pytest.mark.anyio
async def test_d02_synthetic_overview_lists_its_workspaces(monkeypatch):
    monkeypatch.setattr(settings, "PERSONA_ID", SYNTHETIC_PERSONA["id"])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/security/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_projects"] == 3
    assert [p["id"] for p in data["projects"]] == _synthetic_ids()
    assert all(p["audit_status"] == "virtual_airgap" for p in data["projects"])
    assert {p["clearance"] for p in data["projects"]} == {"public", "internal", "restricted_nda"}


@pytest.mark.anyio
async def test_d02_synthetic_rule_applies_only_its_data(tmp_path):
    # PERSONA_ID не подменяется: правила владельца берутся из его данных, синтетические - по явному id
    rows = await DatabaseService.list_workspaces(SYNTHETIC_PERSONA["id"])
    nda_rows = [r for r in rows if r["clearance"] == "restricted_nda"]
    assert len(nda_rows) == 1
    synthetic_ws = nda_rows[0]
    rule = security.nda_rule_for(synthetic_ws)
    assert rule is not None
    assert synthetic_ws["forbidden_remote_substrings"]
    own_remote = "https://" + synthetic_ws["forbidden_remote_substrings"][0] + "/x.git"

    # правило синтетической персоны ловит её подстроку и даёт её сообщение
    own_repo = make_repo(tmp_path / "own", own_remote, {"README.txt": "synthetic\n"})
    res = security.audit_path(own_repo, nda_rule=rule)
    count = len(res["violations"])
    message_ok = res["violations"][0] == rule.violation_message
    assert count == 1
    assert message_ok

    # подстрока владельца для синтетического правила не нарушение
    owner_repo = make_repo(tmp_path / "owner", _owner_remote(), {"README.txt": "synthetic\n"})
    assert security.audit_path(owner_repo, nda_rule=rule)["violations"] == []

    # правило владельца не действует на подстроку синтетической персоны
    owner_rule = security.nda_rule_for(_owner_nda_workspace())
    assert security.audit_path(own_repo, nda_rule=owner_rule)["violations"] == []

    # в сообщении синтетического правила нет названий организаций владельца
    row = await DatabaseService.get_persona("popov-da-default")
    config = row["config"].get("persona", row["config"])
    names: list[str] = []
    for org in config["organizations"].values():
        names.append(org["name"])
        names.extend(org.get("aliases") or [])
    low = rule.violation_message.casefold()
    leaked = any(len(n) >= 3 and n.casefold() in low for n in names)
    assert not leaked


@pytest.mark.anyio
async def test_overview_and_audit_503_without_workspaces(monkeypatch):
    monkeypatch.setattr(settings, "PERSONA_ID", "net-takoy-persony")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overview = await client.get("/api/v1/security/overview")
        audit = await client.post("/api/v1/security/audit", json={})
        single = await client.post("/api/v1/security/audit", json={"project_id": "chat-app"})
    assert overview.status_code == 503
    assert audit.status_code == 503
    assert single.status_code == 503


def test_normalize_remote_matches_case_and_scp_forms():
    """WR-07: регистр, scp-форма, ssh:// и .git не обходят подстроку запрещённого remote."""
    from app.api.v1.security import normalize_remote

    needle = normalize_remote("example.org/Owner")
    for url in (
        "https://example.org/OWNER/repo.git",
        "git@example.org:owner/repo.git",
        "ssh://git@Example.org/owner/repo/",
        "https://user:token@example.org/owner/repo",
    ):
        assert needle in normalize_remote(url), url
    assert needle not in normalize_remote("git@example.org:other/repo.git")
