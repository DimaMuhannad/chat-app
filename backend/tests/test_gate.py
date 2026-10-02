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
