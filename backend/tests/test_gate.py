"""Юнит-тесты чистых функций локального гейта scripts/gate.py.

Здесь нет запуска полного гейта и подпроцессов pytest: гейт сам запускает
pytest chat-app, и такой вызов из теста дал бы рекурсию.
"""

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "gate.py"
_spec = importlib.util.spec_from_file_location("gate", _GATE_PATH)
gate = importlib.util.module_from_spec(_spec)
# dataclass в модуле с отложенными аннотациями ищет свой модуль в sys.modules
sys.modules["gate"] = gate
_spec.loader.exec_module(gate)

CheckResult = gate.CheckResult

JUNIT_SUITES = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<testsuites><testsuite name="pytest" errors="1" failures="2" skipped="3" tests="14">'
    '<testcase classname="backend.tests.test_a" name="test_ok"/>'
    '<testcase classname="backend.tests.test_a" name="test_bad"><failure message="x"/></testcase>'
    '<testcase classname="backend.tests.test_b" name="test_err"><error message="y"/></testcase>'
    "</testsuite></testsuites>"
)
JUNIT_SUITE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="7"/>'
)

GOOD_COUNTS = {"tests": 14, "failures": 0, "errors": 0, "skipped": 0}


def _write(tmp_path, text):
    path = tmp_path / "junit.xml"
    path.write_text(text, encoding="utf-8")
    return path


def test_pytest_counts_testsuites_root(tmp_path):
    counts = gate.pytest_counts(_write(tmp_path, JUNIT_SUITES))
    assert counts == {"tests": 14, "failures": 2, "errors": 1, "skipped": 3}


def test_pytest_counts_testsuite_root(tmp_path):
    counts = gate.pytest_counts(_write(tmp_path, JUNIT_SUITE))
    assert counts == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}


def test_failed_test_ids_lists_failures_and_errors(tmp_path):
    ids = gate.failed_test_ids(_write(tmp_path, JUNIT_SUITES))
    assert ids == ["backend.tests.test_a::test_bad", "backend.tests.test_b::test_err"]


def test_pytest_ok_green_case():
    assert gate.pytest_ok(0, GOOD_COUNTS, []) is True


@pytest.mark.parametrize(
    "returncode, counts, flags",
    [
        (0, {**GOOD_COUNTS, "skipped": 1}, []),
        (0, {**GOOD_COUNTS, "tests": 0}, []),
        (5, {**GOOD_COUNTS, "tests": 0}, []),
        (1, GOOD_COUNTS, []),
        (0, {**GOOD_COUNTS, "failures": 1}, []),
        (0, {**GOOD_COUNTS, "errors": 1}, []),
        (0, GOOD_COUNTS, ["deselected"]),
        (0, GOOD_COUNTS, ["xfailed"]),
    ],
)
def test_pytest_ok_red_cases(returncode, counts, flags):
    assert gate.pytest_ok(returncode, counts, flags) is False


def test_pytest_summary_flags_hidden_deselect_and_xfail():
    output = "...\n=== 10 passed, 2 deselected, 1 xfailed in 3.50s ===\n"
    assert gate.pytest_summary_flags(output) == ["deselected", "xfailed"]


def test_pytest_summary_flags_clean_run():
    assert gate.pytest_summary_flags("=== 14 passed in 2.10s ===\n") == []


def test_pytest_summary_flags_ignores_warnings_word():
    assert gate.pytest_summary_flags("=== 127 passed, 31 warnings in 45.00s ===\n") == []


def test_overall_green_empty_list_is_red():
    assert gate.overall_green([]) is False


def test_render_report_all_green():
    report = gate.render_report([CheckResult("chat-app", "pytest — тестов: 14", True)])
    assert report.splitlines()[-1] == "ИТОГ: ЗЕЛЁНЫЙ"
    assert "✓" in report


def test_render_report_one_red():
    report = gate.render_report([
        CheckResult("chat-app", "pytest — тестов: 14", True),
        CheckResult("assistant-core", "pytest — тестов: 0", False, "не найден pytest"),
    ])
    assert report.splitlines()[-1] == "ИТОГ: КРАСНЫЙ"
    assert "✗" in report
    assert "↳ не найден pytest" in report


def test_chat_pytest_env_requires_copy():
    with pytest.raises(ValueError):
        gate.chat_pytest_env(None)


def test_chat_pytest_env_refuses_live_db():
    with pytest.raises(ValueError):
        gate.chat_pytest_env(gate.LIVE_DB)


def test_chat_pytest_env_points_to_copy(tmp_path):
    copy = tmp_path / "assistant-copy.db"
    assert gate.chat_pytest_env(copy) == {"SQLITE_DB_PATH": str(copy)}


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "blob.bin"
    path.write_bytes(b"gate" * 1000)
    assert gate.sha256_file(path) == hashlib.sha256(b"gate" * 1000).hexdigest()


