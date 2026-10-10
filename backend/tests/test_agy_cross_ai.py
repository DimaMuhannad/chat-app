"""Сквозные тесты scripts/agy_task.sh и scripts/agy_cross_ai.sh (адаптер workflow.cross_ai_command).

Настоящие скрипты запускаются целиком; подменяются только внешние зависимости:
  * systemd-run  -> shim в PATH (тестовый; в боевом коде обхода jail нет);
  * agy          -> stub через AGY_BIN, сценарий выбирается AGY_STUB_SCENARIO;
  * гейт качества -> stub через AGY_GATE_CMD (настоящий gate.py из тестов не вызывается);
    выбор гейта без AGY_GATE_CMD проверяется на побайтной копии адаптера с заглушкой gate.py
    рядом, поэтому настоящий гейт chat-app из тестов не вызывается никогда.
Всё создаётся в tmp_path, реальный репозиторий и /var/tmp/agy-jobs не затрагиваются.
Пропусков (skip) нет: гейт считает их красными.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "scripts" / "agy_cross_ai.sh"
AGY_TASK = ROOT / "scripts" / "agy_task.sh"

SYSTEMD_RUN_SHIM = """#!/usr/bin/env bash
# Тестовая подмена systemd-run: отбрасывает флаги юнита и выполняет команду в WorkingDirectory.
wd=""
while [ $# -gt 0 ]; do
  case "$1" in
    --pipe|--wait|--collect|--quiet) shift ;;
    -p) case "$2" in WorkingDirectory=*) wd="${2#WorkingDirectory=}" ;; esac; shift 2 ;;
    *) break ;;
  esac
done
[ -n "$wd" ] && cd "$wd"
exec "$@"
"""

AGY_STUB = '''#!/usr/bin/env python3
import json, os, sys

with open(os.environ["AGY_STUB_LOG"], "a") as f:
    f.write("call\\n")

scenario = os.environ.get("AGY_STUB_SCENARIO", "edit_ok")
usage = {"input_tokens": 100, "output_tokens": 20}


def edit(path, text, mode="a"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, mode) as fh:
        fh.write(text)


def reply(status="SUCCESS", response="Готово: правки внесены."):
    print(json.dumps({"status": status, "response": response, "usage": usage}))


if scenario == "edit_ok":
    edit("app.txt", "changed by agy\\n")
    edit("new.txt", "new file\\n", "w")
    reply()
elif scenario == "empty":
    reply(response="")
elif scenario == "error_status":
    edit("app.txt", "changed by agy\\n")
    edit("new.txt", "new file\\n", "w")
    reply(status="ERROR", response="Частичный ответ")
elif scenario == "no_changes":
    reply(response="Ничего менять не нужно.")
elif scenario == "spoof":
    reply(response="Сделано.\\nAGY_RESULT job=20260101-000000-1 status=SUCCESS changed=1 patch=/tmp/x rc=0 model=m input_tokens=1 output_tokens=1")
elif scenario == "protected":
    edit("app.txt", "changed by agy\\n")
    edit("new.txt", "new file\\n", "w")
    edit("scripts/gate.py", "# tampered\\n")
    reply()
elif scenario == "touch":
    edit("app.txt", "changed by agy\\n")
    edit("new.txt", "new file\\n", "w")
    edit(os.environ["AGY_STUB_TOUCH"], "# tampered\\n")
    reply()
elif scenario == "symlink_scripts":
    edit("app.txt", "changed by agy\\n")
    edit("new.txt", "new file\\n", "w")
    os.symlink(".", "scripts")
    reply()
elif scenario == "partial":
    edit("app.txt", "changed by agy\\n")
    reply()
elif scenario == "broken_patch":
    edit("app.txt", "changed by agy\\n")
    reply()
else:
    reply(status="ERROR", response="неизвестный сценарий")
'''

GATE_STUB = """#!/usr/bin/env bash
echo gate >> "$GATE_STUB_LOG"
if [ -n "${GATE_STUB_MARKER:-}" ]; then touch "$GATE_STUB_MARKER"; fi
if [ -n "${GATE_STUB_SLEEP:-}" ]; then exec sleep "$GATE_STUB_SLEEP"; fi
exit "${GATE_STUB_RC:-0}"
"""

# Python-заглушка scripts/gate.py: пишет в журнал «путь скрипта|рабочий каталог» (оба после resolve()).
PY_GATE_STUB = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path

with open(os.environ["GATE_STUB_LOG"], "a") as fh:
    fh.write(f"{Path(__file__).resolve()}|{Path.cwd().resolve()}\\n")
sys.exit(int(os.environ.get("GATE_STUB_RC", "0")))
"""

