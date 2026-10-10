"""Модульные тесты общей библиотеки безопасности assistant_shared.security (SEC-01)."""

from pathlib import Path
import pytest

from assistant_shared.security import (
    DEFAULT_REMOTE_VIOLATION,
    FORBIDDEN_FILES,
    NdaRemoteRule,
    SECRET_PATTERNS,
    check_file_content,
    nda_rule_for,
    normalize_remote,
)

from .nda_helpers import owner_nda_keywords


def test_secret_patterns_include_generic_bearer():
    """Проверяет наличие шаблона Generic Bearer Secret в SECRET_PATTERNS (SEC-01)."""
    pattern_names = [name for name, _ in SECRET_PATTERNS]
    assert "Generic Bearer Secret" in pattern_names

    # Проверка срабатывания регулярного выражения Generic Bearer
    generic_pat = next(pat for name, pat in SECRET_PATTERNS if name == "Generic Bearer Secret")
    assert generic_pat.search("api" + "_key = 'abcdef1234567890'")
    assert generic_pat.search("AUTH" + '_TOKEN = "secret_token_12345"')
    assert generic_pat.search("secret" + "-key: 'my_very_secret_key_value'")


def test_normalize_remote_formats():
    """Проверяет корректность нормализации remote url для HTTPS, SSH и SCP форматов (WR-07)."""
    expected = "git.example.org/exampleorg/chat-app"
    assert normalize_remote("https://git.example.org/ExampleOrg/chat-app.git") == expected
    assert normalize_remote("ssh://git@git.example.org/ExampleOrg/chat-app") == expected
    assert normalize_remote("git@git.example.org:ExampleOrg/chat-app.git") == expected
    assert normalize_remote("http://git.example.org/exampleorg/chat-app/") == expected


def test_nda_rule_for_clearance():
    """Проверяет создание правила NDA только для clearance == 'restricted_nda' (fail-closed)."""
    # Публичное пространство
    public_ws = {"clearance": "public", "forbidden_remote_substrings": ["github.com/foo"]}
    assert nda_rule_for(public_ws) is None

    # Внутреннее пространство
    internal_ws = {"clearance": "internal"}
    assert nda_rule_for(internal_ws) is None

    # NDA пространство с кастомным сообщением
    nda_ws = {
        "clearance": "restricted_nda",
        "forbidden_remote_substrings": ["github.com/personal"],
        "remote_violation_message": "Запрещено пушить в личный гит!",
    }
    rule = nda_rule_for(nda_ws)
    assert rule is not None
    assert rule.forbidden_remote_substrings == ("github.com/personal",)
    assert rule.violation_message == "Запрещено пушить в личный гит!"

    # NDA пространство без кастомного сообщения (дефолтное сообщение)
    nda_ws_default = {
        "clearance": "restricted_nda",
        "forbidden_remote_substrings": ["github.com/bad"],
    }
    rule_default = nda_rule_for(nda_ws_default)
    assert rule_default is not None
    assert rule_default.violation_message == DEFAULT_REMOTE_VIOLATION


def test_check_file_content_secrets(tmp_path: Path):
    """Проверяет обнаружение утечек секретов в файлах."""
    secret_file = tmp_path / "leaked.py"
    secret_file.write_text("API" + "_KEY = 'super_secret_bearer_token_12345'\n", encoding="utf-8")

    violations = check_file_content(secret_file, is_public_repo=True)
    assert len(violations) >= 1
    assert any("Generic Bearer Secret" in v for v in violations)


def test_check_file_content_forbidden_file(tmp_path: Path):
    """Проверяет обнаружение запрещённых имён файлов (.env, credentials.json)."""
    env_file = tmp_path / ".env.production"
    env_file.write_text("DEBUG=False\n", encoding="utf-8")

    violations = check_file_content(env_file, is_public_repo=True)
    assert len(violations) == 1
    assert "Forbidden file pattern committed" in violations[0]


def test_check_file_content_corporate_keywords(tmp_path: Path):
    """Проверяет обнаружение корпоративных ключевых слов NDA в публичных репозиториях."""
    code_file = tmp_path / "main.py"
    kw = owner_nda_keywords()[0]  # слово берётся из данных NDA-пространства, литерала в тесте нет
    code_file.write_text(f"val = '{kw}'\n", encoding="utf-8")

    # В публичном репозитории - нарушение
    pub_violations = check_file_content(code_file, is_public_repo=True, custom_keywords=[kw])
    assert len(pub_violations) == 1
    assert "proprietary corporate keyword" in pub_violations[0]

    # В приватном NDA репозитории - разрешено
    nda_violations = check_file_content(code_file, is_public_repo=False, custom_keywords=[kw])
    assert len(nda_violations) == 0
