---
phase: 04-vladelets-shemy-bd-i-obschaya-biblioteka-bezopasnosti
plan: 01
subsystem: database
tags: [migrations, schema, ddl, assistant-shared, DAT-01]

requires:
  - phase: 03-persona-kak-dannye
    provides: "Данные персон, коннекторов и воркспейсов в SQLite"
provides:
  - "Локальный Python-пакет /opt/assistant-shared с модулем assistant_shared.db.migrator"
  - "Базовая DDL-миграция 0001_initial_schema.sql, воспроизводящая все таблицы платформы"
  - "Рефакторинг init_db() в assistant-core/src/storage/db.py с удалением 475 строк ad-hoc DDL"
  - "Модульные тесты мигратора backend/tests/test_migrations.py (6 тестов: инициализация, :memory:, aiosqlite, идемпотентность, baseline-детекция)"
affects: [phase-04, phase-05, phase-06]

actuals:
  tokens: 15000
  tasks: 2
  commits: 3

tech-stack:
  added:
    - assistant-shared (локальный пакет /opt/assistant-shared)
  patterns:
    - "Версионированные SQL-миграции с таблицей schema_migrations (KISS)"
    - "Идемпотентная детекция baseline для уже существующей базы данных"
    - "Поддержка как файловых баз SQLite, так и активных дескрипторов :memory: / aiosqlite"

key-files:
  created:
    - /opt/assistant-shared/pyproject.toml
    - /opt/assistant-shared/README.md
    - /opt/assistant-shared/assistant_shared/__init__.py
    - /opt/assistant-shared/assistant_shared/db/__init__.py
    - /opt/assistant-shared/assistant_shared/db/migrator.py
    - /opt/assistant-shared/assistant_shared/db/migrations/__init__.py
    - /opt/assistant-shared/assistant_shared/db/migrations/0001_initial_schema.sql
    - /opt/chat-app/backend/tests/test_migrations.py
  modified:
    - /opt/assistant-core/src/storage/db.py

key-decisions:
  - "Локальный пакет /opt/assistant-shared подключён в оба виртуальных окружения (.venv) через assistant_shared.pth для обхода отсутствия setuptools в Python 3.12"
  - "Мигратор поддерживает исполнение на активных дескрипторах SQLite / aiosqlite для сохранения :memory: баз в тестах"
  - "Схема 0001_initial_schema.sql включает все таблицы ядра (personas, workspaces, connector_bindings, tasks, reminders, methodist_*), устраняя необходимость множественных ALTER TABLE при старте"

requirements-completed: [DAT-01]

coverage:
  - id: DAT-01-MIGRATOR
    description: "Единый версионированный мигратор схемы БД в assistant-shared"
    requirement: "DAT-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_migrations.py (6 passed)"
        status: pass
    human_judgment: false
  - id: DAT-01-CORE-INIT
    description: "Делегирование init_db() в assistant-core на вызов run_migrations"
    requirement: "DAT-01"
    verification:
      - kind: unit
        ref: "assistant-core/src/storage/db.py refactored, commit 51cf4d1"
        status: pass
    human_judgment: false

status: complete
completed: 2026-10-03
---

# Phase 4 Plan 01: Создание пакета assistant-shared, DDL-мигратора и базовой схемы SQLite Summary

**Создан локальный Python-пакет `/opt/assistant-shared` с легковесным SQL-мигратором и базовой миграцией `0001_initial_schema.sql`. Метод `init_db()` в `assistant-core/src/storage/db.py` отрефакторен с удалением 475 строк устаревшего ad-hoc DDL.**

## Performance

- **Tasks:** 2 из 2 выполнено
- **Commits:**
  - `assistant-shared`: `3ad4e8e` (feat(db): initial assistant-shared package and SQL migrator)
  - `chat-app`: `055e33a` (test(migrations): add comprehensive test suite for assistant-shared migrator)
  - `assistant-core`: `51cf4d1` (feat(db): delegate init_db to assistant_shared.db.migrator)

## Accomplishments

- **Пакет `/opt/assistant-shared` (Задача 04-01-01):**
  - Создана модульная структура пакета с `pyproject.toml` (build-backend `setuptools.build_meta`).
  - Пакет интегрирован в виртуальные окружения `/opt/chat-app/backend/.venv` и `/opt/assistant-core/.venv` через `.pth`-ссылки в `site-packages`.
  - Сформирована базовая DDL-миграция `0001_initial_schema.sql`, объединяющая все таблицы и индексы платформы, включая `personas`, `workspaces`, `connector_bindings`, `methodist_chunks_fts` и триггеры.
  - Реализован `migrator.py`: функции `run_migrations`, `get_schema_version`, `list_applied_migrations` с поддержкой файловых путей и дескрипторов соединений SQLite / aiosqlite.

- **Рефакторинг `init_db()` и тесты идемпотентности (Задача 04-01-02):**
  - В `backend/tests/test_migrations.py` реализованы 6 всесторонних тестов (накатывание на чистую базу, in-memory SQLite, in-memory aiosqlite, идемпотентность повторного вызова, baseline-детекция существующей БД без потери данных, пустая БД).
  - В `/opt/assistant-core/src/storage/db.py` удалено 475 строк императивных DDL `executescript` и цепочек `ALTER TABLE`, заменено на вызов `run_migrations`.
  - Обеспечена корректная работа с `:memory:` тестами в `assistant-core` благодаря передаче `check_same_thread=False` и активного соединения в мигратор.

## Verification Results

- `test_migrations.py`: 6 passed
- `test_core_architecture.py`: контракт чистоты ядра сохранён (ядро `src.core` не импортирует `assistant_shared`).
- Чистота боевой БД: `/opt/assistant-core/data/assistant.db` не затрагивалась.

## Self-Check: PASSED
- Файлы мигратора и миграции присутствуют в `/opt/assistant-shared`.
- Коммиты зафиксированы во всех трёх репозиториях.
