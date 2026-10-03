---
phase: 4
reviewers: [antigravity]
reviewed_at: 2026-10-03T20:35:07Z
plans_reviewed: [04-01-PLAN.md, 04-02-PLAN.md, 04-03-PLAN.md, 04-04-PLAN.md]
models:
  antigravity: "unknown"
model_sources:
  antigravity: "unknown"
---

# Cross-AI Plan Review — Phase 4

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## Antigravity Review

Проверяю структуру конфигурации персоны в фоновом режиме. Все последующие выводы и анализ планов формируются строго на русском языке согласно правилам проекта.
# Обзор планов реализации Фазы 4: Владелец схемы БД и общая библиотека безопасности

Проведена проверка планов реализации Фазы 4 (`04-01-PLAN.md` — `04-04-PLAN.md`) с верификацией по исходному коду репозиториев `/opt/chat-app` и `/opt/assistant-core`.

---

## 04-01

### 1. Summary
План `04-01` закладывает фундаментальную основу Фазы 4: создаёт отдельный локальный Python-пакет `/opt/assistant-shared`, реализует легковесный SQL-раннер версионированных миграций (`assistant_shared.db.migrator`), консолидирует полную схему таблиц платформы в `0001_initial_schema.sql` и устраняет ad-hoc создание таблиц в `assistant-core/src/storage/db.py:init_db()`. Архитектурное решение строго следует принципам KISS/YAGNI (отказ от тяжеловесных ORM вроде Alembic). Тем не менее, план содержит две критические ошибки исполнения: использование команды `pip install --no-build-isolation -e` при отсутствии `setuptools` в виртуальных окружениях, а также разрушение работы с базой `:memory:`, используемой в более чем 20 тестовых модулях `assistant-core`.

### 2. Strengths
• **Консолидация схемы без лишних абстракций (KISS):** DDL всех таблиц платформы переносится из разрозненного скрипта `assistant-core/src/storage/db.py:48-445` в единый файл `0001_initial_schema.sql` с отслеживанием применённых версий в служебной таблице `schema_migrations(version, applied_at)`.
• **Безопасное распознавание существующей БД (Baseline Detection):** Логика `_is_pre_migration_baseline` проверяет наличие прикладных таблиц (`tasks`, `projects`) в `sqlite_master`. Для существующей боевой базы операторы `CREATE TABLE IF NOT EXISTS` выполняются идемпотентно, досоздавая отсутствующие таблицы (`personas`, `workspaces`, `connector_bindings`), после чего фиксируется версия `0001_initial_schema` без мутации существующих данных (соответствует требованиям DAT-01 и D-05).
• **Соблюдение архитектурных контрактов чистоты ядра:** Пакет `assistant_shared` импортируется исключительно в слое хранения (`src.storage.db`), не затрагивая `src.core`, что гарантирует прохождение теста `assistant-core/tests/test_core_architecture.py:39-48` и контракта `core-is-pure` в `assistant-core/.importlinter:58-79`.

### 3. Concerns
• **HIGH:** Разрушение работы тестов `assistant-core` с базами `:memory:`.
  - *Локация:* `assistant-core/src/storage/db.py:28-33` и более 20 файлов в `assistant-core/tests/` (например, `test_persona_storage.py:41-44`, `test_secretary_dialog.py:17`, `test_phase1.py:161`).
  - *Механизм:* В тестах хранилище инициализируется как `Database(":memory:")` с вызовом `await db.init_db()`. Задача `04-01-02` заменяет тело `init_db()` на вызов `run_migrations(self.db_path)`. В модуле `migrator.py` раннер миграций открывает собственное соединение `conn = sqlite3.connect(str(target_path))` и закрывает его в блоке `finally`. В SQLite каждое подключение к `:memory:` создаёт независимую временную БД в оперативной памяти, которая бесследно уничтожается при закрытии дескриптора. В результате `run_migrations(":memory:")` накатывает схему во временную БД и закрывает её, а разделяемое соединение `Database._shared_conn` остаётся абсолютно пустым. Все тесты с фикстурой `db = Database(":memory:")` немедленно упадут с ошибкой `sqlite3.OperationalError: no such table: ...`.
