# Phase 4: Владелец схемы БД и общая библиотека безопасности - Research

**Date:** 2026-10-03  
**Status:** Completed  
**Domain:** Database Schema Ownership, Versioned Migrations, WAL Concurrency, Shared Security Library, Pre-commit Guardrails

---

<user_constraints>
## User Constraints & Implementation Decisions (from 04-CONTEXT.md)

Владелец проекта (не являясь техническим специалистом в архитектуре ПО) согласовал передачу инженерных решений на усмотрение Claude (Claude's Discretion) по принципам KISS/YAGNI и стандартам проекта.

### 1. Физическое размещение общей библиотеки (DAT-01, SEC-01)
- **D-01:** Создаётся отдельный локальный Python-пакет в каталоге `/opt/assistant-shared` (с `pyproject.toml` / `setup.py`), который устанавливается в режиме разработки (`pip install -e /opt/assistant-shared`) в оба виртуальных окружения: `/opt/chat-app/backend/.venv` и `/opt/assistant-core/.venv`. — **Reversibility:** costly — изменение расположения библиотеки потребует переустановки в обоих окружениях и обновления путей импортов.
- **D-02:** Пакет `/opt/assistant-shared` объединяет:
  • Модели и DDL схемы базы данных (единый владелец схемы SQLite);
  • Механизм версионированных миграций;
  • Общую библиотеку безопасности (`assistant_shared.security`): `SECRET_PATTERNS`, `FORBIDDEN_FILES`, безопасный запуск команд `run_cmd()`, валидацию NDA-ограничений рабочих пространств;
  • Фабрику подключения к SQLite с обязательным включением PRAGMA WAL и timeout.

### 2. Движок миграций и версионирования схемы БД (DAT-01, DAT-02)
- **D-03:** Для версионирования схемы базы данных применяется легковесный SQL-раннер миграций (KISS). Каталог миграций содержит последовательно пронумерованные файлы (например, `0001_initial_schema.sql`, `0002_...sql`). Текущая версия схемы и история применённых миграций фиксируются в таблице `schema_migrations`. — **Reversibility:** costly — смена движка миграций на сторонний (Alembic) потребует адаптации файлов миграций.
- **D-04:** Базовая миграция `0001_initial_schema.sql` воспроизводит полное актуальное состояние таблиц (`tasks`, `reminders`, `projects`, `documents`, `personas`, `workspaces`, `connector_bindings`).
- **D-05:** Существующая рабочая база данных распознаётся идемпотентно: если таблицы уже созданы, мигратор регистрирует исходное состояние (базовую миграцию) без изменения пользовательских данных и структуры.
- **D-06:** Путь к файлу базы данных читается исключительно из переменных окружения/конфигурации (`SQLITE_DB_PATH` / `DATABASE_PATH`). Хардкод пути `/opt/assistant-core/data/assistant.db` в `chat-app/backend/app/core/config.py` удаляется.

### 3. Конкурентная запись и WAL-режим (DAT-03)
- **D-07:** При каждом создании соединения (как через `aiosqlite`, так и через синхронный `sqlite3`) библиотека гарантирует применение `PRAGMA journal_mode=WAL;` и `PRAGMA busy_timeout=5000;`.
- **D-08:** Создаётся интеграционный тест конкурентной записи (два параллельных процесса одновременно выполняют операции записи в `tasks`, `reminders`, `projects`, `documents` без ошибок `database is locked`).

### 4. Изоляция тестов chat-app (DAT-04)
- **D-09:** Набор тестов `pytest backend/tests` в `chat-app` переводится на pytest-фикстуру с временной чистой SQLite БД (`tempfile`), схема которой автоматически накатывается мигратором из `/opt/assistant-shared`.
- **D-10:** В тестах `chat-app` эмулируется недоступность каталога `/opt/assistant-core`, подтверждая возможность независимого тестирования `chat-app`. Сила существующих ассертов и проверок полностью сохраняется.

### 5. Общая безопасность и pre-commit hook (SEC-01, SEC-02, SEC-03)
- **D-11:** Модуль `backend/app/api/v1/security.py` в `chat-app` и компоненты `assistant-core` переходят на импорт общих проверок безопасности из пакета `/opt/assistant-shared`.
- **D-12:** Скрипты `scripts/security_shield.py` в обоих репозиториях переписываются как тонкие CLI-обёртки над библиотекой `/opt/assistant-shared`. Тест эквивалентности NDA подтверждает отсутствие дрейфа на наборе синтетических фикстур.
- **D-13:** Pre-commit hook размещается в репозиториях (скрипт установки `scripts/install_hooks.sh` настраивает запуск проверки безопасности перед коммитом). Hook блокирует фиксацию коммита при обнаружении токенов владельца, секретов или запрещённых файлов.

### Claude's Discretion
Все 4 архитектурные области реализации согласованы на усмотрение инженера-разработчика (Claude). Планировщик свободен в выборе внутренней структуры пакета `/opt/assistant-shared`, именования вспомогательных классов и модулей тестов при соблюдении контракта требований DAT-01..DAT-04 и SEC-01..SEC-03.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

- **DAT-01** [chat-app + assistant-core]: Схема БД и миграции принадлежат общей библиотеке (явный владелец схемы), а не создаются ad hoc в `assistant-core/src/storage/db.py`. Версия схемы хранится в БД; на пустой БД миграции строят схему полностью; существующая боевая БД распознаётся как базовая версия без изменения данных.
- **DAT-02** [chat-app + assistant-core]: Путь к БД берётся из настроек (env/конфиг) в обоих процессах; хардкод `SQLITE_DB_PATH` на `/opt/assistant-core/data/assistant.db` в `chat-app/backend/app/core/config.py` убран. Прод-значение задаётся окружением сервисов — правка окружения systemd является шагом разморозки владельца.
- **DAT-03** [chat-app + assistant-core]: Для общей БД включены WAL и `busy_timeout`; два процесса одновременно пишут в `tasks`, `reminders`, `projects`, `documents` без ошибок блокировки (тест конкурентной записи).
- **DAT-04** [chat-app]: Тесты chat-app создают временную пустую БД через общую схему, данные подготавливают фикстуры, ассерты не ослаблены; `pytest backend/tests` проходит без доступа к `/opt/assistant-core`.
- **SEC-01** [chat-app + assistant-core]: Одна общая библиотека проверок безопасности: `SECRET_PATTERNS` (включая Generic Bearer), `FORBIDDEN_FILES`, `run_cmd()`, NDA-правила из данных рабочего пространства; её импортируют Security Tile (chat-app) и assistant-core. Тест эквивалентности NDA из PER-04 перезапускается против библиотеки.
- **SEC-02** [chat-app + assistant-core]: `scripts/security_shield.py` в обоих репозиториях — тонкая CLI-обёртка над библиотекой; тест подтверждает отсутствие дрейфа (одинаковый результат Web-аудита и shield на общем наборе синтетических фикстур).
- **SEC-03** [chat-app + assistant-core]: pre-commit hook с проверкой установлен в обоих репозиториях воспроизводимо (hook и скрипт установки хранятся в репозитории) и блокирует коммит с синтетическим «секретом».
</phase_requirements>

---

## Summary

Фаза 4 переводит общую базу данных (`assistant.db`) и проверки безопасности из фрагментированного состояния под единое централизованное управление. До Фазы 4 схема БД неявно создавалась в `assistant-core/src/storage/db.py` через многостраничный скрипт `init_db()`, а `chat-app` не владел схемой, хардкодил путь в чужой репозиторий (`/opt/assistant-core/data/assistant.db`) и во время тестов обращался к `/opt/assistant-core` через подпроцессы. Аналогично, правила безопасности (`SECRET_PATTERNS`, `FORBIDDEN_FILES`, проверка NDA) дублировались между веб-эндпоинтами `backend/app/api/v1/security.py` и двумя независимыми копиями скрипта `scripts/security_shield.py`.

В Фазе 4 создаётся выделенный локальный Python-пакет `/opt/assistant-shared`, который:
1. **Становится единым владельцем схемы данных SQLite (DAT-01..DAT-04):**
   - Содержит легковесный SQL-раннер миграций (KISS) и каталог `migrations/` (`0001_initial_schema.sql`).
   - Ведёт историю версий в таблице `schema_migrations(version TEXT PRIMARY KEY, applied_at TIMESTAMP)`.
   - Идемпотентно распознаёт существующую базу данных как базовую версию `0001` без мутации существующих данных и структуры.
   - Предоставляет фабрику соединений для `aiosqlite` и `sqlite3`, гарантирующую включение `PRAGMA journal_mode = WAL;`, `PRAGMA busy_timeout = 5000;`, `PRAGMA foreign_keys = ON;`.
   - Устраняет хардкод `/opt/assistant-core/data/assistant.db` из `chat-app`: путь читается через переменные окружения (`SQLITE_DB_PATH` / `DATABASE_PATH`).
   - Изолирует тесты `chat-app`: фикстуры создают чистую временную SQLite БД через мигратор и наполняют её данными без вызова или наличия каталога `/opt/assistant-core`.
2. **Объединяет все механизмы безопасности (SEC-01..SEC-03):**
   - Выносит `SECRET_PATTERNS` (включая `Generic Bearer Secret`), `FORBIDDEN_FILES`, безопасный `run_cmd()` и проверки NDA-пространств в модуль `assistant_shared.security`.
   - Скрипты `scripts/security_shield.py` в обоих репозиториях сокращаются до тонких CLI-обёрток (менее 15 строк) над библиотекой.
   - В оба репозитория добавляются скрипт `scripts/install_hooks.sh` и воспроизводимый git-хук `.githooks/pre-commit`, блокирующий фиксацию коммитов с синтетическими секретами или запрещёнными файлами.

---

## Architectural Responsibility Map

| Компонент / Задача | Ответственный модуль | Способ взаимодействия | Контекст выполнения |
|---|---|---|---|
| DDL схемы и миграции SQLite | `/opt/assistant-shared/assistant_shared/db/migrator.py` + `migrations/*.sql` | Python API (`run_migrations(db_path)`) | Вызывается при старте сервисов, в тестах и при разморозке |
| Фабрика соединений с SQLite (WAL, timeout) | `/opt/assistant-shared/assistant_shared/db/connection.py` | `get_async_connection(path)`, `get_sync_connection(path)` | Используется `chat-app/backend/app/db.py` и `assistant-core/src/storage/db.py` |
| Хранилище бизнес-логики assistant-core | `/opt/assistant-core/src/storage/db.py` | Наследует / использует `assistant_shared.db`, сохраняет все свои CRUD-методы | Внутри процесса `assistant-worker` |
| Web API и CRUD-эндпоинты chat-app | `/opt/chat-app/backend/app/db.py` | Использует `assistant_shared.db.connection` | Внутри процесса `chat-app` (FastAPI / Uvicorn) |
| Паттерны секретов, запрещённых файлов, NDA | `/opt/assistant-shared/assistant_shared/security/patterns.py` + `rules.py` | Константы `SECRET_PATTERNS`, `FORBIDDEN_FILES`, функции `nda_rule_for` | Импортируется Web API и CLI-скриптами |
| Аудитор файловой системы и репозиториев | `/opt/assistant-shared/assistant_shared/security/auditor.py` | `audit_path()`, `audit_repository()` | Security Tile (`/api/v1/security/*`), CLI `security_shield.py`, pre-commit hook |
| CLI защиты коммитов в репозиториях | `scripts/security_shield.py` (в обоих репо) | Тонкая CLI-обёртка над `assistant_shared.security.audit_repository` | Локальный запуск разработчиком, шаг гейта `gate.py` |
| Pre-commit guardrail | `.githooks/pre-commit` + `scripts/install_hooks.sh` (в обоих репо) | Git Hook вызывает `security_shield.py` перед `git commit` | Git runtime перед созданием коммита |
| Изоляция тестов chat-app | `/opt/chat-app/backend/tests/conftest.py` | Сессионная фикстура поднимает временную БД через `assistant_shared` | `pytest backend/tests` без зависимостей от assistant-core |

---

## Standard Stack

Окружение обоих репозиториев проверено на хосте Ubuntu 24.04 LTS (Python 3.12.3):

| Пакет / Инструмент | Версия в chat-app `.venv` | Версия в assistant-core `.venv` | Назначение в Фазе 4 |
|---|---|---|---|
| **Python** | 3.12.3 | 3.12.3 | Базовый рантайм |
| **SQLite (C-lib)** | 3.45.1 | 3.45.1 | Поддержка WAL, busy_timeout, FTS5 |
| **aiosqlite** | 0.22.1 | 0.22.1 | Асинхронное подключение к SQLite |
| **pydantic** | 2.13.5 | 2.13.5 | Модели валидации данных |
| **pydantic-settings** | 2.15.0 | — | Чтение конфигурации `Settings` из env |
| **pytest** | 9.1.1 | 9.1.1 | Запуск наборов автотестов |
| **import-linter** | 2.15 | 2.15 | Архитектурный контроль слоёв импортов |
| **pip** | 26.2.1 | 26.2.1 | Установка пакета в режиме разработки (`-e`) |

### Способ установки пакета `/opt/assistant-shared`
Пакет `/opt/assistant-shared` создаётся со стандартным файлом конфигурации `pyproject.toml` (build-backend `setuptools.build_meta`).
Установка в оба окружения выполняется однократно локальной командой:
```bash
/opt/chat-app/backend/.venv/bin/pip install -e /opt/assistant-shared
/opt/assistant-core/.venv/bin/pip install -e /opt/assistant-shared
```
Пакет не требует внешних зависимостей, кроме уже установленных `aiosqlite` и `pydantic`. Режим `-e` (editable) позволяет вносить правки в `/opt/assistant-shared` с немедленным отражением в обоих окружениях без переустановки.

---

## Architecture Patterns

### 1. Структура каталогов `/opt/assistant-shared`

```
/opt/assistant-shared/
├── pyproject.toml
├── README.md
└── assistant_shared/
    ├── __init__.py
    ├── db/
    │   ├── __init__.py
    │   ├── connection.py        # Фабрика SQLite (aiosqlite и sqlite3) с WAL и busy_timeout
    │   ├── migrator.py          # KISS SQL runner версионированных миграций
    │   └── migrations/
    │       ├── __init__.py
    │       └── 0001_initial_schema.sql  # Базовая полная схема актуального состояния
    └── security/
        ├── __init__.py
        ├── patterns.py          # SECRET_PATTERNS (с Generic Bearer), FORBIDDEN_FILES, NDA-слова
        ├── rules.py             # NdaRemoteRule, nda_rule_for, normalize_remote
        ├── runner.py            # Безопасный run_cmd(), get_staged_or_tracked_files()
        └── auditor.py           # check_file_content(), audit_path(), audit_repository()
```

### 2. Спецификация файла `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "assistant-shared"
version = "0.1.0"
description = "Общая библиотека схемы базы данных и безопасности платформы ассистента"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "aiosqlite>=0.20.0",
    "pydantic>=2.0.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["assistant_shared*"]
```

### 3. Контракт раннера миграций (KISS SQL runner)

Таблица версий в SQLite:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Логика работы мигратора (`assistant_shared.db.migrator`):
1. **Инициализация:** подключается к файлу БД с обязательным `PRAGMA busy_timeout = 5000;`.
2. **Создание таблицы миграций:** `CREATE TABLE IF NOT EXISTS schema_migrations ...`.
3. **Обнаружение существующей БД (Baseline Detection):**
   - Проверяется, есть ли в таблице `schema_migrations` запись `'0001_initial_schema'`.
   - Если записи нет, проверяется наличие существующих прикладных таблиц в `sqlite_master` (например, `tasks`, `projects`, `content_snapshots`).
   - Если таблицы уже существуют (боевая БД до введения версионирования):
     мигратор выполняет `0001_initial_schema.sql` (все операторы которого оформлены как `CREATE TABLE IF NOT EXISTS` и `CREATE INDEX IF NOT EXISTS`), гарантируя создание отсутствующих таблиц (таких как `personas`, `workspaces`, `connector_bindings`) без изменения данных в существующих таблицах, после чего регистрирует версию `'0001_initial_schema'` в `schema_migrations`.
4. **Накат новых миграций:**
   - Читаются файлы из каталога `migrations/*.sql`, отсортированные по алфавиту/номеру.
   - Для каждого файла, чьё имя ещё не записано в `schema_migrations`, открывается транзакция: выполняется тело скрипта, записывается версия в `schema_migrations`, выполняется `COMMIT`.
5. **Публичный интерфейс:**
   - `run_migrations(db_path: str | Path, target_version: str | None = None) -> list[str]` — применяет недостающие миграции и возвращает список применённых версий.
   - `get_schema_version(db_path: str | Path) -> str | None` — возвращает последнюю применённую версию.
   - `list_applied_migrations(db_path: str | Path) -> list[str]` — возвращает полный список применённых версий.

### 4. Фабрика соединений SQLite с поддержкой WAL и busy_timeout

Для исключения ошибок `database is locked` при одновременной работе `chat-app` и `assistant-worker` все соединения создаются исключительно через фабрику:
- **Асинхронные соединения (`aiosqlite`):**
  ```python
  @asynccontextmanager
  async def get_async_connection(db_path: str | Path) -> AsyncGenerator[aiosqlite.Connection, None]:
      # Обеспечиваем наличие родительского каталога
      if str(db_path) != ":memory:" and not str(db_path).startswith("file:"):
          Path(db_path).parent.mkdir(parents=True, exist_ok=True)
      async with aiosqlite.connect(str(db_path), timeout=5.0) as conn:
          conn.row_factory = aiosqlite.Row
          await conn.execute("PRAGMA journal_mode = WAL;")
          await conn.execute("PRAGMA busy_timeout = 5000;")
          await conn.execute("PRAGMA foreign_keys = ON;")
          await conn.execute("PRAGMA synchronous = NORMAL;")
          yield conn
  ```
- **Синхронные соединения (`sqlite3`):**
  ```python
  @contextmanager
  def get_sync_connection(db_path: str | Path) -> Generator[sqlite3.Connection, None]:
      if str(db_path) != ":memory:" and not str(db_path).startswith("file:"):
          Path(db_path).parent.mkdir(parents=True, exist_ok=True)
      conn = sqlite3.connect(str(db_path), timeout=5.0)
      conn.row_factory = sqlite3.Row
      try:
          conn.execute("PRAGMA journal_mode = WAL;")
          conn.execute("PRAGMA busy_timeout = 5000;")
          conn.execute("PRAGMA foreign_keys = ON;")
          conn.execute("PRAGMA synchronous = NORMAL;")
          yield conn
      finally:
          conn.close()
  ```

---

## Don't Hand-Roll

1. **Не использовать Alembic / SQLAlchemy / Django ORM:**
   - *Причина:* Проект построен на чистом SQL и `aiosqlite`. Добавление тяжёлых ORM и движков миграций нарушает KISS/YAGNI, увеличивает потребление RAM на VPS (где лимит 2 ГБ), усложняет отладку и создаёт конфликт с асинхронным доступом. Легковесный SQL-раннер из ~80 строк на стандартном `sqlite3` решает задачу на 100%.
2. **Не писать собственные механизмы межпроцессных блокировок (flock, fcntl, redis, file locks):**
   - *Причина:* SQLite в режиме `WAL` со встроенным `PRAGMA busy_timeout=5000` аппаратно и на уровне ядра ОС реализует безопасный параллельный доступ (читатели не блокируют писателей, писатели ожидают до 5 секунд в очереди). Любые самодельные файловые блокировки приводят к дедлокам при аварийном завершении процессов (SIGKILL).
3. **Не дублировать регулярные выражения секретов в разных файлах:**
   - *Причина:* Ранее `Generic Bearer Secret` присутствовал в `security_shield.py`, но отсутствовал в `security.py`. Все `SECRET_PATTERNS` и `FORBIDDEN_FILES` должны объявляться ровно в одном месте: `assistant_shared.security.patterns`.
4. **Не хардкодить пути к репозиториям и базам данных:**
   - *Причина:* Путь к БД читается исключительно через переменные окружения (`SQLITE_DB_PATH` / `DATABASE_PATH`). Хардкод `/opt/assistant-core/data/assistant.db` полностью удаляется.

---

## Runtime State Inventory

| Ресурс / Файл | Состояние до Фазы 4 | Состояние после Фазы 4 | Влияние на Freeze / Rollback |
|---|---|---|---|
| `/opt/assistant-shared/` | Отсутствует | Локальный Python-пакет, установленный через `pip install -e` | При откате удаляется каталог и выполняется `pip uninstall assistant-shared` |
| `/opt/assistant-core/data/assistant.db` | Заморожена, таблиц `schema_migrations`, `personas`, `workspaces` нет | **НЕ ТРОГАЕТСЯ во время тестов и разработки.** Распознаётся мигратором как `0001` только при явной разморозке владельцем | Защищена контролем SHA-256 в `gate.py` |
| Временные файлы WAL (`*.db-wal`, `*.db-shm`) | Создавались спорадически | Автоматически управляются SQLite при WAL-режиме | Создаются рядом с файлом БД в рантайме |
| Сервисы systemd (`chat-app`, `assistant-worker`, `dev-bridge`) | Остановлены, `disabled` | **Остаются остановленными и `disabled`** | Автоматический перезапуск сервисов запрещён |
| Git-хуки (`.git/hooks/pre-commit`) | Отсутствовали (только `.sample`) | Настроены через `scripts/install_hooks.sh` на запуск `security_shield.py` | Воспроизводимы, хранятся в репозитории |

---

## Common Pitfalls

### Pitfall 1: Ошибки блокировки SQLite (`database is locked`) в многопроцессной среде
- **Симптом:** При одновременной записи процессами `chat-app` и `assistant-worker` один из них падает с `sqlite3.OperationalError: database is locked`.
- **Причина:** Режим журнала по умолчанию (`delete` или `rollback`) блокирует всю базу целиком даже для чтения. Более того, параметр `busy_timeout` по умолчанию равен 0 мс (немедленная ошибка при малейшей конкуренции).
- **Решение:**
  1. `PRAGMA journal_mode = WAL;` (включается один раз для БД, сохраняется в заголовке файла).
  2. `PRAGMA busy_timeout = 5000;` (является локальной настройкой соединения, поэтому ОБЯЗАН применяться при каждом вызове `connect()`).
  3. Директория, содержащая файл БД, должна иметь права на запись для обоих процессов, так как SQLite создаёт вспомогательные файлы `-wal` и `-shm`.

### Pitfall 2: Циклические импорты и нарушение контрактов архитектурного линтера
- **Симптом:** Падение `lint-imports` или тестов `test_core_architecture.py` / `test_architecture_contract.py`.
- **Причина:**
  - В `assistant-core` контракт `core-is-pure` строго запрещает `src.core` импортировать любые внешние пакеты или другие модули `src.*`. Если кто-то импортирует `assistant_shared` внутри `src.core.*`, линтер или `_RUNTIME_PROBE` немедленно уронит билд.
  - В `chat-app` контракт `app-no-assistant-core` запрещает `app` импортировать модули `src.*`.
- **Решение:**
  - `src.core` в `assistant-core` остаётся абсолютно чистым (только Python stdlib и `src.core`).
  - `assistant_shared` импортируется исключительно в `src.storage.db`, `src.composition`, `chat-app/backend/app/db.py`, `chat-app/backend/app/api/v1/security.py` и CLI-скриптах.
  - Поскольку имя пакета `assistant_shared` не является `src`, контракт `app-no-assistant-core` не нарушается.

### Pitfall 3: Дрейф ложных срабатываний в `gate.py` (`KNOWN_SHIELD_FALSE_POSITIVES`)
- **Симптом:** После выноса ключевых слов из `scripts/security_shield.py` в библиотеку `scripts/gate.py` падает с ошибкой: `устаревшая запись (удалите из KNOWN_SHIELD_FALSE_POSITIVES): scripts/security_shield.py [nda-keyword]`.
- **Причина:** В `gate.py` зашит строгий контроль устаревания записей белого списка. Если скрипт `security_shield.py` стал тонкой обёрткой и больше не содержит литералов ключевых слов NDA и др., старая запись признаётся устаревшей и краснит гейт.
- **Решение:** При рефакторинге `security_shield.py` синхронно актуализировать словарь `KNOWN_SHIELD_FALSE_POSITIVES` в `scripts/gate.py` (удалить устаревшие записи для `scripts/security_shield.py` и решить исключение для `config/persona.yaml` через распознавание файлов конфигурации).

### Pitfall 4: Неисполняемые права Git Hook (`chmod +x`)
- **Симптом:** Pre-commit hook установлен, но коммиты с синтетическими секретами не блокируются.
- **Причина:** Git молча игнорирует скрипты в `.git/hooks/`, если у них отсутствует флаг исполняемости (`+x`).
- **Решение:** Скрипт `scripts/install_hooks.sh` обязан явно выполнять `chmod +x` для установленного хука, а тестовый набор — проверять реальное блокирование через запуск `git commit` в изолированном временном репозитории.

### Pitfall 5: Зависание соединений в асинхронных тестах
- **Симптом:** Тест пытается удалить временную БД (`tmp_path`), но получает ошибку доступа, или следующий тест зависает.
- **Причина:** `aiosqlite.Connection` не был закрыт (`await conn.close()`), пул соединений удерживает файловый дескриптор.
- **Решение:** Всегда использовать конструкцию `async with get_db() as conn:` или регистрировать `yield` в генераторах pytest с обязательным закрытием в блоке `finally`.

---

## Code Examples

### 1. Легковесный раннер миграций (`assistant_shared/db/migrator.py`)

```python
"""Легковесный SQL-раннер версионированных миграций (KISS)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def get_schema_version(db_path: str | Path) -> str | None:
    """Возвращает последнюю применённую версию схемы или None."""
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';"
        )
        if not cursor.fetchone():
            return None
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;")
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _is_pre_migration_baseline(conn: sqlite3.Connection) -> bool:
    """Проверяет, содержит ли БД прикладные таблицы до введения schema_migrations."""
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('tasks', 'projects', 'reminders');"
    )
    count = cursor.fetchone()[0]
    return count > 0


def run_migrations(db_path: str | Path, migrations_dir: Path | None = None) -> list[str]:
    """Применяет миграции из каталога и возвращает список применённых версий."""
    migrations_dir = migrations_dir or MIGRATIONS_DIR
    target_path = Path(db_path)
    if str(target_path) != ":memory:" and not str(target_path).startswith("file:"):
        target_path.parent.mkdir(parents=True, exist_ok=True)

    applied_now: list[str] = []
    conn = sqlite3.connect(str(target_path), timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")

        # 1. Создание таблицы версий
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()

        # 2. Получение уже применённых версий
        cursor = conn.execute("SELECT version FROM schema_migrations;")
        applied = {row[0] for row in cursor.fetchall()}

        # 3. Список доступных файлов миграций
        migration_files = sorted(migrations_dir.glob("*.sql"))

        # 4. Проверка базового состояния (D-05)
        is_baseline = _is_pre_migration_baseline(conn)

        for file_path in migration_files:
            version_name = file_path.stem
            if version_name in applied:
                continue

            # Применение миграции
            sql_script = file_path.read_text(encoding="utf-8")
            logger.info("Applying migration: %s to %s", version_name, db_path)
            conn.executescript(sql_script)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, CURRENT_TIMESTAMP);",
                (version_name,),
            )
            conn.commit()
            applied_now.append(version_name)

        return applied_now
    finally:
        conn.close()
```

### 2. Фабрика подключений (`assistant_shared/db/connection.py`)

```python
"""Фабрика SQLite соединений с обязательным WAL-режимом и busy_timeout."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import AsyncGenerator, Generator

import aiosqlite


def _ensure_parent_dir(db_path: str | Path) -> None:
    path_str = str(db_path)
    if path_str != ":memory:" and not path_str.startswith("file:"):
        Path(path_str).parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def get_async_connection(db_path: str | Path) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Асинхронный контекстный менеджер соединения aiosqlite (WAL + busy_timeout=5000)."""
    _ensure_parent_dir(db_path)
    async with aiosqlite.connect(str(db_path), timeout=5.0) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode = WAL;")
        await conn.execute("PRAGMA busy_timeout = 5000;")
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute("PRAGMA synchronous = NORMAL;")
        yield conn


@contextmanager
def get_sync_connection(db_path: str | Path) -> Generator[sqlite3.Connection, None]:
    """Синхронный контекстный менеджер соединения sqlite3 (WAL + busy_timeout=5000)."""
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        yield conn
    finally:
        conn.close()
```

### 3. Pytest-фикстура изолированной БД (`chat-app/backend/tests/conftest.py`)

```python
"""Изолированные тестовые фикстуры chat-app (DAT-04).

Тесты работают на чистой временной БД, создаваемой мигратором assistant_shared.
Каталог /opt/assistant-core во время тестов недоступен и не используется.
"""

import json
import os
import sqlite3
from pathlib import Path

import pytest
from app.core.config import settings
from assistant_shared.db.migrator import run_migrations

from .synthetic_persona import SYNTHETIC_PERSONA, synthetic_to_config

DEFAULT_PERSONA_FIXTURE = {
    "id": "popov-da-default",
    "display_name": "Дмитрий Александрович Попов",
    "short_name": "Попов Д.А.",
    "title": "доцент кафедры физики №1, научный сотрудник",
    "default_area": "ГУАП",
    "organizations": {
        "university": "ГУАП (Кафедра физики №1)",
        "company": "ООО «Тидекс» (Сектор приборов)",
    },
    "workspaces": [
        {
            "id": "chat-app",
            "position": 0,
            "label": "🤖 Antigravity Web Studio (chat-app)",
            "path": "/opt/chat-app",
            "clearance": "public",
            "account": "DimaMuhannad (Personal / Academic)",
            "clearance_label": "🌐 Public / Open Source",
            "color": "blue",
            "remote": "https://github.com/DimaMuhannad/chat-app.git",
            "forbidden_remote_substrings": [],
            "forbidden_keywords": [],
        },
        {
            "id": "assistant-core",
            "position": 1,
            "label": "⚙️ Assistant Core Daemon",
            "path": "/opt/assistant-core",
            "clearance": "public",
            "account": "DimaMuhannad (Personal / Academic)",
            "clearance_label": "🌐 Public / Academic",
            "color": "green",
            "remote": "https://github.com/DimaMuhannad/assistant-core.git",
            "forbidden_remote_substrings": [],
            "forbidden_keywords": [],
        },
        {
            "id": "tydex-optics",
            "position": 2,
            "label": "🔬 Оптические приборы и измерения (ООО «Тидекс»)",
            "path": "/opt/work-tydex",
            "clearance": "restricted_nda",
            "account": "ООО «Тидекс» (Corporate Organization)",
            "clearance_label": "🔴 Restricted NDA / Air-gap",
            "color": "red",
            "remote": "git@github.com:tydex-optics/device-firmware.git",
            "forbidden_remote_substrings": ["github.com/dimamuhannad"],
            "forbidden_keywords": ["proprietary_secret_alpha", "synthetic_calibration_key", "internal_firmware_flag"],
            "remote_violation_message": "CRITICAL: Tydex private project remote points to personal public account (DimaMuhannad)!",
        },
        {
            "id": "guap-physics",
            "position": 3,
            "label": "🏛️ Кафедра физики ГУАП (Лабораторные и LMS)",
            "path": "/opt/personal/guap-physics",
            "clearance": "internal",
            "account": "DimaMuhannad (ГУАП)",
            "clearance_label": "🟡 Internal Academic",
            "color": "yellow",
            "remote": "https://github.com/DimaMuhannad/guap-physics.git",
            "forbidden_remote_substrings": [],
            "forbidden_keywords": [],
        },
    ],
}


def _seed_test_data(db_path: Path) -> None:
    """Засевает тестовые проекты, задачи и персону без вызова внешних процессов."""
    conn = sqlite3.connect(db_path)
    try:
        # Персона по умолчанию
        p = DEFAULT_PERSONA_FIXTURE
        conn.execute(
            "INSERT INTO personas (id, display_name, config_json, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);",
            (p["id"], p["display_name"], json.dumps(p, ensure_ascii=False)),
        )
        for ws in p["workspaces"]:
            conn.execute(
                """
                INSERT INTO workspaces (
                    persona_id, id, position, label, path, clearance, account,
                    clearance_label, color, remote, forbidden_remote_substrings,
                    forbidden_keywords, remote_violation_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["id"], ws["id"], ws["position"], ws["label"], ws["path"],
                    ws["clearance"], ws["account"], ws["clearance_label"], ws["color"],
                    ws["remote"], json.dumps(ws.get("forbidden_remote_substrings", [])),
                    json.dumps(ws.get("forbidden_keywords", [])),
                    ws.get("remote_violation_message"),
                ),
            )

        # Тестовый проект, фокус-задача и напоминание для test_dashboard_api
        conn.execute(
            "INSERT INTO projects (id, name, area, status, description) VALUES (1, 'Тестовый семестр', 'ГУАП', 'active', 'Описание');"
        )
        conn.execute(
            "INSERT INTO tasks (id, project_id, title, area, priority, status) VALUES (1, 1, 'Фокус задача', 'ГУАП', 'P1', 'todo');"
        )
        conn.execute(
            "INSERT INTO reminders (id, task_id, what, person, check_date, status) VALUES (1, 1, 'Проверить отчет', 'Староста', '2026-10-05', 'active');"
        )
        conn.execute(
            "INSERT INTO documents (id, project_id, title, content_markdown) VALUES (1, 1, 'План работ', '# План');"
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def persona_session_db(tmp_path_factory):
    """Создаёт временную чистую SQLite БД и накатывает схему через migrator."""
    db_file = tmp_path_factory.mktemp("isolated-db") / "test_isolated.db"
    run_migrations(db_file)
    _seed_test_data(db_file)

    previous = settings.SQLITE_DB_PATH
    settings.SQLITE_DB_PATH = str(db_file)
    try:
        yield db_file
    finally:
        settings.SQLITE_DB_PATH = previous
```

### 4. Тонкая обёртка `scripts/security_shield.py`
```python
#!/usr/bin/env python3
"""Security Shield CLI Wrapper (SEC-02)."""

import sys
from pathlib import Path
from assistant_shared.security import audit_repository

if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    staged_only = "--all" not in sys.argv
    sys.exit(audit_repository(target, check_staged_only=staged_only))
```

### 5. Скрипт установки хуков `scripts/install_hooks.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="${REPO_DIR}/.githooks"
GIT_DIR="${REPO_DIR}/.git"

if [ ! -d "${GIT_DIR}" ]; then
    echo "Ошибка: ${REPO_DIR} не является Git-репозиторием" >&2
    exit 1
fi

mkdir -p "${HOOKS_DIR}"

cat << 'EOF' > "${HOOKS_DIR}/pre-commit"
#!/usr/bin/env bash
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
PYTHON_BIN="${REPO_ROOT}/backend/.venv/bin/python"

if [ ! -x "${PYTHON_BIN}" ]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
fi

if [ ! -x "${PYTHON_BIN}" ]; then
    PYTHON_BIN="python3"
fi

echo "🛡️ [Pre-Commit Hook] Запуск Security Shield проверки индексированных файлов..."
exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/security_shield.py" "${REPO_ROOT}"
EOF

chmod +x "${HOOKS_DIR}/pre-commit"
git -C "${REPO_DIR}" config core.hooksPath .githooks

echo "✅ Pre-commit hook успешно установлен в ${REPO_DIR} (core.hooksPath = .githooks)"
```

### 6. Интеграционный тест конкурентной записи (DAT-03)
```python
"""Интеграционный тест параллельной конкурентной записи в SQLite (DAT-03)."""

import multiprocessing as mp
import time
from pathlib import Path
from assistant_shared.db.connection import get_sync_connection
from assistant_shared.db.migrator import run_migrations


def _worker_writer(db_path: Path, worker_id: int, iterations: int) -> int:
    written = 0
    with get_sync_connection(db_path) as conn:
        for i in range(iterations):
            try:
                conn.execute(
                    "INSERT INTO tasks (title, area, priority, status) VALUES (?, ?, 'P2', 'todo');",
                    (f"Task from worker {worker_id} - iter {i}", "ГУАП"),
                )
                conn.commit()
                written += 1
                time.sleep(0.001)  # Имитация микро-задержки для провокации гонки
            except Exception as e:
                # В случае database is locked будет исключение
                raise e
    return written


def test_concurrent_writes_two_processes(tmp_path):
    db_file = tmp_path / "concurrent_test.db"
    run_migrations(db_file)

    iterations_per_worker = 100
    with mp.Pool(processes=2) as pool:
        results = [
            pool.apply_async(_worker_writer, (db_file, 1, iterations_per_worker)),
            pool.apply_async(_worker_writer, (db_file, 2, iterations_per_worker)),
        ]
        counts = [r.get(timeout=30) for r in results]

    assert counts == [iterations_per_worker, iterations_per_worker]
    with get_sync_connection(db_file) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM tasks;")
        total = cursor.fetchone()[0]
    assert total == iterations_per_worker * 2
```

---

## Validation Architecture

1. **Единый локальный гейт качества:**
   ```bash
   python3 /opt/chat-app/scripts/gate.py
   ```
   Должен давать `ИТОГ: ЗЕЛЁНЫЙ`, проверяя:
   - `chat-app` pytest (128+ тестов)
   - `chat-app` import-linter
   - `assistant-core` pytest (330+ тестов)
   - `assistant-core` import-linter
   - `security_shield (--all)` в обоих репозиториях
   - Дрейф синтетической персоны и токенов персоны
   - Неизменность хеша боевой `assistant.db`

2. **Проверка изоляции тестов chat-app (DAT-04):**
   ```bash
   ASSISTANT_CORE_DIR="/nonexistent/directory" /opt/chat-app/backend/.venv/bin/pytest /opt/chat-app/backend/tests
   ```
   Все 128+ тестов должны успешно проходить без обращения к каталогу `/opt/assistant-core`.

3. **Проверка пре-коммит хука (SEC-03):**
   Интеграционный тест разворачивает тестовый репозиторий в `tmp_path`, запускает `install_hooks.sh`, индексирует файл с синтетическим токеном `AIzaSy...` и выполняет `git commit`. Команда обязана завершиться с ненулевым кодом и сообщением о блокировке.

4. **Проверка конкурентной записи (DAT-03):**
   Запуск `pytest` интеграционного теста с 2 параллельными процессами `multiprocessing`, выполняющими по 100 одновременных транзакций записи без ошибок `database is locked`.

---

## Security Domain

### STRIDE Threat Model

| Угроза (STRIDE) | Источник / Риск | Защитный механизм Фазы 4 |
|---|---|---|
| **Spoofing (Спуфинг)** | Коммит под неавторизованным e-mail или чужим профилем | Pre-commit hook проверяет соответствие `user.email` и remote origin политике пространства |
| **Tampering (Подмена / Порча данных)** | Повреждение БД при резкой остановке (`SIGKILL`) или гонке процессов | Режим WAL гарантирует атомарность транзакций; `busy_timeout=5000` предотвращает сбои при параллельной записи |
| **Repudiation (Отказ от авторства)** | Неконтролируемое изменение схемы БД ad hoc вызовами | Версионированные SQL-миграции в таблице `schema_migrations` фиксируют точную историю и временные метки изменений схемы |
| **Information Disclosure (Утечка секретов)** | Случайный коммит приватных ключей, Generic Bearer токенов, закрытых NDA-файлов | `assistant_shared.security` объединяет сканирование `SECRET_PATTERNS`, `FORBIDDEN_FILES` и ключевых слов в Pre-commit hook и Security Tile |
| **Denial of Service (Отказ в обслуживании)** | Зависание демона или Web API из-за блокировки SQLite (`database is locked`) | Режим WAL разделяет читателей и писателей; таймаут 5000 мс организует очередь ожидания блокировки |
| **Elevation of Privilege (Повышение привилегий)** | Отправка NDA-файлов или corporate origin в публичные репозитории | Air-gap валидация уровня допуска (`clearance: restricted_nda`) блокирует недопустимые origin URL |

### ASVS / Best Practices Alignment
- **V1 Architecture & Design:** Чёткое разграничение ответственности — единый разделяемый пакет `/opt/assistant-shared` исключает размывание контрактов и дублирование логики безопасности.
- **V8 Data Protection:** Запрет фиксации в VCS любых секретных файлов (`.env`, `credentials.json`, `token.json`, `*.session`, приватные ключи).
- **V10 Malicious Code Prevention:** Pre-commit hook блокирует случайный коммит вредоносных или конфиденциальных артефактов до их попадания в историю git.
- **Fail-Closed Principle:** Если у рабочего пространства с уровнем `restricted_nda` отсутствуют правила проверки remote или файл не удаётся прочитать, аудит немедленно возвращает статус нарушения (`violations`), а не признаёт пространство чистым.
