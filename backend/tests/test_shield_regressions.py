"""Регрессионные тесты fail-closed поведения shield (04-REVIEW CR-01..CR-05, CR-07).

Секретные строки собираются из частей, чтобы файл теста сам не совпадал с шаблонами секретов.
"""

import subprocess
from pathlib import Path

import pytest

from assistant_shared.security import audit_path, audit_repository
from assistant_shared.security.runner import GitError, get_staged_or_tracked_files

SECRET_LINE = "api" + "_key = '" + "a" * 20 + "'\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _init(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "synthetic@example.org")
    _git(repo, "config", "user.name", "synthetic")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


def _commit(repo: Path, message: str = "c") -> None:
    _git(repo, "commit", "-q", "-m", message)


# --------------------------- CR-01 ---------------------------


def test_cr01_renamed_forbidden_file_is_scanned(tmp_path, capsys):
    repo = _init(tmp_path / "repo")
    (repo / "cfg.txt").write_text("synthetic\n", encoding="utf-8")
    _git(repo, "add", "cfg.txt")
    _commit(repo)
    _git(repo, "mv", "cfg.txt", "credentials.json")
    assert get_staged_or_tracked_files(repo, check_staged_only=True) == ["credentials.json"]
    assert audit_repository(repo) == 1
    assert "Forbidden file pattern" in capsys.readouterr().out


def test_cr01_non_ascii_file_name_is_scanned(tmp_path, capsys):
    repo = _init(tmp_path / "repo")
    (repo / "секрет.py").write_text(SECRET_LINE, encoding="utf-8")
    _git(repo, "add", "-A")
    assert get_staged_or_tracked_files(repo, check_staged_only=True) == ["секрет.py"]
    assert audit_repository(repo) == 1
    assert "Generic Bearer Secret" in capsys.readouterr().out


def test_cr01_git_failure_is_fail_closed(tmp_path, capsys):
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    with pytest.raises(GitError):
        get_staged_or_tracked_files(not_a_repo, check_staged_only=True)
    assert audit_repository(not_a_repo) == 1
    assert "SECURITY SHIELD ERROR" in capsys.readouterr().out


# --------------------------- CR-03 ---------------------------


def test_cr03_staged_secret_is_found_after_worktree_cleanup(tmp_path, capsys):
    repo = _init(tmp_path / "repo")
    (repo / "leak.txt").write_text(SECRET_LINE, encoding="utf-8")
    _git(repo, "add", "leak.txt")
    (repo / "leak.txt").write_text("clean\n", encoding="utf-8")  # рабочая копия чистая, индекс нет
    assert audit_repository(repo) == 1
    assert "Generic Bearer Secret" in capsys.readouterr().out