• **HIGH:** Сбой установки пакета через `pip install --no-build-isolation -e`.
  - *Локация:* Текст задачи `04-01-01` (строки 1030, 1121) и конфигурация окружений `/opt/chat-app/backend/.venv`, `/opt/assistant-core/.venv`.
  - *Механизм:* Флаг `--no-build-isolation` приказывает `pip` использовать сборочный бэкенд, установленный в текущем `.venv`. Однако в обоих виртуальных окружениях пакет `setuptools` отсутствует (в выводе `pip list` присутствуют только чистый `pip` и прикладные библиотеки, вызов `python -c "import setuptools"` завершается с `ModuleNotFoundError`). Запуск команды `pip install --no-build-isolation -e /opt/assistant-shared` немедленно завершится фатальной ошибкой сборки.
• **MEDIUM:** Потеря ad-hoc миграций столбцов при отказе от старого кода `init_db()`.
  - *Локация:* `assistant-core/src/storage/db.py:449-521`.
  - *Механизм:* В старом `init_db()` содержались блоки `ALTER TABLE email_messages ADD COLUMN ...`, `ALTER TABLE email_drafts ADD COLUMN ...`, `ALTER TABLE email_threads ADD COLUMN ...`, `ALTER TABLE bot_dialog_history ADD COLUMN is_archived ...`, а также пересоздание таблицы `calendar_sync_records`. Если базовая миграция `0001_initial_schema.sql` оформлена как `CREATE TABLE IF NOT EXISTS`, то при накате на существующую стороннюю БД с неполным набором колонок оператор `CREATE TABLE IF NOT EXISTS` не добавит недостающие столбцы. Хотя боевая БД `/opt/assistant-core/data/assistant.db` уже содержит эти столбцы, план обязан явно зафиксировать, что миграция `0001` определяет каноническую схему, а ad-hoc миграции удаляются.

### 4. Suggestions
• Расширить сигнатуру `run_migrations(db_path_or_conn: str | Path | sqlite3.Connection | aiosqlite.Connection)`: если передан объект соединения (или если `Database` работает в режиме `:memory:`), мигратор должен выполнять DDL-скрипт непосредственно в контексте существующего соединения `Database._shared_conn`, не открывая и не закрывая отдельный дескриптор `:memory:`.
• Для установки пакета `/opt/assistant-shared` либо предварительно установить `setuptools` в оба `.venv`, либо устанавливать пакет без флага `--no-build-isolation`, либо применить надёжный подход без внешних сборочных инструментов: прописать файл `assistant_shared.pth` со строкой `/opt/assistant-shared` напрямую в каталоги `site-packages` обоих `.venv`.

### 5. Risk Assessment
**HIGH.** Без исправления механизма миграции для соединений `:memory:` и устранения проблемы с `setuptools` выполнение плана заблокируется на первой же задаче, а принудительный запуск вызовет регрессию десятков существующих тестов `assistant-core`.

---

## 04-02

### 1. Summary
План `04-02` решает задачи DAT-02, DAT-03 и DAT-04: создаёт централизованную фабрику соединений SQLite (`assistant_shared.db.connection`) с принудительной активацией WAL-режима и таймаута ожидания блокировки (`busy_timeout=5000`), переводит на неё `chat-app/backend/app/db.py` и `assistant-core/src/storage/db.py`, удаляет строковый хардкод `/opt/assistant-core/data/assistant.db` из настроек `chat-app` и полностью изолирует тестовый набор `chat-app` от внешнего репозитория `assistant-core`. План хорошо структурирован, однако предложенная в исследовании структура фикстуры персоны для `conftest.py` грубо нарушает контракт данных и сломает зависимые тесты.

