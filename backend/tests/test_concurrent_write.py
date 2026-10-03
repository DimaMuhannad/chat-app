"""Стресс-тест конкурентной записи двух процессов с PRAGMA journal_mode=WAL (DAT-03)."""

import multiprocessing
from pathlib import Path
import time
import pytest

from assistant_shared.db.connection import get_sync_connection
from assistant_shared.db.migrator import run_migrations


def _worker_write_batch(args: tuple[str, int, int]) -> int:
    """Воркер отдельного процесса, выполняющий пачку транзакций записи.

    Каждая транзакция создает связанные записи:
    projects -> tasks -> reminders -> documents.
    """
    db_path, worker_id, count = args
    written = 0
    with get_sync_connection(db_path) as conn:
        for i in range(count):
            proj_name = f"Проект worker_{worker_id}_{i}"
            task_title = f"Задача worker_{worker_id}_{i}"
            reminder_what = f"Напоминание worker_{worker_id}_{i}"
            doc_title = f"Документ worker_{worker_id}_{i}"

            with conn:
                cur = conn.execute(
                    "INSERT INTO projects (name, area, status) VALUES (?, 'ГУАП', 'active');",
                    (proj_name,),
                )
                proj_id = cur.lastrowid

                cur = conn.execute(
                    "INSERT INTO tasks (project_id, title, area, priority, status) VALUES (?, ?, 'ГУАП', 'P1', 'todo');",
                    (proj_id, task_title),
                )
                task_id = cur.lastrowid

                conn.execute(
                    "INSERT INTO reminders (task_id, what, check_date, status) VALUES (?, ?, '2026-10-10', 'active');",
                    (task_id, reminder_what),
                )

                conn.execute(
                    "INSERT INTO documents (project_id, title, content_markdown) VALUES (?, ?, '# Описание');",
                    (proj_id, doc_title),
                )

            written += 1
            # Микрозадержка для создания конкуренции и провокации блокировки
            time.sleep(0.001)

    return written


def test_concurrent_write_two_processes(tmp_path: Path) -> None:
    """Интеграционный тест: два процесса одновременно пишут по 100 записей без блокировок (D-08)."""
    db_file = str(tmp_path / "concurrent_test.db")
    run_migrations(db_file)

    items_per_worker = 100
    worker_args = [
        (db_file, 1, items_per_worker),
        (db_file, 2, items_per_worker),
    ]

    with multiprocessing.Pool(processes=2) as pool:
        results = pool.map(_worker_write_batch, worker_args)

    assert results == [items_per_worker, items_per_worker]

    with get_sync_connection(db_file) as conn:
        for table in ["projects", "tasks", "reminders", "documents"]:
            cur = conn.execute(f"SELECT count(*) FROM {table};")
            count = cur.fetchone()[0]
            assert count == 200, f"Таблица {table} содержит {count} строк вместо 200"
