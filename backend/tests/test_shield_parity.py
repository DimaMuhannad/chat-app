"""Тест паритета проверок безопасности между Web API (audit_path) и CLI (audit_repository) (SEC-02)."""

from pathlib import Path
import subprocess
import pytest

from assistant_shared.security import (
    audit_path,
    audit_repository,
    check_file_content,
    get_staged_or_tracked_files,
)


def _init_test_git_repo(repo_path: Path) -> Path:
    """Инициализирует git-репозиторий с тестовыми файлами."""
    repo_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(repo_path), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.org"], cwd=str(repo_path), check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(repo_path), check=True)

    # 1. Валидный чистый файл
    (repo_path / "valid.py").write_text("print('clean code')\n", encoding="utf-8")

    # 2. Файл с Generic Bearer Secret
    (repo_path / "secret.py").write_text("api" + "_key = 'super_secret_token_12345'\n", encoding="utf-8")

    # 3. Файл с приватным RSA-ключом
    (repo_path / "private_key.txt").write_text("-----BEGIN " + "RSA PRIVATE KEY-----\nfake\n-----END " + "RSA PRIVATE KEY-----\n", encoding="utf-8")

    # 4. Запрещённый конфигурационный файл
    (repo_path / ".env.prod").write_text("SECRET=12345\n", encoding="utf-8")

    subprocess.run(["git", "add", "-A"], cwd=str(repo_path), check=True)
    return repo_path


def test_parity_between_web_audit_and_cli_shield(tmp_path: Path, capsys):
    """Проверяет 100% паритет нарушений между Web-аудитом и CLI shield (SEC-02)."""
    repo = _init_test_git_repo(tmp_path / "test_repo")

    # 1. Web-аудит (audit_path)
    web_res = audit_path(repo, is_public_repo=True)
    assert web_res["exists"] is True
    assert web_res["status"] == "violations"
    web_violations = web_res["violations"]

    # 2. CLI-аудит (audit_repository)
    cli_code = audit_repository(repo, check_staged_only=False)
    captured = capsys.readouterr()
    assert cli_code == 1

    # Извлекаем строки нарушений из вывода CLI shield
    cli_violations = [
        line.strip().replace("🚨 ", "")
        for line in captured.out.splitlines()
        if "🚨 " in line
    ]

    # 3. Сверка нарушений по категориям
    assert any("Forbidden file pattern" in v or "Запрещенный файл" in v for v in web_violations)
    assert any("Forbidden file pattern" in v for v in cli_violations)

    assert any("Generic Bearer Secret" in v for v in web_violations)
    assert any("Generic Bearer Secret" in v for v in cli_violations)

    assert any("Private Key" in v for v in web_violations)
    assert any("Private Key" in v for v in cli_violations)

    # 4. Точный паритет количества найденных проблем в файлах репозитория
    files = get_staged_or_tracked_files(repo, check_staged_only=False)
    direct_violations = []
    for f in files:
        direct_violations.extend(check_file_content(repo / f, is_public_repo=True))

    assert len(cli_violations) == len(direct_violations)
    assert len(web_violations) == len(direct_violations)