### 2. Strengths
• **Аппаратное предотвращение блокировок SQLite (DAT-03):** Фабрика `get_async_connection` и `get_sync_connection` гарантирует выполнение `PRAGMA journal_mode = WAL;`, `PRAGMA busy_timeout = 5000;`, `PRAGMA foreign_keys = ON;` и `PRAGMA synchronous = NORMAL;` при каждом подключении, устраняя сбои `database is locked` при одновременной записи нескольких процессов.
• **Устранение жесткой связности путей (DAT-02):** Полностью убирается строковый хардкод пути `/opt/assistant-core/data/assistant.db` из `chat-app/backend/app/core/config.py:19`. Путь конфигурируется через переменные окружения `SQLITE_DB_PATH` / `DATABASE_PATH`.
• **Автономия тестов chat-app (DAT-04):** В `chat-app/backend/tests/conftest.py` ликвидируется небезопасный подпроцесс `subprocess.run` к `/opt/assistant-core/.venv/bin/python -m src.persona.seed` (строки 55-69), а тесты переводятся на чистую временную SQLite БД, создаваемую мигратором из `assistant-shared`.

### 3. Concerns
• **HIGH:** Невалидная структура словаря `DEFAULT_PERSONA_FIXTURE` в фикстуре `conftest.py`.
  - *Локация:* `chat-app/backend/tests/conftest.py:79-95`, `chat-app/backend/tests/persona_tokens.py:53-56`, `chat-app/backend/tests/test_synthetic_persona.py:96-122`.
  - *Механизм:* В исследовательском коде (`04-RESEARCH.md:385-450`), на который опирается план, структура `DEFAULT_PERSONA_FIXTURE` содержит плоские строки для организаций (`"university": "ГУАП (Кафедра физики №1)"`), а также полностью лишена ключей `connectors` и `telegram`. В то же время:
    1. `persona_tokens.py:53-54` выполняет: `for organization in (config.get("organizations") or {}).values(): tokens["organization"].add(str(organization.get("name", "")).strip())`. На строковом значении вызов `.get("name")` вызовет `AttributeError: 'str' object has no attribute 'get'`.
    2. `test_synthetic_persona.py:98-111` ожидает `default["connectors"]["schedule_source"][0]["config"]`, `default["connectors"]["timesheet"]` и `default["organizations"]["university"]["name"]`.
    При заполнении БД предложенным урезанным фикстурным словарем тесты `test_hardcode_scanner.py`, `test_index_whitelabel.py` и `test_synthetic_persona.py` немедленно завершатся аварийно.
• **MEDIUM:** Неполный охват таблиц в интеграционном тесте конкурентной записи.
  - *Локация:* Задача `04-02-01` (строки 1290-1294) против примера в исследовании (`04-RESEARCH.md:923-927`).
  - *Механизм:* Требование DAT-03 строго предписывает: «два процесса одновременно пишут в `tasks`, `reminders`, `projects`, `documents` без ошибок блокировки». В приведённом в `04-RESEARCH.md` прототипе теста воркер пишет только в `tasks`. Тест обязан выполнять транзакции записи во все 4 таблицы, учитывая наличие внешних ключей `reminders.task_id -> tasks.id` и `documents.project_id -> projects.id` при активном `PRAGMA foreign_keys = ON;`.
• **LOW:** Ограниченность чтения alias в Pydantic `BaseSettings`.
  - *Локация:* `chat-app/backend/app/core/config.py:19-29`.
  - *Механизм:* Конструкция `SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH") or os.getenv("DATABASE_PATH") ...` на уровне атрибутов класса в Pydantic вычисляется единожды при импорте модуля. Для полноценной поддержки переопределения через окружение в рантайме Pydantic v2 требует использования `Field(default="./data/assistant.db", validation_alias=AliasChoices("SQLITE_DB_PATH", "DATABASE_PATH"))`.

### 4. Suggestions
• В `chat-app/backend/tests/conftest.py` фикстурные данные персоны по умолчанию должны полностью повторять схему `PersonaConfig.model_dump(mode="json")` (со сложными объектами `organizations`, массивами `connectors`, объектом `telegram` и расписанием), исключая падение парсеров токенов.
• В тесте `test_concurrent_write.py` реализовать сценарий, где каждый воркер создает проект, привязанную задачу, напоминание и документ в рамках единой транзакции.
• Использовать `pydantic.Field` с `AliasChoices` в `config.py`.

