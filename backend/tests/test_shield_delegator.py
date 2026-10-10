"""scripts/security_shield.py - тонкий делегатор к обёртке assistant-core (SECF-01, D-18).

Заменяет прежний тест равенства sha256 двух копий обёртки. Тест не пропускается: assistant-core
на этой машине обязателен (решение владельца D-18), его отсутствие делает тест красным.
Секретная строка собирается из частей, файл теста сам не совпадает с шаблонами секретов.
"""

import os
import subprocess
import sys
from pathlib import Path

SHIELD = Path(__file__).resolve().parents[2] / "scripts" / "security_shield.py"
SECRET_LINE = "api" + "_key = '" + "a" * 20 + "'\n"
ERROR_MARK = "SECURITY SHIELD ERROR"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(root: Path, text: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "synthetic@example.org")
    _git(root, "config", "user.name", "synthetic")
    (root / "data.txt").write_text(text, encoding="utf-8")
    _git(root, "add", "-A")
    return root


def _run(*args: str, cwd: Path, core_dir: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if core_dir is not None:
        env["ASSISTANT_CORE_DIR"] = str(core_dir)
    return subprocess.run([sys.executable, str(SHIELD), *args], cwd=cwd, capture_output=True, text=True, env=env)


def test_delegator_does_not_import_the_shared_library():
    text = SHIELD.read_text(encoding="utf-8")
    assert ("assistant" + "_shared") not in text
    assert "audit_repository" not in text
    assert "CORPORATE" not in text


def test_delegator_end_to_end_blocks_secret_and_passes_clean(tmp_path):
    leaky = _repo(tmp_path / "leaky", SECRET_LINE)
    clean = _repo(tmp_path / "clean", "synthetic\n")
    blocked = _run("--all", str(leaky), cwd=tmp_path)
    passed = _run("--all", str(clean), cwd=tmp_path)
    assert blocked.returncode == 1
    assert passed.returncode == 0


def test_delegator_unknown_flag_exits_with_two(tmp_path):
    assert _run("--bogus", cwd=tmp_path).returncode == 2


def test_delegator_missing_core_dir_is_fail_closed(tmp_path):
    res = _run("--all", str(tmp_path), cwd=tmp_path, core_dir=tmp_path / "net-takogo-kataloga")
    assert res.returncode == 1
    assert ERROR_MARK in res.stderr


def test_delegator_core_dir_without_interpreter_is_fail_closed(tmp_path):
    core = tmp_path / "core"
    (core / "scripts").mkdir(parents=True)
    (core / "scripts" / "security_shield.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    res = _run("--all", str(tmp_path), cwd=tmp_path, core_dir=core)
    assert res.returncode == 1
    assert ERROR_MARK in res.stderr


def test_delegator_core_dir_without_wrapper_is_fail_closed(tmp_path):
    core = tmp_path / "core"
    (core / ".venv" / "bin").mkdir(parents=True)
    stub = core / ".venv" / "bin" / "python"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    res = _run("--all", str(tmp_path), cwd=tmp_path, core_dir=core)
    assert res.returncode == 1
    assert ERROR_MARK in res.stderr


def test_delegator_passes_args_cwd_and_exit_code_through(tmp_path):
    core = tmp_path / "core"
    (core / "scripts").mkdir(parents=True)
    (core / "scripts" / "security_shield.py").write_text("# stub\n", encoding="utf-8")
    (core / ".venv" / "bin").mkdir(parents=True)
    stub = core / ".venv" / "bin" / "python"
    stub.write_text('#!/bin/sh\necho "ARGS:$*"\npwd\nexit 7\n', encoding="utf-8")
    stub.chmod(0o755)
    work = tmp_path / "work"
    work.mkdir()
    res = _run("--all", "some-path", cwd=work, core_dir=core)
    assert res.returncode == 7
    lines = res.stdout.splitlines()
    assert lines[0] == f"ARGS:{core / 'scripts' / 'security_shield.py'} --all some-path"
    assert Path(lines[1]).resolve() == work.resolve()
