#!/usr/bin/env python3
"""Локальный гейт качества: одна команда -> честный итог «ЗЕЛЁНЫЙ» / «КРАСНЫЙ».

Запуск (из /opt/chat-app):  python3 scripts/gate.py
Только стандартная библиотека Python, запускается любым python3.

Что делает гейт:
  1. считает SHA-256 боевой assistant.db («до»);
  2. делает консистентную копию боевой БД во временный каталог (права 0700);
  3. запускает pytest chat-app ТОЛЬКО с SQLITE_DB_PATH на эту копию;
  4. запускает pytest assistant-core (переопределить БД окружением нельзя:
     src/config.py вызывает load_dotenv(..., override=True) - защита это хеш);
  5. сравнивает две копии synthetic_persona.py по SHA-256 (дрейф краснит итог);
  6. запускает scripts/security_shield.py каждого репозитория: из вывода берутся
     только строки находок (путь, вид, число), остальное не печатается и не хранится;
  7. считает SHA-256 боевой БД («после») и красит итог при любом расхождении;
  8. печатает по-русски таблицу «репозиторий × проверка -> ✓/✗» и итог.

Гейт не обрывается на первой ошибке. Прогон с 0 собранных тестов, с
пропущенными, xfail/xpass или deselected тестами считается красным.
Гейт не читает .env, credentials.json, token.json, *.session и не трогает
systemd-сервисы.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CHAT_DIR = Path(__file__).resolve().parents[1]
CORE_DIR = Path(os.environ.get("ASSISTANT_CORE_DIR", "/opt/assistant-core"))
LIVE_DB = CORE_DIR / "data" / "assistant.db"
CHAT_VENV_BIN = CHAT_DIR / "backend" / ".venv" / "bin"
CORE_VENV_BIN = CORE_DIR / ".venv" / "bin"
CHAT_PERSONA = CHAT_DIR / "backend" / "tests" / "synthetic_persona.py"
CORE_PERSONA = CORE_DIR / "tests" / "synthetic_persona.py"
CHAT_TOKENS = CHAT_DIR / "backend" / "tests" / "persona_tokens.py"
CORE_TOKENS = CORE_DIR / "tests" / "persona_tokens.py"
PYTEST_TIMEOUT_S = 900
LINT_TIMEOUT_S = 300
SHIELD_TIMEOUT_S = 300
# Режим запуска shield: "all" - все отслеживаемые файлы (с замороженным списком известных
# ложных срабатываний), "staged" - только проиндексированные и изменённые файлы.
SHIELD_MODE = "all"

# Известные ложные срабатывания эвристик shield; записи только удаляются; без номеров
# строк и без текста ключевых слов. Ключ записи: (путь в posix, вид находки) -> число.
KNOWN_SHIELD_FALSE_POSITIVES: dict[str, dict[tuple[str, str], int]] = {
    "chat-app": {
        ("docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md", "nda-keyword"): 3,
    },
    "assistant-core": {
        # Решение владельца 2026-10-02 (OQ1): единственное исключение для файла данных персоны;
        # снимается правилом Фазы 4 (SEC-01).
        ("config/persona.yaml", "nda-keyword"): 3,
        ("tests/test_debrief_parser.py", "secret:Generic Bearer Secret"): 2,
        ("tests/test_notion_client.py", "secret:Generic Bearer Secret"): 1,
        ("tests/test_voice.py", "secret:Generic Bearer Secret"): 3,
    },
}

REPO_CHAT = "chat-app"
REPO_CORE = "assistant-core"
REPO_BOTH = "оба"

_SUMMARY_WORDS = frozenset(
    {"failed", "error", "errors", "skipped", "deselected", "xfailed", "xpassed"}
)


@dataclass(frozen=True)
class CheckResult:
    repo: str
    name: str
    ok: bool
    detail: str = ""


def sha256_file(path: Path) -> str:
    """SHA-256 файла, чтение блоками."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_db_copy(live_db: Path, tmp_dir: Path) -> Path:
    """Консистентная копия боевой БД через sqlite3 backup (источник только на чтение).

    Единственная точка замены в Фазе 4 (DAT-04) на временную БД из общей схемы.
    Не shutil.copy: backup() даёт целостный снимок и не создаёт файлов рядом с боевой БД.
    """
    dst = tmp_dir / "assistant-copy.db"
    src = sqlite3.connect(live_db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        out = sqlite3.connect(dst)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    return dst


def run_cmd(
    cmd: list[str],
    cwd: Path,
    env_extra: dict[str, str] | None = None,
    timeout: int = PYTEST_TIMEOUT_S,
) -> subprocess.CompletedProcess:
    """Запуск подпроцесса: список аргументов, без shell, с таймаутом."""
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
    )