### 5. Risk Assessment
**MEDIUM.** Риск связан исключительно с неполнотой фикстурных данных персоны, способной завалить тесты Фазы 3. Сама архитектура фабрики соединений и изоляции тестов разработана корректно.

---

## 04-03

### 1. Summary
План `04-03` реализует требования SEC-01 и SEC-02: создаёт модуль `assistant_shared.security` (`patterns`, `rules`, `runner`, `auditor`), устраняет дублирование проверок безопасности между Web API (`chat-app/backend/app/api/v1/security.py`) и CLI-утилитами, ликвидирует исторический дрейф шаблона `Generic Bearer Secret` (обеспечивая 100% паритет `set(web) == set(script)`), переписывает `scripts/security_shield.py` в обоих репозиториях в тонкие CLI-обёртки и актуализирует белые списки ложных срабатываний. Однако план упускает критическую деталь вызова `security_shield.py` из `scripts/gate.py`, что приведёт к падению сквозного гейта.

### 2. Strengths
• **Ликвидация бреши безопасности и дрейфа (SEC-01):** Шаблон `Generic Bearer Secret`, ранее отсутствовавший в `chat-app/backend/app/api/v1/security.py:17-24`, теперь включается в единый список `SECRET_PATTERNS`, а тест `test_nda_equivalence.py:332-341` переводится с проверки подмножества на строгое равенство `assert set(web) == set(script)`.
• **Тонкие CLI-обёртки и синхронизация белых списков (SEC-02):** Скрипты `scripts/security_shield.py` сокращаются со 144 строк до 15-строчных вызовов `audit_repository()`. Синхронно удаляются записи для `scripts/security_shield.py` из `KNOWN_SHIELD_FALSE_POSITIVES` в `scripts/gate.py:63,66` и из `HARDCODE_BASELINE` в обоих файлах `hardcode_baseline.py:18,26`, что предотвращает срабатывание стража устаревших записей в `test_hardcode_scanner.py:155-158`.
• **Защита от утечки NDA-литералов:** Ключевые слова NDA выносятся в библиотеку безопасным способом, исключающим ложные срабатывания при статическом сканировании репозиториев (соответствует требованию запрета открытых литералов в исходном коде).

### 3. Concerns
• **HIGH:** Запуск `security_shield.py` через `sys.executable` в `scripts/gate.py` уронит гейт с `ModuleNotFoundError`.
  - *Локация:* `chat-app/scripts/gate.py:388` (`cmd = [sys.executable, str(script), str(repo_dir)]`).
  - *Механизм:* Согласно документации и стандартам проекта, `gate.py` запускается через системный Python хоста: `python3 scripts/gate.py` (где `sys.executable` равен `/usr/bin/python3`). Пакет `assistant-shared` и его зависимость `pydantic` установлены ТОЛЬКО в виртуальных окружениях `/opt/chat-app/backend/.venv` и `/opt/assistant-core/.venv` (в `/usr/bin/python3` пакет `pydantic` отсутствует, проверено: `ModuleNotFoundError`). Когда `gate.py` доходит до шага `run_shield_step()`, он запускает `security_shield.py` системным интерпретатором `sys.executable`. Скрипт падает с ошибкой `ModuleNotFoundError: No module named 'assistant_shared'`. Гейт фиксирует ненулевой код возврата без находок и окрашивается в КРАСНЫЙ цвет.
• **MEDIUM:** Прямой запуск CLI-скрипта разработчиком вне активированного окружения.
  - *Локация:* `scripts/security_shield.py:1` (`#!/usr/bin/env python3`).
  - *Механизм:* Если разработчик запускает `./scripts/security_shield.py` в терминале без предварительного `source .venv/bin/activate`, шебанг вызывает `/usr/bin/python3`, что приведёт к ошибке импорта.