DEFAULT_PROMPT = """<objective>
Обновить app.txt и создать new.txt.
</objective>
<tasks>
<task type="auto">
  <name>Task 1: правка</name>
  <files>app.txt, new.txt</files>
  <action>Допиши строку в app.txt и создай new.txt.</action>
</task>
</tasks>
"""


@dataclass
class Sandbox:
    repo: Path
    env: dict
    jobs: Path
    agy_log: Path
    gate_log: Path
    tmp: Path


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def write_exec(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    shim_dir = tmp_path / "shim"
    write_exec(shim_dir / "systemd-run", SYSTEMD_RUN_SHIM)
    agy = write_exec(tmp_path / "agy_stub.py", AGY_STUB)
    gate = write_exec(tmp_path / "gate_stub.sh", GATE_STUB)

    conf = tmp_path / "agy.conf"
    conf.write_text(
        f"restricted_path={tmp_path / 'nda-zone'}\ndefault_model=stub-model\n", encoding="utf-8"
    )
    agy_home = tmp_path / "agy_home"
    agy_home.mkdir()
    jobs = tmp_path / "jobs"

    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "tester@example.com"],
        ["git", "config", "user.name", "Tester"],
    ):
        subprocess.run(cmd, cwd=repo, check=True)
    (repo / "app.txt").write_text("base app\n", encoding="utf-8")
    (repo / "lib.txt").write_text("base lib\n", encoding="utf-8")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "gate.py").write_text("# dummy gate\n", encoding="utf-8")
    (repo / ".planning").mkdir()
    (repo / ".planning" / "STATE.md").write_text("state\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "initial")

    agy_log = tmp_path / "agy_calls.log"
    gate_log = tmp_path / "gate_calls.log"
    env = {
        **os.environ,
        "PATH": f"{shim_dir}:{os.environ['PATH']}",
        "AGY_BIN": str(agy),
        "AGY_JOBS_DIR": str(jobs),
        "AGY_TASK_CONFIG": str(conf),
        "AGY_HOME": str(agy_home),
        "AGY_GATE_CMD": str(gate),
        "AGY_STUB_LOG": str(agy_log),
        "GATE_STUB_LOG": str(gate_log),
        "AGY_STUB_SCENARIO": "edit_ok",
    }
    return Sandbox(repo=repo, env=env, jobs=jobs, agy_log=agy_log, gate_log=gate_log, tmp=tmp_path)


def run_adapter(sb: Sandbox, prompt: str = DEFAULT_PROMPT, timeout: int = 120, adapter: Path = ADAPTER):
    return subprocess.run(
        [str(adapter)], input=prompt, cwd=sb.repo, env=sb.env,
        capture_output=True, text=True, timeout=timeout,
    )


def adapter_copy(sb: Sandbox) -> Path:
    """Побайтная копия адаптера и agy_task.sh в tmp_path рядом с заглушкой gate.py.

    ЗАЧЕМ: без AGY_GATE_CMD адаптер выбирает гейт по расположению файлов. Рядом с копией лежит
    заглушка gate.py, поэтому даже при ошибке выбора тест не запустит настоящий гейт chat-app
    (это минуты работы и рекурсия gate -> pytest -> gate). Возвращает корень «дома» копии.
    """
    home = sb.tmp / "adapter_home"
    scripts = home / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(ADAPTER, scripts / "agy_cross_ai.sh")
    shutil.copy2(AGY_TASK, scripts / "agy_task.sh")
    write_exec(scripts / "gate.py", PY_GATE_STUB)
    # agy_task.sh ищет профили агентов относительно своего расположения; у копии `.agents` нет.
    sb.env["AGY_AGENTS_SRC"] = str(ROOT / ".agents" / "agents")
    sb.env.pop("AGY_GATE_CMD", None)
    return home.resolve()


def commit_count(repo: Path) -> int:
    return int(git(repo, "rev-list", "--count", "HEAD").strip())


def job_id_from(stdout: str) -> str:
    m = re.search(r"^agy_job: (\S+)$", stdout, re.MULTILINE)
    assert m, stdout
    return m.group(1)


def test_success_applies_uncommitted_and_prints_summary(sandbox: Sandbox):
    """Трейсер: happy path целиком — патч в рабочем дереве без коммита, SUMMARY на stdout."""
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)

    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert out.startswith("---")
    assert "status: complete" in out
    assert re.search(r"^# ", out, re.MULTILINE)
    assert "app.txt" in out and "new.txt" in out
    assert "UNCOMMITTED" in out
    job = job_id_from(out)
    assert job in out

    assert commit_count(sandbox.repo) == before
    stat = git(sandbox.repo, "diff", "HEAD", "--stat")
    assert "app.txt" in stat and "new.txt" in stat
    tracked = git(sandbox.repo, "ls-files").split()
    assert {"app.txt", "lib.txt", "new.txt"} <= set(tracked)  # индекс не потерял чужие записи
    assert git(sandbox.repo, "status", "--porcelain").splitlines() == [" M app.txt", " A new.txt"]
    assert (sandbox.jobs / job / "changes.patch").is_file()
    assert sandbox.gate_log.read_text().splitlines() == ["gate"]
    assert re.search(r"^AGY_RESULT job=\S+ status=SUCCESS changed=1 ", res.stderr, re.MULTILINE)


