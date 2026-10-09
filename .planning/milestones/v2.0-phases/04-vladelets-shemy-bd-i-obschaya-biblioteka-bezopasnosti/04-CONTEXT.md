# Phase 4: Владелец схемы БД и общая библиотека безопасности - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning

<domain>
## Phase Boundary

У общей базы данных SQLite (`assistant.db`) появляется единый явный владелец схемы и версионированные миграции (DAT-01..DAT-04). Обеспечивается безопасная параллельная запись двух процессов (chat-app и assistant-core) при включённом WAL-режиме и настройке `busy_timeout` (DAT-03). Тесты chat-app изолируются: `pytest backend/tests` проходит на чистой временной БД без обращения к `/opt/assistant-core` (DAT-04).
Проверки безопасности выносятся в единую общую библиотеку (SEC-01..SEC-03): паттерны секретов `SECRET_PATTERNS` (включая Generic Bearer), `FORBIDDEN_FILES`, безопасный `run_cmd()`, правила проверки NDA-пространств. Скрипты `scripts/security_shield.py` в обоих репозиториях становятся тонкими обёртками над библиотекой (SEC-02). В оба репозитория воспроизводимо устанавливается pre-commit hook (SEC-03), блокирующий коммиты с синтетическими секретами.

Не входит в фазу: единый HITL-примитив подтверждения (Фаза 5, HIT-01..HIT-04), мультитенантность, очистка глобального `GEMINI_API_KEY` и `WorkspaceScope` (Фаза 6), Git-источники и дашборды Notion (Фаза 7).

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Требования и границы
- `.planning/REQUIREMENTS.md` — требования DAT-01..DAT-04, SEC-01..SEC-03, критерии приёмки
- `.planning/ROADMAP.md` §«Phase 4: Владелец схемы БД и общая библиотека безопасности» — цели, критерии успеха и заметки планирования
- `.planning/PROJECT.md` §Key Decisions — W5 (единая БД, владелец схемы, WAL), W9 (единая библиотека безопасности + hook)
- `.planning/intel/user-resolutions.md` — W5, W9

### Архитектура и предыдущие фазы
- `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` §3.2 (SQLite-схема), §4 (безопасность и NDA)
- `.planning/phases/01-strahovochnaya-set-i-karkas/01-CONTEXT.md` — D-03 (защита базы данных гейтом)
- `.planning/phases/03-persona-kak-dannye/03-CONTEXT.md` — D-02 (схема таблиц персон), D-15 (чек-лист NDA)
- `docs/BASELINE.md` — baseline тестов и фиксация шагов разморозки
- `scripts/gate.py` — проверка качества и контроль хеша базы данных

### Кодовая база
- `backend/app/api/v1/security.py` — текущая логика безопасности chat-app
- `backend/app/core/config.py`, `backend/app/db.py` — настройки пути к SQLite и подключение к БД
- `/opt/assistant-core/src/storage/db.py` — текущая DDL-схема и инициализация БД
- `/opt/assistant-core/scripts/security_shield.py`, `/opt/chat-app/scripts/security_shield.py` — скрипты защиты репозиториев
- `backend/tests/test_security_api.py`, `test_synthetic_persona.py` — тесты безопасности и персон

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/gate.py` — запуск тестов с контролем хеша базы данных на копии
- `scripts/security_shield.py` — сканер утечек секретов и запрещённых путей
- `/opt/assistant-core/src/storage/db.py` — готовые DDL-запросы существующих таблиц

### Established Patterns
- Pydantic v2 и SQLite (aiosqlite) в качестве базового стека данных
- Запуск тестов через фикстуры с временными файлами БД
- Тонкие CLI-обёртки для скриптов сопровождения

### Integration Points
- `/opt/assistant-shared` — новый единый разделяемый пакет
- `chat-app/backend/app/core/config.py` — чтение `SQLITE_DB_PATH`
- `chat-app/backend/app/api/v1/security.py` — импорт `assistant_shared.security`
- `chat-app/scripts/install_hooks.sh` и `assistant-core/scripts/install_hooks.sh` — установка pre-commit hook

</code_context>

<specifics>
## Specific Ideas

Реализация по принципу KISS: отказ от громоздких ORM/миграторов в пользу чистого версионированного SQL-мигратора и отдельного пакета `/opt/assistant-shared`.

</specifics>

<deferred>
## Deferred Ideas

None — все обсужденные вопросы соответствуют границам Фазы 4.

</deferred>

---

*Phase: 04-vladelets-shemy-bd-i-obschaya-biblioteka-bezopasnosti*
*Context gathered: 2026-10-03*