### 4. Suggestions
• В `scripts/gate.py:388` изменить логику формирования команды: использовать интерпретатор соответствующего виртуального окружения вместо `sys.executable`:
  ```python
  venv_python = CHAT_VENV_BIN / "python" if repo == REPO_CHAT else CORE_VENV_BIN / "python"
  cmd = [str(venv_python), str(script), str(repo_dir)]
  ```
• В тонкую CLI-обёртку `scripts/security_shield.py` добавить автоматический поиск и добавление `/opt/assistant-shared` в `sys.path` при отсутствии установленного пакета, либо автоматический перезапуск через локальный `.venv/bin/python`.

### 5. Risk Assessment
**HIGH.** Из-за вызова `sys.executable` в `scripts/gate.py` единый локальный гейт гарантированно упадет на шаге `security_shield`. Проблема устраняется точечной правкой формирования команды в `gate.py`.

---

## 04-04

### 1. Summary
План `04-04` завершает Фазу 4: настраивает воспроизводимый Git-хук `.githooks/pre-commit` и скрипт установки `scripts/install_hooks.sh` в обоих репозиториях (SEC-03), валидирует перехват коммитов интеграционным тестом `test_pre_commit_hook.py`, устанавливает хуки в рабочие репозитории и выполняет сквозную проверку гейтом `gate.py`. План продуман и направлен на закрытие приёмочных критериев фазы, однако содержит ошибку в логике выбора Python-интерпретатора внутри хука при работе в изолированных тестовых репозиториях `tmp_path`.

### 2. Strengths
• **Воспроизводимость конфигурации хуков (SEC-03):** Использование `git config core.hooksPath .githooks` гарантирует, что хук версионируется в репозитории и не затирается при стандартных операциях git.
• **Комплексный интеграционный тест:** `test_pre_commit_hook.py` проверяет все критические сценарии: успешный коммит чистых файлов, блокировку токенов Google API (`AIzaSy...`), блокировку файлов `.env` и успешный коммит после санитизации индекса.
• **Соблюдение ограничений безопасности боевой БД:** План подтверждает неизменность контрольной суммы SHA-256 боевой базы данных `/opt/assistant-core/data/assistant.db` до и после выполнения всех проверок гейта.

### 3. Concerns
• **HIGH:** Сбой pre-commit хука в тесте `test_pre_commit_hook.py` из-за неэкспортированной переменной `VIRTUAL_ENV`.
  - *Локация:* Текст хука `.githooks/pre-commit` в задаче `04-04-01` (строки 1647-1655).
  - *Механизм:* Логика выбора интерпретатора в хуке полагается на:
    ```bash
    if [ -n "${VIRTUAL_ENV}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
        PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
    elif [ -x "${REPO_ROOT}/backend/.venv/bin/python" ]; then ...
    elif [ -x "${REPO_ROOT}/.venv/bin/python" ]; then ...
    else
        PYTHON_BIN="python3"
    fi
    ```
    При запуске тестов командой `/opt/chat-app/backend/.venv/bin/pytest` без явной активации (`source activate`) переменная окружения `VIRTUAL_ENV` НЕ устанавливается в `os.environ` (проверено на хосте: `VIRTUAL_ENV: None`). Во временном репозитории `tmp_path` каталоги `backend/.venv` и `.venv` отсутствуют. В результате хук выбирает `PYTHON_BIN="python3"` (`/usr/bin/python3`), в котором нет `assistant_shared` и `pydantic`. Хук падает с ошибкой импорта на ЛЮБОМ коммите. Тест 1 («чистый коммит должен пройти») гарантированно упадет с кодом 1.
• **MEDIUM:** Отсутствие скрипта `security_shield.py` во временном тестовом репозитории.
  - *Локация:* `chat-app/backend/tests/test_pre_commit_hook.py`.
  - *Механизм:* Хук вызывает `${REPO_ROOT}/scripts/security_shield.py`. Если тестовая фикстура создает репозиторий в `tmp_path` и копирует только `.githooks/pre-commit`, но не копирует каталог `scripts/`, вызов завершится ошибкой отсутствия файла `No such file or directory`.