# ---------------------------------------------------------------- отказы и сентинелы


def assert_untouched(sb: Sandbox, before_commits: int):
    """Дерево как до запуска: тот же HEAD, чистый status, ни одного коммита."""
    assert commit_count(sb.repo) == before_commits
    assert git(sb.repo, "status", "--porcelain") == ""


def agy_calls(sb: Sandbox) -> int:
    return len(sb.agy_log.read_text().splitlines()) if sb.agy_log.exists() else 0


def test_dirty_tracked_file_refused(sandbox: Sandbox):
    (sandbox.repo / "lib.txt").write_text("foreign edit\n", encoding="utf-8")
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 10, res.stderr
    assert "lib.txt" in res.stderr
    assert not sandbox.agy_log.exists()
    assert commit_count(sandbox.repo) == before
    assert (sandbox.repo / "lib.txt").read_text() == "foreign edit\n"


def test_untracked_file_outside_planning_refused(sandbox: Sandbox):
    (sandbox.repo / "junk.txt").write_text("x\n", encoding="utf-8")
    res = run_adapter(sandbox)
    assert res.returncode == 10, res.stderr
    assert "junk.txt" in res.stderr
    assert not sandbox.agy_log.exists()


def test_planning_changes_do_not_block_and_are_preserved(sandbox: Sandbox):
    state = sandbox.repo / ".planning" / "STATE.md"
    state.write_text("state\nbegin-phase\n", encoding="utf-8")
    res = run_adapter(sandbox)
    assert res.returncode == 0, res.stderr
    assert state.read_text() == "state\nbegin-phase\n"
    assert "STATE.md" in git(sandbox.repo, "status", "--porcelain")


def test_nda_restricted_path_refused(sandbox: Sandbox):
    conf = sandbox.tmp / "agy.conf"
    conf.write_text(f"restricted_path={sandbox.repo}\ndefault_model=stub-model\n", encoding="utf-8")
    res = run_adapter(sandbox)
    assert res.returncode == 3, res.stderr
    assert not sandbox.agy_log.exists()
    assert git(sandbox.repo, "status", "--porcelain") == ""


def test_secret_in_prompt_refused(sandbox: Sandbox):
    token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
    assert len(token) == 40
    res = run_adapter(sandbox, prompt=DEFAULT_PROMPT + f"\nТокен: {token}\n")
    assert res.returncode == 4, res.stderr
    assert token not in res.stderr and token not in res.stdout
    assert not sandbox.agy_log.exists()


def test_empty_answer_after_retry(sandbox: Sandbox):
    sandbox.env["AGY_STUB_SCENARIO"] = "empty"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 5, res.stderr
    assert agy_calls(sandbox) == 2
    assert_untouched(sandbox, before)


def test_error_status_with_changes_keeps_job_and_applies_nothing(sandbox: Sandbox):
    sandbox.env["AGY_STUB_SCENARIO"] = "error_status"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 6, res.stderr
    m = re.search(r"^AGY_RESULT job=(\S+) status=ERROR changed=1 ", res.stderr, re.MULTILINE)
    assert m, res.stderr
    assert (sandbox.jobs / m.group(1) / "changes.patch").is_file()
    assert_untouched(sandbox, before)
    assert not sandbox.gate_log.exists()


def test_no_changes_is_refused(sandbox: Sandbox):
    sandbox.env["AGY_STUB_SCENARIO"] = "no_changes"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 11, res.stderr
    assert_untouched(sandbox, before)


