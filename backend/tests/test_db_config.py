"""Тест конфигурации пути к SQLite из переменных окружения (DAT-02, D-06)."""

import os
from pathlib import Path
from app.core.config import Settings


def test_sqlite_db_path_default() -> None:
    """По умолчанию путь к БД относительный, без хардкода assistant-core."""
    # Очищаем env на время теста
    env = os.environ.copy()
    env.pop("SQLITE_DB_PATH", None)
    env.pop("DATABASE_PATH", None)
    s = Settings(_env_file=None, **{})
    assert s.SQLITE_DB_PATH == "./data/assistant.db"


def test_sqlite_db_path_from_sqlite_db_path_env(monkeypatch) -> None:
    """Путь читается из переменной окружения SQLITE_DB_PATH."""
    monkeypatch.setenv("SQLITE_DB_PATH", "/tmp/custom_chat.db")
    s = Settings(_env_file=None)
    assert s.SQLITE_DB_PATH == "/tmp/custom_chat.db"


def test_sqlite_db_path_from_database_path_alias(monkeypatch) -> None:
    """Путь читается из алиаса переменной окружения DATABASE_PATH."""
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    monkeypatch.setenv("DATABASE_PATH", "/tmp/alias_db.db")
    s = Settings(_env_file=None)
    assert s.SQLITE_DB_PATH == "/tmp/alias_db.db"


def test_no_hardcoded_assistant_core_path_in_config() -> None:
    """Проверяет отсутствие строкового хардкода /opt/assistant-core/data/assistant.db в config.py."""
    config_file = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"
    content = config_file.read_text(encoding="utf-8")
    assert "/opt/assistant-core/data/assistant.db" not in content, (
        "Обнаружен строковый хардкод /opt/assistant-core/data/assistant.db в config.py"
    )