def chat_pytest_env(db_copy: Path | None) -> dict[str, str]:
    """Окружение для pytest chat-app: SQLITE_DB_PATH строго на копию.

    CRUD-тесты chat-app пишут в БД, поэтому без копии pytest chat-app не запускается никогда.
    """
    if db_copy is None:
        raise ValueError("нет копии БД: pytest chat-app без неё не запускается")
    if db_copy.resolve() == LIVE_DB.resolve():
        raise ValueError("SQLITE_DB_PATH не может указывать на боевую БД")
    return {"SQLITE_DB_PATH": str(db_copy)}


def _testsuites(junit_xml: Path) -> list[ET.Element]:
    root = ET.parse(junit_xml).getroot()
    if root.tag == "testsuite":
        return [root]
    suites = root.findall("testsuite")
    if not suites:
        raise ValueError("в junit XML нет элемента testsuite")
    return suites


def pytest_counts(junit_xml: Path) -> dict[str, int]:
    """Счётчики tests/failures/errors/skipped из junit XML (корень testsuites или testsuite)."""
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in _testsuites(junit_xml):
        for key in counts:
            counts[key] += int(suite.get(key, 0))
    return counts


def failed_test_ids(junit_xml: Path, limit: int = 10) -> list[str]:
    """«classname::name» первых упавших/ошибочных тестов."""
    ids: list[str] = []
    root = ET.parse(junit_xml).getroot()
    for case in root.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            ids.append(f"{case.get('classname', '')}::{case.get('name', '')}")
            if len(ids) >= limit:
                break
    return ids


def _last_summary_line(output: str) -> str:
    last = ""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("=") and " in " in stripped:
            last = stripped
    return last


def pytest_summary_flags(output: str) -> list[str]:
    """Слова из итоговой строки pytest, которые означают «не чисто» (skip/xfail/deselect/ошибки)."""
    line = _last_summary_line(output)
    if not line:
        return []
    tokens = "".join(ch if ch.isalpha() else " " for ch in line).split()
    return sorted({t for t in tokens if t in _SUMMARY_WORDS})


def pytest_ok(returncode: int, counts: dict[str, int], flags: list[str]) -> bool:
    """Зелёный только при коде 0, ненулевом числе тестов и без failed/error/skipped/flags."""
    return (
        returncode == 0
        and counts.get("tests", 0) > 0
        and counts.get("failures", 0) == 0
        and counts.get("errors", 0) == 0
        and counts.get("skipped", 0) == 0
        and not flags
    )


def _git_head(cwd: Path) -> str:
    try:
        proc = run_cmd(["git", "-C", str(cwd), "rev-parse", "HEAD"], cwd, timeout=30)
    except Exception:
        return "неизвестен"
    head = proc.stdout.strip()
    return head if proc.returncode == 0 and head else "неизвестен"


def _write_snapshot(
    save_dir: Path, repo: str, cmd: list[str], env_extra: dict[str, str] | None,
    cwd: Path, tmp_dir: Path, stdout: str,
) -> None:
    parts = [f"{key}={value}" for key, value in (env_extra or {}).items()] + cmd
    command = " ".join(parts).replace(str(tmp_dir), "временный каталог")
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    header = f"# Команда: {command}\n# Коммит: {_git_head(cwd)}\n# Дата: {stamp}\n"
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / f"pytest-{repo}.txt").write_text(header + stdout, encoding="utf-8")


def run_pytest_step(
    repo: str,
    pytest_bin: Path,
    target: str,
    cwd: Path,
    env_extra: dict[str, str] | None,
    tmp_dir: Path,
    save_dir: Path | None,
) -> CheckResult:
    """Один запуск pytest -> CheckResult. Команда без -k/-m/--deselect: набор тестов не сужается."""
    name = "pytest — тестов: 0"
    if not pytest_bin.is_file():
        return CheckResult(repo, name, False, f"не найден pytest: {pytest_bin}")
    if not cwd.is_dir():
        return CheckResult(repo, name, False, f"нет каталога репозитория: {cwd}")
    junit = tmp_dir / f"junit-{repo}.xml"
    cmd = [
        str(pytest_bin), target, "-v", "-p", "no:cacheprovider",
        f"--junitxml={junit}", f"--basetemp={tmp_dir}/pytest-{repo}",
    ]
    try:
        proc = run_cmd(cmd, cwd, env_extra)
    except subprocess.TimeoutExpired:
        return CheckResult(repo, name, False, "превышено время выполнения pytest")
    if save_dir is not None:
        _write_snapshot(save_dir, repo, cmd, env_extra, cwd, tmp_dir, proc.stdout)
    try:
        counts = pytest_counts(junit)
        failed = failed_test_ids(junit)
    except (OSError, ET.ParseError, ValueError):
        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        failed = []
    flags = pytest_summary_flags(proc.stdout)
    name = f"pytest — тестов: {counts['tests']}"
    if pytest_ok(proc.returncode, counts, flags):
        return CheckResult(repo, name, True)
    lines = [_last_summary_line(proc.stdout) or f"код возврата pytest: {proc.returncode}"]
    if counts["tests"] == 0:
        lines.append("не собрано ни одного теста")
    lines.extend(f"упал: {test_id}" for test_id in failed)
    return CheckResult(repo, name, False, "\n".join(lines))