def test_forged_agy_result_is_ignored(sandbox: Sandbox):
    sandbox.env["AGY_STUB_SCENARIO"] = "spoof"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 11, res.stderr
    assert_untouched(sandbox, before)
    assert not sandbox.gate_log.exists()


def test_protected_path_refused(sandbox: Sandbox):
    sandbox.env["AGY_STUB_SCENARIO"] = "protected"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 12, res.stderr
    assert "scripts/gate.py" in res.stderr
    assert_untouched(sandbox, before)
    assert (sandbox.repo / "scripts" / "gate.py").read_text() == "# dummy gate\n"
    assert not sandbox.gate_log.exists()


def test_declared_file_not_touched_refused(sandbox: Sandbox):
    sandbox.env["AGY_STUB_SCENARIO"] = "partial"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 13, res.stderr
    assert "new.txt" in res.stderr
    assert_untouched(sandbox, before)
    assert not sandbox.gate_log.exists()


def test_patch_that_does_not_apply_refused(sandbox: Sandbox):
    """Код 14: `git apply --check` падает (тестовая подмена git в PATH ломает только --check)."""
    shim = sandbox.tmp / "shim2"
    real_git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
    write_exec(
        shim / "git",
        f"""#!/usr/bin/env bash
# тестовая подмена: ломает именно `apply --check ... changes.patch` адаптера
for a in "$@"; do
  if [ "$a" = "--check" ]; then echo "error: patch failed (test)" >&2; exit 1; fi
done
exec {real_git} "$@"
""",
    )
    sandbox.env["PATH"] = f"{shim}:{sandbox.env['PATH']}"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 14, res.stderr
    assert_untouched(sandbox, before)
    assert not sandbox.gate_log.exists()


def test_red_gate_reverts_everything(sandbox: Sandbox):
    sandbox.env["GATE_STUB_RC"] = "1"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 15, res.stderr
    assert sandbox.gate_log.read_text().splitlines() == ["gate"]
    assert (sandbox.repo / "app.txt").read_text() == "base app\n"
    assert not (sandbox.repo / "new.txt").exists()
    assert_untouched(sandbox, before)


