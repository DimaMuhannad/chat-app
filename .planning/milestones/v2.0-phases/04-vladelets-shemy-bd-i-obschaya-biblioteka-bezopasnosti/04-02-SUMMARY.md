---
phase: 04-vladelets-shemy-bd-i-obschaya-biblioteka-bezopasnosti
plan: 02
subsystem: database
tags: [sqlite, wal, busy_timeout, isolated-tests, config, DAT-02, DAT-03, DAT-04]

requires:
  - phase: 04-01
    provides: "assistant_shared.db.migrator и базовая DDL-схема SQLite"
provides:
  - "Фабрика подключений assistant_shared.db.connection (get_async_connection, get_sync_connection)"
  - "Гарантия PRAGMA journal_mode=WAL и PRAGMA busy_timeout=5000 во всех соединениях"
  - "Интеграционный тест test_concurrent_write.py (2 параллельных процесса по 100 транзакций записи)"
  - "Устранение хардкода /opt/assistant-core/data/assistant.db в config.py через SQLITE_DB_PATH / DATABASE_PATH"
  - "Полная изоляция тестов chat-app (140+ тестов) без обращения к каталогу assistant-core и боевой БД"
affects: [phase-04, phase-05, phase-06]

actuals:
  tokens: 22000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "WAL mode + busy_timeout=5000 для предотвращения ошибок database is locked"
    - "Динамическая конфигурация пути БД из переменных окружения (SQLITE_DB_PATH / DATABASE_PATH)"
    - "Изолированная сессионная фикстура БД на базе run_migrations без внешних CLI-процессов"

key-files:
  created:
    - /opt/assistant-shared/assistant_shared/db/connection.py
    - /opt/chat-app/backend/tests/test_concurrent_write.py
    - /opt/chat-app/backend/tests/test_db_config.py
    - /opt/chat-app/backend/tests/test_database_isolated.py
  modified:
    - /opt/assistant-shared/assistant_shared/db/__init__.py
    - /opt/assistant-core/src/storage/db.py
    - /opt/chat-app/backend/app/core/config.py
    - /opt/chat-app/backend/app/db.py
    - /opt/chat-app/backend/tests/conftest.py
    - /opt/chat-app/backend/tests/test_gate.py
    - /opt/chat-app/backend/tests/test_nda_equivalence.py

key-decisions:
  - "Единая фабрика get_async_connection / get_sync_connection в assistant_shared гарантирует WAL, busy_timeout=5000, foreign_keys=ON и synchronous=NORMAL"
  - "Хардкод пути /opt/assistant-core/data/assistant.db заменён на Pydantic Field с валидационным алиасом AliasChoices('SQLITE_DB_PATH', 'DATABASE_PATH') и дефолтом './data/assistant.db'"
  - "Фикстура conftest.py создаёт изолированную временную БД через run_migrations и наполняет сущности напрямую через SQLite-дескриптор, исключая обращение к боевой БД"
  - "Межрепозиторные тесты test_gate.py и test_nda_equivalence.py безопасно пропускают проверку внешнего репозитория при ASSISTANT_CORE_DIR='/nonexistent'"

requirements-completed: [DAT-02, DAT-03, DAT-04]

coverage:
  - id: DAT-02-CONFIG
    description: "Конфигурация пути SQLite из переменных окружения"
    requirement: "DAT-02"
    verification:
      - kind: unit
        ref: "backend/tests/test_db_config.py (4 passed)"
        status: pass
    human_judgment: false
  - id: DAT-03-CONCURRENCY
    description: "Фабрика соединений WAL/busy_timeout и тест конкурентной записи двух процессов"
    requirement: "DAT-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_concurrent_write.py (passed, 200 строк в 4 таблицах)"
        status: pass
    human_judgment: false
  - id: DAT-04-ISOLATION
    description: "Полная изоляция тестов chat-app от assistant-core"
    requirement: "DAT-04"
    verification:
      - kind: unit
        ref: "ASSISTANT_CORE_DIR=/nonexistent pytest backend/tests (140 passed, 2 skipped)"
        status: pass
    human_judgment: false

