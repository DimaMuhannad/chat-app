"""Тесты модуля миграций и управления схемой SQLite (DAT-01)."""

import asyncio
import sqlite3
from pathlib import Path
import aiosqlite
import pytest

from assistant_shared.db.migrator import (
    get_schema_version,
    list_applied_migrations,
    run_migrations,
)

EXPECTED_CORE_TABLES = [
    "monitored_sources",
    "content_snapshots",
    "calendar_sync_records",
    "action_items",
    "email_messages",
    "email_threads",
    "email_drafts",
    "projects",
    "tasks",
    "reminders",
    "documents",
    "timesheet_records",
    "lms_submissions",
    "methodist_documents",
    "methodist_chunks",
    "methodist_chunks_fts",
    "methodist_qa_memory",
    "methodist_toc_index",
    "methodist_toc_fts",
    "bot_dialog_history",
    "memory_facts",
    "daily_primed_context",
    "pending_memory_reviews",
    "router_audit_log",
    "bot_live_ticker",
    "personas",
    "workspaces",
    "connector_bindings",
    "schema_migrations",
    "pending_confirmations",
]

LATEST_SCHEMA_VERSION = "0002_pending_confirmations"
ALL_MIGRATIONS = ["0001_initial_schema", "0002_pending_confirmations"]


def test_initial_schema_creates_all_tables(tmp_path: Path) -> None:
    """Проверяет, что на пустой БД миграции создают все таблицы платформы."""
    db_file = tmp_path / "test_init.db"
    applied = run_migrations(db_file)

    assert "0001_initial_schema" in applied
    assert "0002_pending_confirmations" in applied
    assert get_schema_version(db_file) == LATEST_SCHEMA_VERSION
    assert list_applied_migrations(db_file) == ALL_MIGRATIONS

    conn = sqlite3.connect(str(db_file))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual');")
        tables = {row[0] for row in cur.fetchall()}
        for expected in EXPECTED_CORE_TABLES:
            assert expected in tables, f"Таблица {expected} отсутствует в созданной БД"
    finally:
        conn.close()


def test_migrations_in_memory_connection() -> None:
    """Проверяет, что передача активного соединения :memory: не уничтожает БД при миграции."""
    conn = sqlite3.connect(":memory:")
    try:
        applied = run_migrations(conn)
        assert "0001_initial_schema" in applied
        assert "0002_pending_confirmations" in applied

        # База осталась активной и таблицы существуют в том же соединении
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='tasks';")
        assert cur.fetchone()[0] == 1
        assert get_schema_version(conn) == LATEST_SCHEMA_VERSION
    finally:
        conn.close()


def test_migrations_aiosqlite_in_memory_connection() -> None:
    """Проверяет передачу aiosqlite соединения :memory: в мигратор."""

    async def _test():
        async with aiosqlite.connect(":memory:", check_same_thread=False) as aio_conn:
            applied = run_migrations(aio_conn)
            assert "0001_initial_schema" in applied
            assert "0002_pending_confirmations" in applied

            async with aio_conn.execute("SELECT count(*) FROM schema_migrations;") as cursor:
                row = await cursor.fetchone()
                assert row[0] == 2

            async with aio_conn.execute("SELECT count(*) FROM tasks;") as cursor:
                row = await cursor.fetchone()
                assert row[0] == 0

    asyncio.run(_test())


def test_migrations_idempotency_empty_db(tmp_path: Path) -> None:
    """Повторный запуск миграций возвращает пустой список и ничего не меняет."""
    db_file = tmp_path / "test_idempotent.db"
    first_applied = run_migrations(db_file)
    assert first_applied == ALL_MIGRATIONS

    second_applied = run_migrations(db_file)
    assert second_applied == []
    assert get_schema_version(db_file) == LATEST_SCHEMA_VERSION


def test_migrations_baseline_detection_existing_db(tmp_path: Path) -> None:
    """Существующая БД с прикладными таблицами распознаётся как baseline (D-05)."""
    db_file = tmp_path / "test_baseline.db"
    conn = sqlite3.connect(str(db_file))
    try:
        # Создаем таблицы в структуре реального хранилища до введения schema_migrations
        conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                title TEXT NOT NULL,
                area TEXT NOT NULL DEFAULT 'ГУАП',
                priority TEXT NOT NULL DEFAULT 'P2',
                status TEXT NOT NULL DEFAULT 'todo',
                due_date TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                area TEXT NOT NULL DEFAULT 'ГУАП',
                status TEXT NOT NULL DEFAULT 'active'
            );
            """
        )
        conn.execute("INSERT INTO tasks (title) VALUES ('Существующая задача');")
        conn.execute("INSERT INTO projects (name) VALUES ('Существующий проект');")
        conn.commit()
    finally:
        conn.close()

    # Запускаем миграции
    applied = run_migrations(db_file)
    assert "0001_initial_schema" in applied
    assert "0002_pending_confirmations" in applied
    assert get_schema_version(db_file) == LATEST_SCHEMA_VERSION

    # Проверяем, что пользовательские данные не затронуты
    conn = sqlite3.connect(str(db_file))
    try:
        cur = conn.cursor()
        cur.execute("SELECT title FROM tasks;")
        assert cur.fetchone()[0] == "Существующая задача"
        cur.execute("SELECT name FROM projects;")
        assert cur.fetchone()[0] == "Существующий проект"

        # Недостающие таблицы (например personas) были досозданы
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='personas';")
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()

    # Повторный вызов идемпотентен
    assert run_migrations(db_file) == []


def test_get_schema_version_empty_db(tmp_path: Path) -> None:
    """Пустая БД без миграций возвращает None."""
    db_file = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_file))
    conn.close()
    assert get_schema_version(db_file) is None
    assert list_applied_migrations(db_file) == []
