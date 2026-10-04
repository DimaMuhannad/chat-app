"""Интеграционные тесты pre-commit hook безопасности (SEC-03)."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

HOOK_SOURCE = Path(__file__).resolve().parents[2] / ".githooks" / "pre-commit"
SHIELD_SOURCE = Path(__file__).resolve().parents[2] / "scripts" / "security_shield.py"


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Инициализирует тестовый git-репозиторий с настроенным pre-commit хуком и базовым коммитом."""
    repo = tmp_path / "test_repo"
    repo.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(repo), check=True)

    # Установка .githooks/pre-commit
    hooks_dir = repo / ".githooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_dest = hooks_dir / "pre-commit"
    shutil.copy2(HOOK_SOURCE, hook_dest)
    hook_dest.chmod(0o755)

    # Настройка git config core.hooksPath
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=str(repo), check=True)

    # Копирование security_shield.py
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shield_dest = scripts_dir / "security_shield.py"
    shutil.copy2(SHIELD_SOURCE, shield_dest)
    shield_dest.chmod(0o755)

    # Создаём начальный коммит, чтобы HEAD существовал
    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo), check=True)
    _run_git_commit(repo, "chore: initial commit")

    return repo


def _run_git_commit(repo: Path, message: str) -> subprocess.CompletedProcess[str]:
    """Запускает git commit с передачей VIRTUAL_ENV активного окружения."""
    env = {
        **os.environ,
        "VIRTUAL_ENV": str(Path(sys.executable).parent.parent),
    }
    return subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=env,
    )


def test_clean_commit_succeeds(git_repo: Path):
    """Тест 1: Чистый коммит без секретов успешно фиксируется в репозитории."""
    clean_file = git_repo / "clean.txt"
    clean_file.write_text("Hello World! This is safe clean code.\n", encoding="utf-8")

    subprocess.run(["git", "add", "clean.txt"], cwd=str(git_repo), check=True)
    result = _run_git_commit(git_repo, "feat: clean commit")

    output = result.stdout + "\n" + result.stderr
    assert result.returncode == 0, f"Коммит завершился с ошибкой:\n{output}"
    assert "Security Shield passed" in output or "Pre-Commit Hook" in output


def test_blocked_on_synthetic_secret(git_repo: Path):
    """Тест 2: Попытка коммита синтетического секрета блокируется хуком."""
    secret_token = "AIzaSy" + "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"
    leak_file = git_repo / "leak.txt"
    leak_file.write_text(f"API_KEY = '{secret_token}'\n", encoding="utf-8")

    subprocess.run(["git", "add", "leak.txt"], cwd=str(git_repo), check=True)
    result = _run_git_commit(git_repo, "leak: commit secret")

    assert result.returncode == 1, "Коммит с утечкой секрета должен быть заблокирован!"
    output = result.stdout + "\n" + result.stderr
    assert "SECURITY VIOLATIONS DETECTED" in output
    assert "Commit or push blocked" in output


def test_blocked_on_forbidden_env_file(git_repo: Path):
    """Тест 3: Попытка коммита запрещённого файла .env блокируется хуком."""
    env_file = git_repo / ".env"
    env_file.write_text("DATABASE_PASSWORD=secret\n", encoding="utf-8")

    subprocess.run(["git", "add", ".env"], cwd=str(git_repo), check=True)
    result = _run_git_commit(git_repo, "config: add env file")

    assert result.returncode == 1, "Коммит с файлом .env должен быть заблокирован!"
    output = result.stdout + "\n" + result.stderr
    assert "Forbidden file pattern committed: .env" in output or "SECURITY VIOLATIONS DETECTED" in output


def test_commit_succeeds_after_sanitization(git_repo: Path):
    """Тест 4: После санитизации индекса (удаления секрета) коммит проходит успешно."""
    secret_token = "sk-" + "a" * 32
    bad_file = git_repo / "bad.py"
    bad_file.write_text(f"key = '{secret_token}'\n", encoding="utf-8")

    subprocess.run(["git", "add", "bad.py"], cwd=str(git_repo), check=True)
    res_bad = _run_git_commit(git_repo, "bad commit")
    assert res_bad.returncode == 1

    # Санитизация индекса
    subprocess.run(["git", "reset", "HEAD", "bad.py"], cwd=str(git_repo), check=True)
    bad_file.unlink()

    good_file = git_repo / "good.py"
    good_file.write_text("print('all clean now')\n", encoding="utf-8")
    subprocess.run(["git", "add", "good.py"], cwd=str(git_repo), check=True)

    res_good = _run_git_commit(git_repo, "clean commit after fix")
    assert res_good.returncode == 0