status: complete
completed: 2026-10-04
---

# Phase 4 Plan 02: Конфигурация пути БД из env, фабрика соединений WAL/busy_timeout и изоляция тестов chat-app Summary

**Реализована единая фабрика соединений SQLite с WAL-режимом и защитой от блокировок `busy_timeout=5000`, подтверждена безопасность одновременной записи двух процессов, удален хардкод пути боевой базы, а набор тестов `chat-app` полностью изолирован от внешнего репозитория `assistant-core`.**

## Performance

- **Tasks:** 2 из 2 выполнено
- **Commits:**
  - `assistant-shared`: `2575c83` (feat(db): implement SQLite connection factory with WAL and busy_timeout)
  - `assistant-core`: `afb7c08` (feat(db): use assistant_shared connection factory in Database.connection)
  - `chat-app`:
    - `fd08aa5` (feat(db): use assistant_shared connection factory and add concurrent write stress test)
    - `a9fe607` (feat(db): read SQLite path from env and isolate chat-app test suite)

## Accomplishments

- **Фабрика соединений WAL/busy_timeout (Задача 04-02-01):**
  - В `assistant_shared.db.connection` реализованы `get_async_connection` и `get_sync_connection`.
  - Все соединения автоматически настраивают `PRAGMA journal_mode = WAL;`, `PRAGMA busy_timeout = 5000;`, `PRAGMA foreign_keys = ON;`, `PRAGMA synchronous = NORMAL;`.
  - Функция `get_db()` в `chat-app/backend/app/db.py` и `Database.connection()` в `assistant-core/src/storage/db.py` переведены на фабрику.
  - Разработан интеграционный тест `test_concurrent_write.py`, доказавший отсутствие сбоев `database is locked` при одновременной записи двумя независимыми процессами 200 транзакций по 4 связанным таблицам.

- **Устранение хардкода и изоляция тестов (Задача 04-02-02):**
  - Из `chat-app/backend/app/core/config.py` полностью удалён строковый хардкод `/opt/assistant-core/data/assistant.db`. Путь читается через `AliasChoices("SQLITE_DB_PATH", "DATABASE_PATH")` с локальным дефолтом `"./data/assistant.db"`.
  - Модульный тест `test_db_config.py` подтвердил чтение путей из обоих псевдонимов и отсутствие хардкода.
  - Сессионная фикстура `conftest.py` переписана: исключены внешние `subprocess`-вызовы к `src.persona.seed` и резервное копирование боевой базы; временная БД инициализируется через `run_migrations` и заполняется каноническими сущностями напрямую.
  - В тестах `test_gate.py` и `test_nda_equivalence.py` добавлены безопасные `pytest.skip` при недоступности внешнего репозитория `assistant-core`.
  - Создан интеграционный тест `test_database_isolated.py`, подтверждающий полную работоспособность CRUD-операций на изолированной БД.

## Verification Results

- `test_db_config.py`: 4 passed
- `test_concurrent_write.py`: 1 passed (0 ошибок блокировок, 200 записей)
- `test_database_isolated.py`: 3 passed
- Полный прогон `chat-app` в режиме изоляции (`ASSISTANT_CORE_DIR="/nonexistent"`): **140 passed, 2 skipped** (0 failed)
- Полный прогон `chat-app` в штатном режиме: **142 passed** (0 failed)
- Прогон тестов `assistant-core`: 15 passed (архитектура ядра и хранилище персон не затронуты)
- Неприкосновенность боевой БД: `/opt/assistant-core/data/assistant.db` не открывалась на запись.

## Self-Check: PASSED
- Файлы созданы и закоммичены во всех затронутых репозиториях.
- Отсутствуют регрессии в существующих модулях и тестах.