def test_db_unchanged_check_none_hash_is_red():
    assert gate.db_unchanged_check(None, "x").ok is False
    assert gate.db_unchanged_check("x", None).ok is False


def test_db_unchanged_check_differing_hash_is_red():
    assert gate.db_unchanged_check("a", "b").ok is False


def test_db_unchanged_check_equal_hash_is_green():
    assert gate.db_unchanged_check("a", "a").ok is True


def test_lint_imports_step_missing_binary_is_red_without_exception(tmp_path):
    result = gate.run_lint_imports_step(
        "chat-app", tmp_path / "нет" / "lint-imports", tmp_path, None
    )
    assert result.ok is False
    assert "requirements-dev.txt" in result.detail


def test_persona_drift_check_identical_copies_is_green(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_bytes(b"SYNTHETIC_PERSONA = {}\n")
    b.write_bytes(b"SYNTHETIC_PERSONA = {}\n")
    result = gate.persona_drift_check(a, b)
    assert result.ok is True
    assert result.name == "синтетическая персона (дрейф SHA-256)"


def test_persona_drift_check_different_copies_is_red(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_bytes(b"SYNTHETIC_PERSONA = {}\n")
    b.write_bytes(b"SYNTHETIC_PERSONA = {'x': 1}\n")
    result = gate.persona_drift_check(a, b)
    assert result.ok is False
    assert "синхронизируйте" in result.detail


def test_persona_drift_check_missing_file_is_red_without_exception(tmp_path):
    a = tmp_path / "a.py"
    a.write_bytes(b"x")
    result = gate.persona_drift_check(a, tmp_path / "нет.py")
    assert result.ok is False
    assert "нет файла" in result.detail


def test_persona_drift_check_uses_given_name(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_bytes(b"x = 1\n")
    b.write_bytes(b"x = 2\n")
    named = "токены персоны (дрейф SHA-256)"
    assert gate.persona_drift_check(a, a, name=named).name == named
    red = gate.persona_drift_check(a, b, name=named)
    assert red.name == named and red.ok is False
    # имя по умолчанию не изменилось
    assert gate.persona_drift_check(a, a).name == "синтетическая персона (дрейф SHA-256)"


def test_gate_checks_persona_tokens_pair():
    assert gate.CHAT_TOKENS == gate.CHAT_DIR / "backend" / "tests" / "persona_tokens.py"
    assert gate.CORE_TOKENS == gate.CORE_DIR / "tests" / "persona_tokens.py"
    if not gate.CORE_DIR.is_dir():
        pytest.skip("assistant-core not available in isolated test mode")
    assert gate.CHAT_TOKENS.is_file() and gate.CORE_TOKENS.is_file()
    source = " ".join(Path(gate.__file__).read_text(encoding="utf-8").split())
    assert "persona_drift_check(CHAT_PERSONA, CORE_PERSONA)" in source
    assert (
        'persona_drift_check(CHAT_TOKENS, CORE_TOKENS, name="токены персоны (дрейф SHA-256)")'
        in source
    )


# --- security_shield: разбор и сверка находок (синтетический вывод) ---

_SYNTH_HEADER = (
    "\U0001F6E1 Running Security Shield on repository: {repo}\n"
    "   • Origin Remote: https://git.example/synthetic/repo.git\n"
    "   • Author Email:  synthetic-author.example\n"
    "   • Profile Mode:  PUBLIC / ACADEMIC\n"
    "   • Scanning 7 files...\n"
)


def _synthetic_shield_output(repo: Path) -> str:
    marker = "synthetic_marker_alpha"
    return (
        _SYNTH_HEADER.format(repo=repo)
        + "\n❌ SECURITY VIOLATIONS DETECTED:\n"
        + f"   \U0001F6A8 {repo}/docs/a.md:3 - Found proprietary corporate keyword '{marker}' in public repository!\n"
        + f"   \U0001F6A8 {repo}/docs/a.md:9 - Found proprietary corporate keyword '{marker}' in public repository!\n"
        + f"   \U0001F6A8 {repo}/tests/t.py:12 - Found potential Generic Bearer Secret\n"
        + "   \U0001F6A8 something unexpected without a known shape\n"
        + "\nCommit or push blocked.\n"
    )


def test_parse_shield_findings_normalizes_and_drops_sensitive_text(tmp_path):
    found = gate.parse_shield_findings(_synthetic_shield_output(tmp_path), tmp_path)
    assert found == {
        ("docs/a.md", "nda-keyword"): 2,
        ("tests/t.py", "secret:Generic Bearer Secret"): 1,
        ("(нераспознано)", "unparsed"): 1,
    }
    flat = " ".join(f"{path} {kind} {count}" for (path, kind), count in found.items())
    assert "synthetic_marker_alpha" not in flat
    assert "git.example" not in flat
    assert "Origin" not in flat


def test_parse_shield_findings_special_kinds(tmp_path):
    output = (
        "   \U0001F6A8 Forbidden file pattern committed: credentials.json\n"
        "   \U0001F6A8 CRITICAL: synthetic remote problem\n"
        f"   \U0001F6A8 {tmp_path}/x.bin - Read error: boom\n"
    )
    assert gate.parse_shield_findings(output, tmp_path) == {
        ("credentials.json", "forbidden-file"): 1,
        ("(remote)", "remote"): 1,
        ("x.bin", "read-error"): 1,
    }


def test_parse_shield_findings_ignores_header_only_output(tmp_path):
    assert not gate.parse_shield_findings(_SYNTH_HEADER.format(repo=tmp_path), tmp_path)


def test_compare_shield_findings_equal_sets_no_problems():
    found = gate.collections.Counter({("docs/a.md", "nda-keyword"): 2})
    assert gate.compare_shield_findings(found, {("docs/a.md", "nda-keyword"): 2}) == ([], [])


def test_compare_shield_findings_extra_finding_is_new():
    found = gate.collections.Counter({("docs/a.md", "nda-keyword"): 3})
    new, stale = gate.compare_shield_findings(found, {("docs/a.md", "nda-keyword"): 2})
    assert new and not stale
    assert "docs/a.md" in new[0]


def test_compare_shield_findings_missing_finding_is_stale():
    found = gate.collections.Counter({("docs/a.md", "nda-keyword"): 1})
    new, stale = gate.compare_shield_findings(found, {("docs/a.md", "nda-keyword"): 2})
    assert stale and not new


def _fake_repo(tmp_path, script_body: str) -> Path:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "security_shield.py").write_text(script_body, encoding="utf-8")
    return tmp_path


def test_run_shield_step_missing_script_is_red(tmp_path):
    result = gate.run_shield_step("chat-app", tmp_path)
    assert result.ok is False


def test_run_shield_step_unexpected_returncode_is_red(tmp_path):
    repo = _fake_repo(tmp_path, "import sys\nsys.exit(2)\n")
    result = gate.run_shield_step("chat-app", repo)
    assert result.ok is False
    assert "сбой" in result.detail


def test_run_shield_step_code_one_without_findings_is_red(tmp_path):
    repo = _fake_repo(tmp_path, "import sys\nprint('Scanning 3 files...')\nsys.exit(1)\n")
    result = gate.run_shield_step("chat-app", repo)
    assert result.ok is False
    assert "без распознанных находок" in result.detail


def test_run_shield_step_empty_scan_is_red_in_all_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "SHIELD_MODE", "all")
    repo = _fake_repo(tmp_path, "print('No staged or modified files found to scan.')\n")
    result = gate.run_shield_step("chat-app", repo)
    assert result.ok is False
    assert "ничего не просканировал" in result.detail


def test_run_shield_step_clean_scan_is_green(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "SHIELD_MODE", "all")
    monkeypatch.setitem(gate.KNOWN_SHIELD_FALSE_POSITIVES, "synthetic-repo", {})
    repo = _fake_repo(tmp_path, "print('Scanning 4 files...')\n")
    assert gate.run_shield_step("synthetic-repo", repo).ok is True


def test_run_shield_step_new_finding_is_red_without_raw_output(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "SHIELD_MODE", "all")
    monkeypatch.setitem(gate.KNOWN_SHIELD_FALSE_POSITIVES, "synthetic-repo", {})
    body = (
        "import sys\n"
        "print('   \\u2022 Origin Remote: https://git.example/synthetic/repo.git')\n"
        "print('Scanning 4 files...')\n"
        "print('   \\U0001F6A8 /x/docs/a.md:3 - Found proprietary corporate keyword "
        "synthetic_marker_alpha in public repository!')\n"
        "sys.exit(1)\n"
    )
    repo = _fake_repo(tmp_path, body)
    result = gate.run_shield_step("synthetic-repo", repo)
    assert result.ok is False
    assert "новая находка" in result.detail
    assert "synthetic_marker_alpha" not in result.detail
    assert "git.example" not in result.detail


def test_known_shield_false_positives_total_is_eighteen():
    # 15 находок Фазы 1 + 3 в config/persona.yaml по решению владельца 2026-10-02 (OQ1).
    total = sum(sum(entries.values()) for entries in gate.KNOWN_SHIELD_FALSE_POSITIVES.values())
    assert total == 18