def run_lint_imports_step(
    repo: str,
    lint_bin: Path,
    cwd: Path,
    env_extra: dict[str, str] | None,
) -> CheckResult:
    """Один запуск lint-imports (контракт .importlinter репозитория) -> CheckResult.

    --no-cache: кэш import-linter не должен появляться в дереве репозитория.
    """
    name = "import-linter"
    if not lint_bin.is_file():
        return CheckResult(repo, name, False, "не установлен import-linter — см. requirements-dev.txt")
    if not cwd.is_dir():
        return CheckResult(repo, name, False, f"нет каталога репозитория: {cwd}")
    try:
        proc = run_cmd([str(lint_bin), "--no-logo", "--no-cache"], cwd, env_extra, timeout=LINT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return CheckResult(repo, name, False, "превышено время выполнения lint-imports")
    if proc.returncode == 0:
        return CheckResult(repo, name, True)
    output = proc.stdout + "\n" + proc.stderr
    lines = [line.strip() for line in output.splitlines() if "BROKEN" in line or "->" in line]
    if not lines:
        lines = [f"код возврата lint-imports: {proc.returncode}"]
    return CheckResult(repo, name, False, "\n".join(lines[:10]))


_SHIELD_LINE_RE = re.compile(r"^\s+\U0001F6A8 (?P<body>.*)$")
_SHIELD_AT_LINE_RE = re.compile(r"^(?P<path>.+?):(?P<line>\d+) - (?P<msg>.*)$")
_SHIELD_SCANNED_RE = re.compile(r"Scanning (?P<n>\d+) files")
_SHIELD_MAX_DETAIL = 15


def _relative_posix(raw_path: str, repo_dir: Path) -> str:
    """Путь относительно repo_dir в posix; вне репозитория остаётся как есть."""
    try:
        return Path(raw_path).relative_to(repo_dir).as_posix()
    except ValueError:
        return raw_path


def parse_shield_findings(output: str, repo_dir: Path) -> collections.Counter:
    """Нормализует вывод shield в Counter {(путь, вид): число}.

    Рассматриваются ТОЛЬКО строки находок («пробелы, значок, пробел, тело»). Заголовок shield
    (адрес remote, e-mail автора), текст NDA-слов и номера строк отбрасываются и не попадают
    в результат: гейт ничего из этого не печатает и не сохраняет.
    """
    found: collections.Counter = collections.Counter()
    for line in output.splitlines():
        match = _SHIELD_LINE_RE.match(line)
        if not match:
            continue
        body = match.group("body").strip()
        if body.startswith("Forbidden file pattern committed:"):
            name = body.split(":", 1)[1].strip()
            found[(name, "forbidden-file")] += 1
            continue
        if body.startswith("CRITICAL"):
            found[("(remote)", "remote")] += 1
            continue
        at_line = _SHIELD_AT_LINE_RE.match(body)
        if at_line:
            path = _relative_posix(at_line.group("path"), repo_dir)
            msg = at_line.group("msg")
            if msg.startswith("Found potential "):
                found[(path, "secret:" + msg[len("Found potential "):].strip())] += 1
                continue
            if msg.startswith("Found proprietary corporate keyword"):
                found[(path, "nda-keyword")] += 1
                continue
        read_error = body.split(" - Read error", 1)
        if len(read_error) == 2:
            found[(_relative_posix(read_error[0].strip(), repo_dir), "read-error")] += 1
            continue
        found[("(нераспознано)", "unparsed")] += 1
    return found


def compare_shield_findings(
    found: collections.Counter, allowed: dict[tuple[str, str], int]
) -> tuple[list[str], list[str]]:
    """(новые находки, устаревшие записи списка известных ложных срабатываний)."""
    new = [
        f"новая находка: {path} [{kind}] ×{count}"
        for (path, kind), count in sorted(found.items())
        if count > allowed.get((path, kind), 0)
    ]
    stale = [
        f"устаревшая запись (удалите из KNOWN_SHIELD_FALSE_POSITIVES): {path} [{kind}]"
        for (path, kind), count in sorted(allowed.items())
        if found.get((path, kind), 0) < count
    ]
    return new, stale


def run_shield_step(repo: str, repo_dir: Path) -> CheckResult:
    """Один запуск scripts/security_shield.py репозитория -> CheckResult.

    detail содержит только строки «новая находка»/«устаревшая запись» или причину сбоя,
    никогда сырой вывод shield.
    """
    name = f"security_shield ({'--all' if SHIELD_MODE == 'all' else 'staged'})"
    script = repo_dir / "scripts" / "security_shield.py"
    if not script.is_file():
        return CheckResult(repo, name, False, f"не найден scripts/security_shield.py: {script}")
    if not repo_dir.is_dir():
        return CheckResult(repo, name, False, f"нет каталога репозитория: {repo_dir}")
    python_bin = CHAT_VENV_BIN / "python" if repo == REPO_CHAT else CORE_VENV_BIN / "python"
    if not python_bin.is_file():
        python_bin = Path(sys.executable)
    cmd = [str(python_bin), str(script), str(repo_dir)]
    if SHIELD_MODE == "all":
        cmd.append("--all")
    try:
        proc = run_cmd(cmd, repo_dir, timeout=SHIELD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return CheckResult(repo, name, False, "превышено время выполнения security_shield")
    if proc.returncode not in (0, 1):
        return CheckResult(repo, name, False, f"сбой security_shield: код возврата {proc.returncode}")
    found = parse_shield_findings(proc.stdout, repo_dir)
    if proc.returncode == 1 and not found:
        return CheckResult(repo, name, False, "сбой security_shield: код 1 без распознанных находок")
    if SHIELD_MODE == "all":
        scanned = _SHIELD_SCANNED_RE.search(proc.stdout)
        if not scanned or int(scanned.group("n")) == 0:
            return CheckResult(repo, name, False, "security_shield ничего не просканировал")
    new, stale = compare_shield_findings(found, KNOWN_SHIELD_FALSE_POSITIVES.get(repo, {}))
    problems = new + stale
    if problems:
        return CheckResult(repo, name, False, "\n".join(problems[:_SHIELD_MAX_DETAIL]))
    return CheckResult(repo, name, True)


def db_unchanged_check(before: str | None, after: str | None) -> CheckResult:
    name = "боевая assistant.db не изменена"
    if before is None or after is None:
        return CheckResult(REPO_BOTH, name, False, "не удалось вычислить хеш боевой БД")
    if before != after:
        return CheckResult(REPO_BOTH, name, False, "хеш боевой БД изменился во время прогона")
    return CheckResult(REPO_BOTH, name, True)


def _rel_to(path: Path, base: Path) -> str:
    """Путь относительно корня репозитория; вне него - как есть."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def persona_drift_check(
    chat_copy: Path, core_copy: Path, name: str = "синтетическая персона (дрейф SHA-256)"
) -> CheckResult:
    """Две копии общего тестового файла (chat-app и assistant-core) должны совпадать по SHA-256."""
    for path in (chat_copy, core_copy):
        if not path.is_file():
            return CheckResult(REPO_BOTH, name, False, f"нет файла: {path}")
    try:
        same = sha256_file(chat_copy) == sha256_file(core_copy)
    except OSError as exc:
        return CheckResult(REPO_BOTH, name, False, f"не удалось прочитать копии: {_exc_text(exc)}")
    if not same:
        return CheckResult(
            REPO_BOTH, name, False,
            f"копии различаются — синхронизируйте {_rel_to(chat_copy, CHAT_DIR)} "
            f"и {_rel_to(core_copy, CORE_DIR)} в assistant-core",
        )
    return CheckResult(REPO_BOTH, name, True)


def overall_green(results: list[CheckResult]) -> bool:
    return bool(results) and all(result.ok for result in results)


def render_report(results: list[CheckResult]) -> str:
    rows = [("Репозиторий", "Проверка", "Результат")]
    rows += [(r.repo, r.name, "✓" if r.ok else "✗") for r in results]
    w_repo = max(len(row[0]) for row in rows) + 2
    w_name = max(len(row[1]) for row in rows) + 2
    lines = ["Гейт качества", ""]
    for index, row in enumerate(rows):
        lines.append(f"{row[0].ljust(w_repo)}{row[1].ljust(w_name)}{row[2]}")
        if index > 0 and not results[index - 1].ok:
            for detail_line in results[index - 1].detail.splitlines():
                lines.append(f"  ↳ {detail_line}")
    lines.append("")
    lines.append("ИТОГ: ЗЕЛЁНЫЙ" if overall_green(results) else "ИТОГ: КРАСНЫЙ")
    return "\n".join(lines)


def _sha_or_none(path: Path) -> str | None:
    try:
        return sha256_file(path)
    except OSError:
        return None


def _exc_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _safe_pytest_step(repo: str, **kwargs) -> CheckResult:
    try:
        return run_pytest_step(repo=repo, **kwargs)
    except Exception as exc:  # неожиданный сбой шага - красная строка, не трассировка
        return CheckResult(repo, "pytest — тестов: 0", False, f"сбой шага: {_exc_text(exc)}")


def _safe_lint_step(repo: str, **kwargs) -> CheckResult:
    try:
        return run_lint_imports_step(repo=repo, **kwargs)
    except Exception as exc:  # неожиданный сбой шага - красная строка, не трассировка
        return CheckResult(repo, "import-linter", False, f"сбой шага: {_exc_text(exc)}")


def _safe_shield_step(repo: str, repo_dir: Path) -> CheckResult:
    try:
        return run_shield_step(repo, repo_dir)
    except Exception as exc:  # неожиданный сбой шага - красная строка, не трассировка
        return CheckResult(repo, "security_shield", False, f"сбой шага: {_exc_text(exc)}")


def _run_all(save_dir: Path | None) -> list[CheckResult]:
    results: list[CheckResult] = []
    before = _sha_or_none(LIVE_DB)
    tmp_dir = Path(tempfile.mkdtemp(prefix="gate-"))
    try:
        db_copy: Path | None = None
        try:
            db_copy = make_db_copy(LIVE_DB, tmp_dir)
        except Exception as exc:
            results.append(CheckResult(
                REPO_BOTH, "копия assistant.db для тестов", False,
                f"не удалось создать копию: {_exc_text(exc)}",
            ))
        if db_copy is None:
            results.append(CheckResult(
                REPO_CHAT, "pytest — тестов: 0", False, "не запущен: нет копии БД",
            ))
        else:
            results.append(_safe_pytest_step(
                REPO_CHAT, pytest_bin=CHAT_VENV_BIN / "pytest", target="backend/tests",
                cwd=CHAT_DIR, env_extra=chat_pytest_env(db_copy),
                tmp_dir=tmp_dir, save_dir=save_dir,
            ))
        # lint-imports кладёт в sys.path только cwd, а пакет app лежит в backend/.
        results.append(_safe_lint_step(
            REPO_CHAT, lint_bin=CHAT_VENV_BIN / "lint-imports", cwd=CHAT_DIR,
            env_extra={"PYTHONPATH": str(CHAT_DIR / "backend")},
        ))
        # Без переопределения БД: src/config.py вызывает load_dotenv(..., override=True).
        results.append(_safe_pytest_step(
            REPO_CORE, pytest_bin=CORE_VENV_BIN / "pytest", target=str(CORE_DIR / "tests"),
            cwd=CORE_DIR, env_extra=None, tmp_dir=tmp_dir, save_dir=save_dir,
        ))
        results.append(_safe_lint_step(
            REPO_CORE, lint_bin=CORE_VENV_BIN / "lint-imports", cwd=CORE_DIR, env_extra=None,
        ))
        results.append(_safe_shield_step(REPO_CHAT, CHAT_DIR))
        results.append(_safe_shield_step(REPO_CORE, CORE_DIR))
        results.append(persona_drift_check(CHAT_PERSONA, CORE_PERSONA))
        results.append(
            persona_drift_check(CHAT_TOKENS, CORE_TOKENS, name="токены персоны (дрейф SHA-256)")
        )
        results.append(db_unchanged_check(before, _sha_or_none(LIVE_DB)))
    finally:
        # В каталоге копия боевой БД и архив test_gdrive_client с копией секретов.
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Локальный гейт качества (оба репозитория).")
    parser.add_argument(
        "--save-pytest-output", metavar="DIR",
        help="сохранить сырой вывод pytest -v каждого репозитория в DIR (снимок baseline)",
    )
    args = parser.parse_args(argv)
    save_dir = Path(args.save_pytest_output).resolve() if args.save_pytest_output else None
    try:
        results = _run_all(save_dir)
    except Exception as exc:
        results = [CheckResult(REPO_BOTH, "работа гейта", False, f"внутренняя ошибка: {_exc_text(exc)}")]
    print(render_report(results))
    return 0 if overall_green(results) else 1


if __name__ == "__main__":
    sys.exit(main())