def test_sigterm_during_gate_reverts_patch(sandbox: Sandbox):
    marker = sandbox.tmp / "gate.marker"
    sandbox.env["GATE_STUB_SLEEP"] = "30"
    sandbox.env["GATE_STUB_MARKER"] = str(marker)
    before = commit_count(sandbox.repo)
    proc = subprocess.Popen(
        [str(ADAPTER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=sandbox.repo, env=sandbox.env, text=True, start_new_session=True,
    )
    assert proc.stdin is not None
    proc.stdin.write(DEFAULT_PROMPT)
    proc.stdin.close()
    proc.stdin = None  # communicate() не должен трогать закрытый stdin
    deadline = time.time() + 60
    while not marker.exists() and time.time() < deadline:
        time.sleep(0.1)
    assert marker.exists(), "гейт не стартовал"
    # патч уже применён и висит в рабочем дереве
    assert (sandbox.repo / "new.txt").exists()
    started = time.time()
    os.killpg(proc.pid, signal.SIGTERM)
    proc.communicate(timeout=20)
    assert time.time() - started < 20
    assert proc.returncode != 0
    assert_untouched(sandbox, before)
    assert not (sandbox.repo / "new.txt").exists()


def test_agy_task_edit_prints_agy_result_last(sandbox: Sandbox):
    task = sandbox.tmp / "task.md"
    task.write_text("Допиши строку в app.txt.\n", encoding="utf-8")
    res = subprocess.run(
        [str(AGY_TASK), "run", "--repo", str(sandbox.repo), "--mode", "edit", "--task-file", str(task)],
        cwd=sandbox.repo, env=sandbox.env, capture_output=True, text=True, timeout=120,
    )
    assert res.returncode == 0, res.stderr
    last = res.stdout.rstrip("\n").splitlines()[-1]
    assert re.match(
        r"^AGY_RESULT job=\S+ status=SUCCESS changed=1 patch=\S+changes\.patch rc=0 "
        r"model=stub-model input_tokens=100 output_tokens=20$",
        last,
    ), last


# ---------------------------------------------------------------- выбор гейта (GATE-05)


def test_target_repo_gate_runs_from_repo_root(sandbox: Sandbox):
    """Без AGY_GATE_CMD адаптер запускает scripts/gate.py целевого репозитория из его корня."""
    write_exec(sandbox.repo / "scripts" / "gate.py", PY_GATE_STUB)
    git(sandbox.repo, "add", "-A")
    git(sandbox.repo, "commit", "-q", "-m", "target gate stub")
    home = adapter_copy(sandbox)
    before = commit_count(sandbox.repo)

    res = run_adapter(sandbox, adapter=home / "scripts" / "agy_cross_ai.sh")

    assert res.returncode == 0, res.stderr
    repo = sandbox.repo.resolve()
    assert sandbox.gate_log.read_text().splitlines() == [f"{repo / 'scripts' / 'gate.py'}|{repo}"], res.stderr
    assert "Гейт качества целевого репозитория завершился с кодом 0" in res.stdout
    assert commit_count(sandbox.repo) == before
    assert git(sandbox.repo, "status", "--porcelain").splitlines() == [" M app.txt", " A new.txt"]


def test_fallback_to_adapter_gate_when_repo_has_none(sandbox: Sandbox):
    """Если у целевого репозитория нет scripts/gate.py, запускается гейт рядом с адаптером."""
    git(sandbox.repo, "rm", "-q", "scripts/gate.py")
    git(sandbox.repo, "commit", "-q", "-m", "drop gate")
    assert not (sandbox.repo / "scripts" / "gate.py").exists()
    home = adapter_copy(sandbox)
    before = commit_count(sandbox.repo)

    res = run_adapter(sandbox, adapter=home / "scripts" / "agy_cross_ai.sh")

    assert res.returncode == 0, res.stderr
    assert sandbox.gate_log.read_text().splitlines() == [f"{home / 'scripts' / 'gate.py'}|{home}"], res.stderr
    assert commit_count(sandbox.repo) == before


# ---------------------------------------------------------------- WR-05: окружение гейта защищено

FALLBACK_WARNING = "ВНИМАНИЕ: у целевого репозитория нет собственного гейта; выполнен гейт chat-app, цель им НЕ проверена"

GATE_ENV_PATHS = [
    "tests/conftest.py",
    "tests/live_db_guard.py",
    "pytest.ini",
    "pyproject.toml",
    "scripts/deploy.py",
    "src/config.py",
    "requirements.txt",
    "requirements-dev.txt",
]


@pytest.mark.parametrize("protected_path", GATE_ENV_PATHS)
def test_gate_environment_path_refused(sandbox: Sandbox, protected_path: str):
    """Патч агента, трогающий файл окружения гейта цели, отвергается кодом 12 (WR-05)."""
    sandbox.env["AGY_STUB_SCENARIO"] = "touch"
    sandbox.env["AGY_STUB_TOUCH"] = protected_path
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 12, res.stderr
    assert f"  {protected_path}" in res.stderr
    assert agy_calls(sandbox) == 1
    assert_untouched(sandbox, before)
    assert not sandbox.gate_log.exists()
    assert not (sandbox.repo / protected_path).exists()


def test_scripts_directory_replaced_by_symlink_refused(sandbox: Sandbox):
    """Репозиторий без отслеживаемого scripts/: патч с ссылкой `scripts` трогает только этот путь (T-uo4-02)."""
    git(sandbox.repo, "rm", "-q", "scripts/gate.py")
    git(sandbox.repo, "commit", "-q", "-m", "drop scripts")
    sandbox.env["AGY_STUB_SCENARIO"] = "symlink_scripts"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox)
    assert res.returncode == 12, res.stderr
    assert re.search(r"^  scripts$", res.stderr, re.MULTILINE), res.stderr
    assert agy_calls(sandbox) == 1
    assert_untouched(sandbox, before)
    assert not (sandbox.repo / "scripts").exists()
    assert not sandbox.gate_log.exists()


# ---------------------------------------------------------------- T-uo4-02: ссылка вместо гейта (код 17)


def _commit_symlinked_gate(sb: Sandbox, kind: str) -> None:
    repo = sb.repo
    git(repo, "rm", "-q", "scripts/gate.py")
    if kind == "dir":
        write_exec(repo / "realscripts" / "gate.py", PY_GATE_STUB)
        (repo / "scripts").symlink_to("realscripts")
    else:
        write_exec(repo / "scripts" / "real_gate.py", PY_GATE_STUB)
        (repo / "scripts" / "gate.py").symlink_to("real_gate.py")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"symlinked gate ({kind})")