### 4. Suggestions
• В скрипте хука `.githooks/pre-commit` добавить явный поиск интерпретатора в стандартных рабочих путях хоста перед откатом на `python3`:
  ```bash
  for candidate in "${VIRTUAL_ENV}/bin/python" "${REPO_ROOT}/backend/.venv/bin/python" "${REPO_ROOT}/.venv/bin/python" "/opt/chat-app/backend/.venv/bin/python" "/opt/assistant-core/.venv/bin/python"; do
      if [ -x "${candidate}" ]; then
          PYTHON_BIN="${candidate}"
          break
      fi
  done
  ```
• В тесте `test_pre_commit_hook.py` при вызове `git commit` явно передавать `env={**os.environ, "VIRTUAL_ENV": str(Path(sys.executable).parent.parent)}` и обязательно копировать `scripts/security_shield.py` в структуру `tmp_path`.

### 5. Risk Assessment
**MEDIUM.** Логика Git-хуков верна по сути, но требует устранения зависимости от системного Python при выполнении тестов в изолированных временных каталогах.

---

## Cross-Plan Analysis & Final Verification

### Анализ зависимостей и порядка выполнения (Wave Sequence)
Последовательность волн выбрана безупречно:
1. **Wave 1 (04-01):** Создание общего пакета, мигратора и базовой схемы DDL.
2. **Wave 2 (04-02):** Подключение фабрики WAL к процессам, устранение хардкода путей и изоляция тестового набора `chat-app`.
3. **Wave 3 (04-03):** Создание модуля безопасности в пакете, рефакторинг API и CLI shield, синхронизация белых списков.
4. **Wave 4 (04-04):** Установка pre-commit хуков и финальная верификация гейтом `gate.py`.
Блокировки между волнами логичны: фабрика соединений и модуль безопасности опираются на пакет, созданный в Wave 1.

### Сводная таблица соответствия требованиям (Requirements Traceability)

| Требование | Описание | Охват планами | Статус и ключевые риски |
|---|---|---|---|
| **DAT-01** | Схема БД и миграции в общей библиотеке, версионирование, baseline без изменения данных | `04-01` | Охватывается полностью. Требуется поддержать `:memory:` соединения. |
| **DAT-02** | Конфигурация пути БД из env, удаление хардкода `/opt/assistant-core/...` | `04-02` | Охватывается полностью (`config.py` + `test_db_config.py`). |
| **DAT-03** | Режим WAL, `busy_timeout=5000`, тест конкурентной записи двух процессов | `04-02` | Охватывается полностью. В тесте обязательно писать во все 4 таблицы (`tasks`, `reminders`, `projects`, `documents`). |
| **DAT-04** | Изоляция тестов `chat-app` на чистой временной БД без обращения к `assistant-core` | `04-02` | Охватывается. Фикстура `conftest.py` должна содержать полную структуру `PersonaConfig`. |
| **SEC-01** | Единая библиотека `assistant_shared.security`, паритет Generic Bearer | `04-03` | Охватывается полностью (`patterns.py`, `rules.py`, `auditor.py`). |
| **SEC-02** | `scripts/security_shield.py` — тонкая обёртка, тест отсутствия дрейфа | `04-03` | Охватывается (`test_shield_parity.py`). Требуется скорректировать запуск в `gate.py`. |
| **SEC-03** | Воспроизводимый pre-commit hook, блокирующий утечки секретов | `04-04` | Охватывается (`core.hooksPath` + `test_pre_commit_hook.py`). |

### Общая оценка рисков Фазы 4
**MEDIUM-HIGH (до внесения правок) ➔ LOW (после внесения предложенных коррекций).**
Архитектура пакета `/opt/assistant-shared` и стратегия миграций выбраны исключительно удачно (KISS, чистый SQL, отсутствие тяжелых зависимостей). Выявленные дефекты носят характер шероховатостей интеграции рантайма (отсутствие `setuptools` в venv, уничтожение БД `:memory:` при `conn.close()`, вызов системного `sys.executable` в `gate.py` и неполные фикстурные данные персоны). Их заблаговременный учет в задачах гарантирует быстрое и бесперебойное прохождение фазы без циклических сбоев автономного разработчика.

