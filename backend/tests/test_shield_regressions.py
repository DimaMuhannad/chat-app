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