def test_cr03_staged_clean_version_passes_despite_dirty_worktree(tmp_path):
    repo = _init(tmp_path / "repo")
    (repo / "ok.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "ok.txt")
    (repo / "ok.txt").write_text(SECRET_LINE, encoding="utf-8")  # не проиндексировано, в коммит не попадёт
    assert audit_repository(repo) == 0


# --------------------------- CR-02 ---------------------------

SHIELD = Path(__file__).resolve().parents[2] / "scripts" / "security_shield.py"


def _run_shield(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    import sys

    return subprocess.run([sys.executable, str(SHIELD), *args], cwd=cwd, capture_output=True, text=True)


def test_cr02_flag_first_is_not_treated_as_path(tmp_path):
    repo = _init(tmp_path / "repo")
    (repo / "leak.txt").write_text(SECRET_LINE, encoding="utf-8")
    _git(repo, "add", "leak.txt")
    res = _run_shield("--all", cwd=repo)
    assert res.returncode == 1
    assert "Generic Bearer Secret" in res.stdout
    res_path = _run_shield("--all", str(repo), cwd=tmp_path)
    assert res_path.returncode == 1


def test_cr02_unknown_flag_and_missing_path_fail(tmp_path):
    assert _run_shield("--bogus", cwd=tmp_path).returncode != 0
    assert _run_shield(str(tmp_path / "net-takogo"), cwd=tmp_path).returncode == 1
    plain = tmp_path / "plain"
    plain.mkdir()
    assert audit_repository(plain, check_staged_only=False) == 1


# --------------------------- CR-04 ---------------------------


def test_cr04_truncated_audit_is_not_passed(tmp_path):
    repo = _init(tmp_path / "repo")
    for i in range(12):
        (repo / f"f{i:02d}.txt").write_text("synthetic\n", encoding="utf-8")
    _git(repo, "add", "-A")
    res = audit_path(repo, max_files=10)
    assert res["scanned_files"] == 10
    assert res["status"] == "violations"
    assert any("неполный" in v for v in res["violations"])


def test_cr04_hidden_parent_directory_and_dotenv_are_scanned(tmp_path):
    hidden_root = tmp_path / ".cache" / "ws"
    hidden_root.mkdir(parents=True)
    (hidden_root / "notes.txt").write_text(SECRET_LINE, encoding="utf-8")
    (hidden_root / ".env").write_text("synthetic\n", encoding="utf-8")
    res = audit_path(hidden_root)  # каталог без git: фолбэк по файловой системе
    assert res["scanned_files"] == 2
    assert res["status"] == "violations"
    assert len(res["violations"]) == 2


def test_cr04_unreadable_file_is_violation(tmp_path, monkeypatch):
    target = tmp_path / "ws"
    target.mkdir()
    (target / "a.txt").write_text("synthetic\n", encoding="utf-8")

    def boom(self, *args, **kwargs):
        raise OSError("synthetic denied")

    monkeypatch.setattr(Path, "read_text", boom)
    res = audit_path(target)
    assert res["status"] == "violations"
    assert "ошибка чтения" in res["violations"][0]


def test_cr04_non_ascii_tracked_file_is_scanned(tmp_path):
    repo = _init(tmp_path / "repo")
    (repo / "секрет.py").write_text(SECRET_LINE, encoding="utf-8")
    _git(repo, "add", "-A")
    res = audit_path(repo)
    assert res["status"] == "violations"


# --------------------------- CR-05 ---------------------------

from assistant_shared.security import NdaRemoteRule, normalize_remote  # noqa: E402

NDA_RULE = NdaRemoteRule(forbidden_remote_substrings=("example.org/owner",), violation_message="CRITICAL: synthetic")


@pytest.mark.parametrize(
    "url",
    [
        "ssh://git@example.org:22/Owner/r.git",
        "ssh://git@ssh.example.org:443/Owner/r.git",
        "https://www.example.org/OWNER/r",
        "git@example.org:owner/r.git",
    ],
)
def test_cr05_normalize_remote_port_and_host_alias(url):
    assert "example.org/owner" in normalize_remote(url)


def test_cr05_normalize_remote_does_not_match_other_owner():
    assert "example.org/owner" not in normalize_remote("ssh://git@ssh.example.org:443/other/r.git")


@pytest.mark.parametrize("url", ["ssh://git@ssh.example.org:443/Owner/r.git", "ssh://git@example.org:22/owner/r.git"])
def test_cr05_nda_origin_with_port_or_alias_is_violation(tmp_path, url):
    repo = _init(tmp_path / "repo")
    _git(repo, "remote", "add", "origin", url)
    res = audit_path(repo, nda_rule=NDA_RULE)
    assert res["violations"] == ["CRITICAL: synthetic"]


def test_cr05_nda_second_remote_and_pushurl_are_checked(tmp_path):
    repo = _init(tmp_path / "repo")
    _git(repo, "remote", "add", "origin", "https://git.example.net/team/r.git")
    _git(repo, "remote", "add", "personal", "https://example.org/owner/r.git")
    assert audit_path(repo, nda_rule=NDA_RULE)["violations"] == ["CRITICAL: synthetic"]

    repo2 = _init(tmp_path / "repo2")
    _git(repo2, "remote", "add", "origin", "https://git.example.net/team/r.git")
    _git(repo2, "remote", "set-url", "--push", "origin", "https://example.org/owner/r.git")
    assert audit_path(repo2, nda_rule=NDA_RULE)["violations"] == ["CRITICAL: synthetic"]


def test_cr05_nda_git_failure_is_fail_closed(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "a.txt").write_text("synthetic\n", encoding="utf-8")
    res = audit_path(plain, nda_rule=NDA_RULE)
    assert res["status"] == "violations"
    assert any("fail-closed" in v for v in res["violations"])
    # без NDA-правила тот же каталог остаётся чистым
    assert audit_path(plain)["status"] == "passed"


def test_cr05_cli_checks_all_remotes_and_aliases(tmp_path):
    nda_root = tmp_path / "tydex-work"
    repo = _init(nda_root / "repo")
    _git(repo, "remote", "add", "origin", "https://git.example.net/team/r.git")
    _git(repo, "remote", "add", "backup", "ssh://git@ssh.github.com:443/DimaMuhannad/r.git")
    assert audit_repository(repo) == 1

    repo2 = _init(nda_root / "repo2")
    _git(repo2, "remote", "add", "origin", "https://git.example.net/team/r.git")
    assert audit_repository(repo2) == 0


# --------------------------- CR-07 ---------------------------

from assistant_shared.security import FORBIDDEN_FILES, SECRET_PATTERNS  # noqa: E402


def _matches(text: str) -> list[str]:
    return [name for name, pat in SECRET_PATTERNS if pat.search(text)]


@pytest.mark.parametrize(
    "sample, expected",
    [
        ("sk-ant-" + "api03-" + "A1b2C3d4" * 4, "OpenAI/Anthropic API Key"),
        ("sk-" + "proj-" + "A1b2C3d4" * 4, "OpenAI/Anthropic API Key"),
        ("-----BEGIN " + "PGP PRIVATE KEY BLOCK-----", "Private Key"),
        ("-----BEGIN " + "ENCRYPTED PRIVATE KEY-----", "Private Key"),
        ("-----BEGIN " + "PRIVATE KEY-----", "Private Key"),
        ("-----BEGIN " + "OPENSSH PRIVATE KEY-----", "Private Key"),
        ("gho_" + "a" * 36, "GitHub Personal Access Token"),
        ("ghs_" + "a" * 36, "GitHub Personal Access Token"),
        ("github_pat_" + "A1b2C3d4" * 8, "GitHub Personal Access Token"),
        ("AKIA" + "ABCDEFGHIJKLMNOP", "AWS Access Key ID"),
        ("xox" + "b-123456789012-abcdefghij", "Slack Token"),
        ('{"api' + '_key": "' + "a" * 20 + '"}', "Generic Bearer Secret"),
    ],
)
def test_cr07_real_secret_formats_are_detected(sample, expected):
    assert expected in _matches(sample)


@pytest.mark.parametrize(
    "name",
    ["id_rsa", "id_ed25519", ".env.test", ".env.production.local", ".env.bak", "service-account-prod.json", ".npmrc", "a/b/id_ecdsa"],
)
def test_cr07_additional_forbidden_files(name):
    assert any(p.search(name) for p in FORBIDDEN_FILES)


@pytest.mark.parametrize("name", [".env.example", "README.md", "src/identity.py", "docs/account.json"])
def test_cr07_ordinary_files_are_not_forbidden(name):
    assert not any(p.search(name) for p in FORBIDDEN_FILES)


def test_cr07_ordinary_code_has_no_false_positives():
    assert _matches("risk-assessment-framework-document-for-the-team") == []
    assert _matches("api_key = settings.get_api_key()") == []