---

## Consensus Summary

Независимое рецензирование планов Фазы 4 («Владелец схемы БД и общая библиотека безопасности») подтвердило общую архитектурную целостность декомпозиции на 4 волны (создание `assistant-shared`, конфигурация БД/WAL/изоляция тестов, общая библиотека безопасности, и pre-commit хук).

При этом глубокая верификация исходного кода обоих репозиториев (`/opt/chat-app` и `/opt/assistant-core`) выявила 4 критических дефекта уровня HIGH, которые приведут к сбоям на шаге исполнения, если не будут скорректированы в планах:

### Agreed Strengths
• **Архитектурный паритет и KISS (DAT-01, SEC-01):** Выбор легковесного версионированного SQL-раннера вместо избыточного Alembic и объединение паттернов поиска секретов (включая устранение исторического пропуска `Generic Bearer Secret`).
• **Аппаратное устранение блокировок SQLite (DAT-03):** Гарантированное включение `PRAGMA journal_mode = WAL` и `PRAGMA busy_timeout = 5000` при каждом подключении.
• **Изоляция окружений и устранение жестких связей (DAT-02, DAT-04):** Ликвидация хардкода путей к БД и отказ от вызова seed-скрипта `assistant-core` из тестов `chat-app`.
• **Воспроизводимый перехват секретов (SEC-03):** Перевод `security_shield.py` в тонкую CLI-обёртку и закрепление pre-commit хука через `core.hooksPath`.

### Agreed Concerns
• **HIGH (План 04-01): Разрушение работы тестов `assistant-core` с базой `:memory:`.**
  Раннер миграций `run_migrations(":memory:")` открывает и тут же закрывает отдельное соединение `sqlite3.connect(":memory:")`, в результате чего DDL применяется в уничтожаемую in-memory базу, а разделяемое соединение `_shared_conn` остаётся пустым. Это вызовет падение более 20 тестовых модулей ядра (`sqlite3.OperationalError: no such table`).
• **HIGH (План 04-01): Сбой сборки/установки пакета через `pip install --no-build-isolation -e`.**
  В чистых виртуальных окружениях Python 3.12 пакет `setuptools` отсутствует по умолчанию, что вызовет немедленную ошибку установки пакета в режиме разработки.
• **HIGH (План 04-02): Невалидная фикстура персоны в тестах `chat-app`.**
  Упрощенная структура `DEFAULT_PERSONA_FIXTURE` из исследования с плоскими строками для организаций сломает `persona_tokens.py` (`AttributeError: str has no attribute get`) и тесты Фазы 3.
• **HIGH (План 04-03): Падение единого гейта `scripts/gate.py` при запуске `security_shield.py`.**
  В `gate.py:388` вызов выполняется через `sys.executable` (`/usr/bin/python3`), где нет установленного пакета `assistant_shared` и `pydantic`, что окрасит локальный CI-гейт в красный цвет.
• **HIGH (План 04-04): Сбой pre-commit хука во временных репозиториях тестов.**
  Хук в `tmp_path` откатывается на системный `python3`, если переменная `VIRTUAL_ENV` не экспортирована явно.

### Actionable Suggestions for Re-planning (/gsd-plan-phase 4 --reviews)
1. Разрешить мигратору принимать уже открытое соединение (`sqlite3.Connection` / `aiosqlite.Connection`) для поддержки `:memory:`.
2. Устанавливать `assistant-shared` через `.pth`-ссылку или обеспечить сборочный бэкенд без внешней сетевой зависимости.
3. Скопировать полную каноническую структуру словаря персоны в фикстуру `conftest.py`.
4. В `scripts/gate.py:388` запускать `security_shield.py` через интерпретатор виртуального окружения (`CHAT_VENV_BIN / "python"`), а не `sys.executable`.
5. В pre-commit хуке предусмотреть перебор путей к `.venv/bin/python` перед откатом на системный `python3`.