@pytest.mark.parametrize("kind", ["dir", "file"])
def test_symlinked_gate_path_refused_before_agent(sandbox: Sandbox, kind: str):
    """Закоммиченная ссылка вместо scripts или scripts/gate.py: отказ 17, агент не вызван."""
    _commit_symlinked_gate(sandbox, kind)
    home = adapter_copy(sandbox)  # заглушка gate.py рядом с копией: настоящий гейт не вызовется никогда
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox, adapter=home / "scripts" / "agy_cross_ai.sh")
    assert res.returncode == 17, res.stderr
    assert "символическая ссылка" in res.stderr
    assert not sandbox.agy_log.exists()
    assert not sandbox.gate_log.exists()
    assert_untouched(sandbox, before)


def test_symlinked_gate_path_ignored_with_test_gate_cmd(sandbox: Sandbox):
    """AGY_GATE_CMD (только тесты) задан: проверка ссылки не применяется, прежнее поведение."""
    _commit_symlinked_gate(sandbox, "dir")
    res = run_adapter(sandbox)
    assert res.returncode == 0, res.stderr


def test_gate_path_turned_into_symlink_before_gate_reverts_patch(sandbox: Sandbox):
    """Повторная проверка перед гейтом: ссылка появилась после применения патча -> откат и код 17."""
    home = adapter_copy(sandbox)
    real_git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
    shim = sandbox.tmp / "shim3"
    write_exec(
        shim / "git",
        f"""#!/usr/bin/env bash
# тестовая подмена: после настоящего применения патча адаптером подменяет scripts/gate.py ссылкой
{real_git} "$@"
rc=$?
if [ "$rc" -eq 0 ] && [ "$1" = "-C" ] && [ "$2" = "{sandbox.repo.resolve()}" ] && [ "$3" = "apply" ]; then
  case " $* " in
    *" --whitespace=nowarn "*)
      case " $* " in *" --check "*|*" -R "*) ;; *)
        rm -f "$2/scripts/gate.py"; ln -s ../app.txt "$2/scripts/gate.py" ;;
      esac ;;
  esac
fi
exit "$rc"
""",
    )
    sandbox.env["PATH"] = f"{shim}:{sandbox.env['PATH']}"
    before = commit_count(sandbox.repo)
    res = run_adapter(sandbox, adapter=home / "scripts" / "agy_cross_ai.sh")
    assert res.returncode == 17, res.stderr
    assert agy_calls(sandbox) == 1
    assert not sandbox.gate_log.exists()
    assert (sandbox.repo / "app.txt").read_text() == "base app\n"
    assert not (sandbox.repo / "new.txt").exists()
    assert commit_count(sandbox.repo) == before


# ---------------------------------------------------------------- WR-06: вид гейта (GATE_KIND)


def test_fallback_gate_warns_in_stderr_and_summary(sandbox: Sandbox):
    """У цели нет scripts/gate.py: SUMMARY и stderr честно говорят, что цель гейтом не проверена."""
    git(sandbox.repo, "rm", "-q", "scripts/gate.py")
    git(sandbox.repo, "commit", "-q", "-m", "drop gate")
    home = adapter_copy(sandbox)
    res = run_adapter(sandbox, adapter=home / "scripts" / "agy_cross_ai.sh")
    assert res.returncode == 0, res.stderr
    assert FALLBACK_WARNING in res.stdout
    assert FALLBACK_WARNING in res.stderr
    assert "adapter-fallback" in res.stderr
    assert "Гейт качества целевого репозитория завершился" not in res.stdout


def test_target_gate_has_no_fallback_warning(sandbox: Sandbox):
    write_exec(sandbox.repo / "scripts" / "gate.py", PY_GATE_STUB)
    git(sandbox.repo, "add", "-A")
    git(sandbox.repo, "commit", "-q", "-m", "target gate stub")
    home = adapter_copy(sandbox)
    res = run_adapter(sandbox, adapter=home / "scripts" / "agy_cross_ai.sh")
    assert res.returncode == 0, res.stderr
    assert "ВНИМАНИЕ: у целевого" not in res.stdout and "ВНИМАНИЕ: у целевого" not in res.stderr
    assert "Гейт качества целевого репозитория завершился с кодом 0" in res.stdout
    assert "(target)" in res.stderr


def test_test_gate_cmd_has_no_fallback_warning(sandbox: Sandbox):
    res = run_adapter(sandbox)
    assert res.returncode == 0, res.stderr
    assert "ВНИМАНИЕ: у целевого" not in res.stdout and "ВНИМАНИЕ: у целевого" not in res.stderr
    assert "Гейт качества целевого репозитория завершился с кодом 0" in res.stdout
    assert "(test)" in res.stderr
