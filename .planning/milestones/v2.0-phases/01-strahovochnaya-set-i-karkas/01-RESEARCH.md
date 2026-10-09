# Phase 1: Страховочная сеть и каркас - Research

**Researched:** 2026-10-01
**Domain:** локальный гейт качества (stdlib Python), import-linter (архитектурные контракты), pytest-каркас синтетической персоны, baseline тестов двух Python-репозиториев
**Confidence:** HIGH (почти всё проверено фактическими запусками на этой машине; единственное MEDIUM — выбор режима `security_shield.py`, он ждёт решения владельца)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Владелец (не специалист) делегировал технические решения этой фазы Claude: «продумай сам». Все решения ниже приняты по KISS/YAGNI из CLAUDE.md и помечены как решения по усмотрению Claude; планировщик не должен считать их решениями владельца уровня W1–W10, но обязан следовать им, если исследование не опровергнет их фактами (тогда — вернуть на обсуждение).

#### Гейт и документ baseline (FND-01, FND-04)
- **D-01:** Гейт — один stdlib-only Python-скрипт `scripts/gate.py` в chat-app (без внешних зависимостей, запускается любым `python3`). Он вызывает по абсолютным путям: два pytest (двумя документированными командами), `lint-imports` для каждого репозитория и `scripts/security_shield.py` каждого репозитория. Путь к assistant-core — константа в начале скрипта, переопределяемая переменной окружения `ASSISTANT_CORE_DIR`.
- **D-02:** Гейт НЕ обрывается на первой ошибке: выполняет все проверки, печатает по-русски таблицу «репозиторий × проверка → ✓/✗» и итог «ЗЕЛЁНЫЙ» или «КРАСНЫЙ»; код возврата 0 только при полностью зелёном итоге. Скрытых deselect/skip/xfail нет.
- **D-03:** Защита боевой БД (по одной функции в скрипте, чтобы Фаза 4 заменила её на временную БД из общей схемы): гейт копирует `/opt/assistant-core/data/assistant.db` во временный каталог (модуль `sqlite3`, backup API); chat-app pytest запускается с `SQLITE_DB_PATH=<копия>`, assistant-core pytest — с `DATABASE_URL=sqlite+aiosqlite:///<копия>`; до и после гейт считает SHA-256 боевой `assistant.db` и красит итог, если хеш изменился. Правка кода для переопределения не нужна (`SQLITE_DB_PATH` — поле `pydantic-settings`; `DATABASE_URL` читается из окружения в `src/config.py`).
- **D-04:** Документ baseline — `docs/BASELINE.md` в chat-app (по-русски): для каждого репозитория команда запуска, число тестов, статус каждого файла, SHA коммита обоих репозиториев, версии Python/pytest/import-linter, дата; плюс раздел «Правила» (100% pytest на каждом шаге, атомарный коммит, revert, не ослаблять тесты). Полный пофайловый/потестовый вывод `pytest -v` — рядом, в `docs/baseline/pytest-chat-app.txt` и `docs/baseline/pytest-assistant-core.txt` (сырой текст; JSON/машиночитаемый формат не нужен — YAGNI).
- **D-05:** Команду гейта добавить одной строкой в раздел «Development Commands» CLAUDE.md — это изменение файла инструкций, выполнять только с явным упоминанием в SUMMARY и на ревью владельца.

#### import-linter (FND-02)
- **D-06:** `import-linter` — dev-зависимость, а не рантайм: новый файл `requirements-dev.txt` в каждом репозитории (с нижней границей версии, на момент обсуждения на PyPI доступна 2.15), установка в оба `.venv`. Это изменение окружения вне git — зафиксировать версию в `docs/BASELINE.md`.
- **D-07:** Конфиг — файл `.importlinter` (INI) в корне каждого репозитория; `pyproject.toml` не создавать (его нет ни в одном репозитории).
- **D-08:** assistant-core: контракт `forbidden` — источники: `src.brain` и `src.notifier.bot_handler`; запрещённые цели: `src.connectors`, `src.calendar`, `src.parser`, `src.sender`, `src.collector` (и `src.notifier` кроме `bot_handler`, если не создаёт ложных срабатываний). ВАЖНО: в ROADMAP `notifier` назван адаптером, но известное нарушение лежит в `bot_handler.py` (он в `src/notifier/`), поэтому `bot_handler` включён как источник — иначе PRT-04 («`ignore_imports` пуст») был бы недоказуем. Точные границы слоёв исследователь обязан сверить фактическим запуском (`grimp`/`lint-imports`), включая инлайн-импорты внутри функций. `src/main.py` — корень композиции и в контракт не входит.
- **D-09:** chat-app: контракт `forbidden`: пакет `app` не импортирует внутренние модули assistant-core (`src`) — внешний запрещённый модуль через `include_external_packages`. Контракт сегодня проходит тривиально; его ценность — защитить от появления связи.
- **D-10:** Известные нарушения — явный список `ignore_imports` с комментарием «долг, только убывает» у каждой строки; Фаза 2 опустошает его.
- **D-11:** «Доказанно падает» — постоянный pytest-тест в каждом репозитории (`test_architecture_contract.py`): строит во временном каталоге синтетический мини-пакет с контрактом той же формы и намеренным нарушением и проверяет, что `lint-imports` завершается с ненулевым кодом; второй тест проверяет, что на чистом синтетическом пакете код нулевой. Это защищает от «тихо ничего не проверяющего» контракта. Реальный конфиг проверяется самим гейтом.

#### Вторая синтетическая персона (FND-03)
- **D-12:** Форма — обычный Python-модуль `synthetic_persona.py` с простым `dict` (не Pydantic, не YAML) и фикстура `synthetic_persona` в новом `conftest.py` каждого тестового набора (`backend/tests/`, `tests/`). Причины: у chat-app в `.venv` нет PyYAML; схема `persona.yaml` принадлежит Фазе 3 (PER-01) и Фаза 1 не должна её предвосхищать.
- **D-13:** Идентифицирующие поля берутся из того, что сегодня зашито в код (аудит — CONCERNS.md): ФИО, должность/звание, названия организаций (вуз, компания), 4 рабочих пространства (id, название, путь, clearance, remote, запретные слова), проект учёта по умолчанию, норма часов в день, адреса сайта расписания и личного кабинета, названия предметов/слоты, идентификатор пользователя Telegram и бота. У синтетической персоны ВСЕ значения заведомо вымышленные, отличаются от персоны по умолчанию в каждом поле (зарезервированные домены `.example`, пути под `/synthetic/`, иная норма часов, имена вроде «Тестовый Тест Тестович»), и она содержит рабочие пространства всех трёх clearance.
- **D-14:** Тесты каркаса, проходящие уже сейчас: фикстура грузится; все ключи идентифицирующих полей присутствуют и непусты; ни одно значение не содержит токенов владельца (ГУАП/GUAP, Тидекс/Tydex, ФИО — они хранятся в ОДНОЙ константе-denylist внутри теста, чтобы Фаза 3 заменила её данными персоны по умолчанию, PER-08/PER-09); каждое поле отличается от того, что зашито сегодня; допускаемые значения clearance — ровно `public`, `internal`, `restricted_nda`.
- **D-15:** Проверки, которые включатся в Фазе 3, перечисляются явно списком в `docs/BASELINE.md` (раздел «Ожидают Фазы 3») и в докстринге `synthetic_persona.py` — БЕЗ skip/xfail-маркеров. Источник перечня — PER-01..09 и BCK-02 (промпты, рабочие пространства/Security Tile, дефолты области, параметры коннекторов, scope-решения, отсутствие хардкода).
- **D-16:** Копий две (в обоих репозиториях общей библиотеки ещё нет, Фаза 4). Дрейф ловит гейт: один дополнительный шаг сравнивает два файла `synthetic_persona.py` по SHA-256 и красит итог при расхождении.

#### Красные тесты на старте (FND-01)
- **D-17:** Красный тест классифицируется на три корзины: (а) окружение/данные (тесту нужны строки, которые есть только в боевой БД; путь отсутствует) — чинится в тестовой инфраструктуре фикстурами/окружением без правки ассертов; (б) устаревший тест при актуальном коде — исправление допустимо только с сохранением смысла проверки, в отдельном атомарном коммите и с записью в baseline; (в) реальная ошибка продакшен-кода — в Фазе 1 НЕ чинится (критерий 5 фазы: логика не меняется): остаётся красной и немедленно выносится владельцу с вариантами; гейт показывает красный итог честно.
- **D-18:** Прежде чем гонять набор assistant-core, исследователь определяет, какие тесты обращаются к внешним сервисам или реальным учётным данным (подозрительные: `test_gdrive_client.py`, `test_notion_client.py`, `test_voice.py`, `test_guap_lms.py`, `test_lms_bot_workflow.py`). Тест, которому нужен живой внешний доступ с боевыми учётными данными, запускается только с ведома владельца: файлы `.env`, `credentials.json`, `token.json`, `*.session` агенты не читают.
- **D-19:** Коммиты атомарные и раздельные по репозиториям: изменения chat-app (гейт, baseline, тесты, `.importlinter`, `requirements-dev.txt`) коммитятся в chat-app; изменения assistant-core (`.importlinter`, `requirements-dev.txt`, `tests/test_architecture_contract.py`, `tests/conftest.py`, `tests/synthetic_persona.py`) — в assistant-core.

### Claude's Discretion

Все области (гейт, import-linter, персона, красные тесты) отданы владельцем на усмотрение Claude. Дополнительно планировщик вправе выбрать: имена тестовых функций, точный формат таблицы гейта, структуру `docs/baseline/`, способ парсинга вывода pytest, список полей синтетической персоны сверх D-13, если это не нарушает D-01..D-19.

### Deferred Ideas (OUT OF SCOPE)

- pre-commit hook с проверкой — Фаза 4 (SEC-03).
- Временная пустая БД из общей схемы вместо копии боевой — Фаза 4 (DAT-04); D-03 изолирован одной функцией именно ради этой замены.
- Единая общая библиотека вместо дублей `security_shield.py`/`synthetic_persona.py` — Фаза 4.
- Тест-сканер хардкода профиля — Фаза 3 (baseline-allowlist), Фаза 6 (пустой allowlist).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FND-01 | Baseline тестов: команда, число тестов, статус каждого, дата; прогон chat-app на копии БД; красные устранены либо вынесены владельцу | Фактический baseline снят (раздел «Фактический baseline»): chat-app 14/14, assistant-core 127/127, красных нет, два прогона дают одно и то же; механизм защиты боевой БД проверен (раздел «Защита боевой БД») |
| FND-02 | Контракт import-linter use-cases ↛ адаптеры; backend chat-app ↛ `src`; `ignore_imports` как убывающий долг; доказанное падение | Подобран и проверен рабочий конфиг для обоих репозиториев; найдена и обойдена ловушка namespace-пакетов (тихий пропуск); перечень реальных нарушений; шаблон теста «падает на нарушении» проверен прототипом |
| FND-03 | Каркас второй синтетической персоны, проходящие тесты, перечень проверок Фазы 3 без xfail | Форма `dict` + фикстура, набросок полей по blueprint §3.1 и CONCERNS.md, список «Ожидают Фазы 3», ловушки сканеров секретов |
| FND-04 | Единая локальная команда-гейт, итог по репозиториям, правило «100% pytest» в baseline | Конструкция гейта, парсинг через junitxml, выявлена ловушка `security_shield.py` (в режиме по умолчанию гейт был бы пустым, в режиме `--all` оба репозитория красные) |
</phase_requirements>

## Summary

Оба тестовых набора на старте полностью зелёные и детерминированные: chat-app — 14 passed (4 файла), assistant-core — 127 passed (21 файл), 31 предупреждение DeprecationWarning, ни одного skip/xfail; два последовательных прогона дали одинаковый результат. Боевая `assistant.db` (хеш SHA-256 `baef14f7…`) не изменилась ни после chat-app на копии, ни после assistant-core. Красных тестов на старте нет, поэтому все три корзины D-17 в Фазе 1 не понадобятся. Единственное «красное» на старте — `security_shield.py --all` в обоих репозиториях (ложные срабатывания эвристик), а в режиме по умолчанию он вообще ничего не проверяет на чистом дереве.

Исследование опровергло или уточнило три допущения CONTEXT.md, они важнее всего для планировщика. (1) **Namespace-ловушка import-linter:** каталоги `src/connectors`, `src/sender` (assistant-core) и `app/core` (chat-app) не содержат `__init__.py`, и grimp не видит их в графе. Наивный контракт D-08 из CONTEXT.md сообщает «KEPT» при пяти реальных нарушениях и не ругается даже на несуществующий запрещённый модуль — то есть «молча ничего не проверяет». Лечится без правки продакшен-кода через официально документированный приём: перечислить «порции» namespace-пакетов в `root_packages` (`src`, `src.connectors`, `src.sender`; `app`, `app.core`) плюс тест-страж, что все модули контракта реально есть в графе. (2) **`DATABASE_URL` для assistant-core не переопределяется окружением:** `src/config.py` вызывает `load_dotenv(..., override=True)`, и боевой `.env` перебивает значение из окружения (проверено экспериментом, файл `.env` не читался). Для этого репозитория D-03 половинчат, но и не нужен: ни один тест не использует `config.SQLITE_DB_PATH` для записи, защитой остаётся хеш-контроль. (3) **`security_shield.py`:** см. Open Questions №1 — нужно решение владельца.

Технически Фаза 1 — малая и низкорисковая: ни одной строки продакшен-логики менять не нужно (подтверждено: контракты, фикстуры и гейт — только новые файлы). Но есть связь, о которой легко забыть: `test_security_audit_all` в chat-app аудирует `git ls-files` ОБОИХ репозиториев регулярками секретов и требует `status == "passed"`; поэтому любые новые файлы (персона, тесты, baseline-выводы) не должны содержать строк, похожих на секреты.

**Primary recommendation:** Делать по D-01..D-19 с тремя поправками: `root_packages` с порциями namespace-пакетов + страж-тест против «пустого» контракта; `allow_indirect_imports = True` и ровно 5 записей в `ignore_imports`; гейт не передаёт `DATABASE_URL` в assistant-core (бесполезно), а полагается на хеш-контроль; режим `security_shield.py` вынести владельцу (рекомендация — `--all` + замороженный список известных ложных срабатываний).

## Project Constraints (from CLAUDE.md)

Из `/opt/chat-app/CLAUDE.md` (и идентичных по смыслу разделов `/opt/assistant-core/CLAUDE.md`):
- Тесты chat-app: `/opt/chat-app/backend/.venv/bin/pytest backend/tests` (запуск из `/opt/chat-app`); assistant-core: `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests`; security scan: `/opt/assistant-core/.venv/bin/python3 scripts/security_shield.py`.
- Поддерживать 100% pass; HITL для деструктивных действий; строгая air-gap-изоляция NDA. Для Фазы 1 это означает: не ослаблять и не удалять существующие тесты, не включать сервисы.
- KISS и YAGNI; typed dataclass/Pydantic — но по D-12 для персоны Фазы 1 сознательно обычный `dict`.
- Async-first для I/O (`aiosqlite`, `httpx`, `aiohttp`): новые тесты каркаса синхронны и I/O не делают; гейт — синхронный скрипт (допустимо: это не рантайм-сервис, а утилита).
- Код, комментарии, коммиты — по-английски или по-русски; пользовательский вывод — строго по-русски (гейт и BASELINE.md — по-русски).
- Делегирование объёмной рутины агентам Antigravity — только через `scripts/agy_task.sh` (никогда `agy` напрямую; NDA-рабочие пространства обёртка отказывается обрабатывать). Для этой фазы делегировать нечего: объём мал и требует внимательного ревью.
- Память пользователя: владелец читает только по-русски, вопросы — через AskUserQuestion с вариантами; ограничение VPS — 2 ГБ ОЗУ (тяжёлые параллельные прогоны запрещены: два pytest запускать последовательно).
- Ограничения фазы из задачи: сервисы остановлены, боевую `assistant.db` не трогать, `.env`/`credentials.json`/`token.json`/`*.session` не читать.
- Изменение CLAUDE.md (D-05) — только с явным упоминанием в SUMMARY.

## Architectural Responsibility Map

Фаза не про веб-слои, поэтому «ярусы» — это инструменты разработки. Карта нужна планировщику, чтобы файлы не попали не в тот репозиторий.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Гейт «одна команда» (`scripts/gate.py`) | chat-app, `scripts/` (dev-tooling) | — | D-01: вызывает оба репозитория по абсолютным путям; assistant-core о нём не знает |
| Защита боевой БД (копия + хеш) | chat-app, `scripts/gate.py` (одна функция) | — | D-03; Фаза 4 заменит одну функцию |
| Baseline-документ и сырые выводы pytest | chat-app, `docs/` | — | D-04; `.planning/` и `docs/` живут в chat-app |
| Контракт import-linter assistant-core | assistant-core, `.importlinter` | тесты в `tests/` | D-07/D-19: конфиг лежит в том репозитории, который проверяет |
| Контракт import-linter chat-app | chat-app, `.importlinter` | тесты в `backend/tests/` | то же |
| Тест «контракт падает на нарушении» | оба набора, `test_architecture_contract.py` | — | D-11; постоянный тест, не одноразовая демонстрация |
| Каркас второй персоны | оба набора, `synthetic_persona.py` + `conftest.py` | гейт (сравнение SHA-256) | D-12, D-16: две идентичные копии до общей библиотеки |
| Проверка секретов | оба репозитория, `scripts/security_shield.py` (как есть) | гейт (вызов и разбор) | D-01: скрипт не меняется |
| Установка dev-зависимости | `.venv` обоих репозиториев (окружение вне git) | `requirements-dev.txt` | D-06; фиксируется версия в BASELINE |

## Фактический baseline (снят в этой сессии, команды только для чтения плюс прогон на копии)

Все числа получены реальными запусками 2026-10-01; сервисы при этом остановлены (`systemctl is-active`: chat-app — inactive, assistant-worker — failed, dev-bridge — inactive) [VERIFIED: запуск `systemctl is-active`].

| Параметр | chat-app | assistant-core |
|----------|----------|----------------|
| Ветка / HEAD | `master` / `8d081d9` | `main` / `6e0850b` |
| Дерево | чистое | чистое |
| Python | 3.12.3 | 3.12.3 |
| pytest | 9.1.1 (плагин: anyio 4.15.1) | 9.1.1 (плагин: pytest-asyncio 1.4.0, `asyncio_mode = auto`) |
| Команда (cwd) | `/opt/chat-app/backend/.venv/bin/pytest backend/tests` (cwd `/opt/chat-app`) | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests` (cwd `/opt/assistant-core`) |
| Итог | **14 passed** за ~2 с | **127 passed**, 31 warnings за ~43–47 с |
| Файлов | 4 | 21 |
| Повторный прогон | 14 passed | 127 passed (детерминированно) |

Тесты по файлам (из `pytest -v`):
- chat-app: `test_dashboard_api.py` 5, `test_health.py` 4, `test_models.py` 2, `test_security_api.py` 3. Параметризация `[asyncio]` приходит от плагина anyio (только бэкенд asyncio) — это нормальные node-id, не дубли.
- assistant-core: `test_aadhk_parser.py` 3, `test_bot_group_isolation.py` 3, `test_bot_menu.py` 3, `test_brain.py` 6, `test_debrief_parser.py` 2, `test_email_collector.py` 7, `test_email_reply_workflow.py` 8, `test_fast_intent_router.py` 10, `test_gdrive_client.py` 3, `test_guap_lms.py` 8, `test_hitl_safety_guardrails.py` 3, `test_key_rotator.py` 6, `test_live_ticker.py` 8, `test_lms_bot_workflow.py` 10, `test_memory_review.py` 5, `test_methodist.py` 2, `test_notion_client.py` 3, `test_phase1.py` 15, `test_phase2_filter.py` 8, `test_secretary_dialog.py` 7, `test_voice.py` 8. Сумма 127.

Красных тестов на старте нет (в `tests/` нет маркеров skip/xfail; вхождения слова `skipped` в `test_phase1.py:314,320` — ключи словаря статистики, не маркеры) [VERIFIED: grep + два прогона]. Итоговые числа после Фазы 1 вырастут за счёт новых тестов каркаса — BASELINE фиксирует «число на старте» (14 и 127) отдельно от числа после фазы.

### Анализ тестов на внешний доступ (D-18)

Все пять подозрительных файлов используют только заглушки, живого внешнего доступа нет [VERIFIED: чтение содержимого тестов]:
- `test_gdrive_client.py`: Google API замещён через `patch("...client.build")`/`patch("...client.Credentials")`, токен — во временном файле. ОДНАКО тест `create_server_backup_archive` вызывает продакшен-код с зашитыми абсолютными путями (`src/connectors/gdrive/client.py:198-209`) и упаковывает в `tar.gz` во временный каталог pytest: боевую `assistant.db`, `assistant_worker.session` и `/opt/assistant-core/.env` (если файлы существуют). Это чтение, не запись (хеш БД не меняется), но копия секретов оказывается в `/tmp/pytest-of-root/pytest-N/...` с правами 644 внутри каталога 0700 (хранятся последние 3 прогона). Тест проходит, если существует хотя бы один из файлов (`assert any(n in names for n in ["assistant.db", "assistant-core.env"])`) — то есть он зависит от наличия боевой БД на диске (корзина (а), для Фазы 4 важно: DAT-04).
- `test_notion_client.py`, `test_voice.py`, `test_guap_lms.py`, `test_lms_bot_workflow.py`: `httpx`/`requests`-сессии и клиенты замещены `patch`/`MagicMock`/`AsyncMock`; учётные данные в тестах — явные фиктивные строки.
- Остальные наборы используют `Database(":memory:")` или `tmp_path`. Единственное исключение — `test_email_collector.py:222` `EmailCollector()` без аргумента строит `Database(config.SQLITE_DB_PATH)` (то есть боевой путь), но конструктор ленивый и в тесте нет обращения к БД (хеш не изменился).

## Защита боевой БД (проверка D-03)

| Репозиторий | Что сказано в D-03 | Факт | Вывод |
|-------------|--------------------|------|-------|
| chat-app | `SQLITE_DB_PATH=<копия>` без правки кода | `SQLITE_DB_PATH: str = "/opt/assistant-core/data/assistant.db"` — поле `pydantic_settings.BaseSettings`, переменная окружения перебивает значение; `/opt/chat-app` не содержит `.env` [VERIFIED: `backend/app/core/config.py:19`, запуск `SQLITE_DB_PATH=... python -c "print(settings.SQLITE_DB_PATH)"` напечатал путь копии]. Прогон 14 тестов изменил копию (хеш копии стал `14eb6b23…`, исходный остался `baef14f7…`) | Работает; CRUD-тесты действительно пишут (создают/удаляют записи), поэтому копия обязательна |
| assistant-core | `DATABASE_URL=sqlite+aiosqlite:///<копия>` | `src/config.py:9-12`: `load_dotenv(BASE_DIR / ".env", override=True)` затем `DATABASE_URL = os.getenv("DATABASE_URL", ...)`. Эксперимент: `DATABASE_URL=sqlite+aiosqlite:////tmp/.../probe.db python -c "from src import config; print(config.DATABASE_URL)"` напечатал `sqlite+aiosqlite:///./data/assistant.db`, а не переданное значение — значит `.env` (в нём есть `DATABASE_URL`) перебивает окружение [VERIFIED: запуск; содержимое `.env` не читалось и не выводилось] | Переопределение окружением НЕ работает. Но и не нужно: тесты не пишут в боевую БД (см. выше), хеш не менялся после двух полных прогонов |

Рекомендация планировщику: функция защиты БД в `gate.py` делает (а) backup-копию боевой БД через `sqlite3` в каталог `tempfile.mkdtemp()` (права 0700), (б) передаёт `SQLITE_DB_PATH=<копия>` только в chat-app pytest, (в) считает SHA-256 боевой БД до и после ВСЕХ шагов и красит итог при расхождении (обе проверки), (г) НЕ передаёт `DATABASE_URL` в assistant-core (в BASELINE честно записать, что переопределение там невозможно без правки кода или `.env`, а защита — хеш-контроль). Если владелец захочет настоящую изоляцию assistant-core — это правка тестовой инфраструктуры (autouse-фикстура, подменяющая `config.SQLITE_DB_PATH`), её можно вынести в Фазу 4 (DAT-04); в Фазе 1 не нужна (YAGNI).

Копирование делать с источником, открытым только на чтение: `sqlite3.connect("file:/opt/assistant-core/data/assistant.db?mode=ro", uri=True).backup(dst)` — не создаёт журналов рядом с боевой БД [VERIFIED: выполнено, хеш не изменился].

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| import-linter | 2.15 (выпущена 2026-09-04) | Контракты на импорты (`lint-imports`) | Решение владельца-делегата D-06; единственный зрелый инструмент для этой задачи; BSD-2, автор seddonym [VERIFIED: pypi.org/project/import-linter]. Поддерживает Python 3.10–3.14 (у нас 3.12.3) |
| grimp | 3.17 (транзитивная) | Построение графа импортов (используется import-linter и в тесте-страже) | Входит в зависимости import-linter [VERIFIED: `pip install --dry-run import-linter` в обоих `.venv`] |
| pytest | 9.1.1 (уже установлен в обоих `.venv`) | Тесты каркаса и тест контракта | Уже стандарт репозиториев |
| Python stdlib (`subprocess`, `sqlite3`, `hashlib`, `tempfile`, `xml.etree.ElementTree`, `argparse`) | 3.12.3 | Гейт `scripts/gate.py` | D-01: без внешних зависимостей |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich, markdown-it-py, mdurl (транзитивные от import-linter) | 15.0.0 / 4.2.0 / 0.1.2 | Вывод `lint-imports` | Устанавливаются автоматически; на существующие пакеты не влияют |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| import-linter | собственный AST-обход в pytest | Отвергнуто: FND-02 прямо требует import-linter; кастомный сканер — именно то, что не надо писать самому |
| Парсинг итоговой строки pytest regex-ом | `--junitxml` + `xml.etree` | junitxml точнее (поля `tests`, `failures`, `errors`, `skipped`); рекомендуется для гейта; решение по способу — на усмотрение планировщика |

**Installation (в оба `.venv`, делает executor; изменение окружения вне git):**
```bash
# requirements-dev.txt (в корне каждого репозитория; для chat-app — рядом с backend/requirements.txt допустимо, но D-06 говорит «в каждом репозитории» — корень)
import-linter>=2.15

/opt/chat-app/backend/.venv/bin/pip install -r /opt/chat-app/requirements-dev.txt
/opt/assistant-core/.venv/bin/pip install -r /opt/assistant-core/requirements-dev.txt
```
Сухой прогон `pip install --dry-run import-linter` в обоих `.venv` показал: будут установлены только `grimp-3.17 import-linter-2.15 markdown-it-py-4.2.0 mdurl-0.1.2 rich-15.0.0`; уже установленные пакеты (click 8.5.0, pygments, typing_extensions) не меняются [VERIFIED: pip dry-run]. Обе `.venv` используют pip 26.2.1.

**Version verification:** `pip index versions import-linter` → `import-linter (2.15)` [VERIFIED: pip index]; страница PyPI: «Released September 4, 2026», Python 3.10–3.14 [VERIFIED: pypi.org/project/import-linter].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| import-linter | PyPI | зрелый проект (текущий релиз 2.15 от 2026-09-04) | сервис легитимности вернул `null` | github.com/seddonym/import-linter (указан на странице PyPI; в метаданных сервиса `repoUrl: null`) | SUS (причины сервиса: `too-new`, `unknown-downloads`, `no-repository`) | Flagged — planner must add checkpoint |
| grimp | PyPI | текущий релиз 3.17 от 2026-09-04 | `null` | в метаданных сервиса отсутствует | SUS (те же причины) | Flagged — planner must add checkpoint (транзитивная зависимость import-linter) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `import-linter` [WARNING: flagged as suspicious — verify before using.], `grimp` [WARNING: flagged as suspicious — verify before using.] — планировщик вставляет `checkpoint:human-verify` перед установкой в `.venv`.

Пояснение для checkpoint: вердикт SUS вызван тем, что СВЕЖАЯ версия вышла меньше месяца назад и у сервиса нет данных о загрузках/репозитории, а не признаками подделки: имя пакета взято из CONTEXT.md D-06 и подтверждено официальной страницей PyPI (автор seddonym, BSD-2, ссылка на GitHub и readthedocs) и официальной документацией [CITED: pypi.org/project/import-linter]. `postinstall`-скриптов у PyPI-пакетов нет (`postinstall: null`). Ранее этот пакет в окружении не стоял. Владельцу достаточно подтвердить установку двух имён и версий `import-linter>=2.15` (в `requirements-dev.txt` для воспроизводимости можно закрепить `==2.15` и `grimp==3.17` в BASELINE).

## Architecture Patterns

### System Architecture Diagram

```
Владелец: python3 /opt/chat-app/scripts/gate.py
        |
        v
 [0] хеш боевой assistant.db (SHA-256 "до") ----------------------------+
        |                                                               |
 [1] sqlite3 backup (mode=ro) -> копия в mkdtemp() (0700)               |
        |                                                               |
        +--> chat-app: pytest backend/tests  (env SQLITE_DB_PATH=копия) -> junitxml -> N passed / failed / skipped
        +--> chat-app: lint-imports (PYTHONPATH=backend, cwd=/opt/chat-app)       -> exit 0/1
        +--> chat-app: security_shield.py (режим — вопрос владельцу)               -> exit + разбор
        +--> assistant-core: pytest tests (cwd=/opt/assistant-core)               -> junitxml
        +--> assistant-core: lint-imports (cwd=/opt/assistant-core)               -> exit 0/1
        +--> assistant-core: security_shield.py                                    -> exit + разбор
        +--> дрейф: SHA-256(chat-app persona) == SHA-256(core persona)
        |
 [2] хеш боевой assistant.db ("после") == "до"? ------------------------+
        |
        v
 таблица «репозиторий × проверка → ✓/✗» (по-русски) -> итог «ЗЕЛЁНЫЙ» (exit 0) / «КРАСНЫЙ» (exit 1)
 + удаление временного каталога (в finally)
```

### Recommended Project Structure

```
/opt/chat-app/
├── .importlinter                         # контракт D-09 (root_packages = app, app.core)
├── requirements-dev.txt                  # import-linter>=2.15
├── scripts/gate.py                       # D-01 (stdlib-only)
├── docs/BASELINE.md                      # D-04 (+ «Правила», «Ожидают Фазы 3»)
├── docs/baseline/pytest-chat-app.txt     # сырой pytest -v
├── docs/baseline/pytest-assistant-core.txt
└── backend/tests/
    ├── conftest.py                       # фикстура synthetic_persona (D-12)
    ├── synthetic_persona.py              # dict + докстринг «Ожидают Фазы 3»
    ├── test_synthetic_persona.py         # D-14
    ├── test_architecture_contract.py     # D-11 + страж «контракт не пустой»
    └── test_gate.py                      # (рекомендуется) чистые функции гейта

/opt/assistant-core/
├── .importlinter                         # контракт D-08 (root_packages = src, src.connectors, src.sender)
├── requirements-dev.txt
└── tests/
    ├── conftest.py
    ├── synthetic_persona.py              # байт-в-байт копия chat-app
    ├── test_synthetic_persona.py
    └── test_architecture_contract.py
```

### Pattern 1: Контракт assistant-core (проверен фактическим запуском)

**What:** два контракта `forbidden` — один для `src.brain`, один для `src.notifier.bot_handler` (у них разные наборы запрещённых целей: бот-обработчик живёт внутри `src.notifier`, и общий запрет `src.notifier` ложно сработал бы на его собственные соседние модули).
**When to use:** `.importlinter` в корне `/opt/assistant-core`, запуск `lint-imports --no-logo --no-cache` из корня.
**Example:**
```ini
# Source: проверено запуском import-linter 2.15 на /opt/assistant-core (exit 0; "2 kept, 0 broken");
# опции — [CITED: import-linter.readthedocs.io/en/stable/contract_types/ , .../get_started/configure/]
[importlinter]
# ВАЖНО: src.connectors и src.sender — namespace-каталоги без __init__.py; без их "порций"
# grimp их не видит и контракт молча проходит (см. Pitfall 1).
root_packages =
    src
    src.connectors
    src.sender
include_external_packages = False

[importlinter:contract:brain-no-adapters]
name = use-cases (brain) не импортируют адаптеры
type = forbidden
source_modules =
    src.brain
forbidden_modules =
    src.connectors
    src.calendar
    src.parser
    src.sender
    src.collector
    src.notifier
# Считаем только прямые импорты: иначе цепочки через чужие модули (bot_handler -> live_ticker -> connectors)
# потребуют дублировать ignore в каждом контракте и тянут в Фазу 2 рефакторинг live_ticker, которого в PRT-04 нет.
allow_indirect_imports = True
ignore_imports =
    # долг, только убывает: inline-импорт внутри функции (secretary_dialog.py:139), уберёт Фаза 2 (PRT-04)
    src.brain.secretary_dialog -> src.connectors.aadhk.parser

[importlinter:contract:bot-handler-no-adapters]
name = bot_handler не импортирует адаптеры
type = forbidden
source_modules =
    src.notifier.bot_handler
forbidden_modules =
    src.connectors
    src.calendar
    src.parser
    src.sender
    src.collector
allow_indirect_imports = True
ignore_imports =
    # долг, только убывает: inline-импорты bot_handler.py:1052,1095,1144, уберёт Фаза 2 (PRT-04)
    src.notifier.bot_handler -> src.connectors.aadhk.parser
    # долг, только убывает: inline-импорт bot_handler.py:1143
    src.notifier.bot_handler -> src.connectors.gdrive.client
    # долг, только убывает: top-level импорт bot_handler.py:23
    src.notifier.bot_handler -> src.connectors.guap_lms.client
    # долг, только убывает: top-level импорт bot_handler.py:22
    src.notifier.bot_handler -> src.sender.email_sender
```

**Фактический перечень нарушений на HEAD `6e0850b`** (grimp + `lint-imports`, номера строк из вывода):

| # | Источник → цель | Строки | Вид |
|---|-----------------|--------|-----|
| 1 | `src.brain.secretary_dialog` → `src.connectors.aadhk.parser` | 139 | inline (внутри функции) |
| 2 | `src.notifier.bot_handler` → `src.connectors.aadhk.parser` | 1052, 1095, 1144 | inline |
| 3 | `src.notifier.bot_handler` → `src.connectors.gdrive.client` | 1143 | inline |
| 4 | `src.notifier.bot_handler` → `src.connectors.guap_lms.client` | 23 | top-level |
| 5 | `src.notifier.bot_handler` → `src.sender.email_sender` | 22 | top-level |

То есть вопреки ROADMAP («inline-импорты») два из пяти — обычные импорты верхнего уровня. Дополнительно, вне контракта и вне `ignore_imports`: `src.notifier.live_ticker` → `src.connectors.aadhk.parser` (115, inline). Это адаптер-к-адаптеру (оба в слоях «адаптер» по ROADMAP), контрактом D-08 не охватывается; в BASELINE записать как известный незащищённый долг для решения в Фазе 2. Остальные импорты `src.brain` и `bot_handler` (в `src.config`, `src.models.*`, `src.storage.db`, соседние `src.brain.*`, `src.notifier.telegram|live_ticker`) контракт не запрещает [VERIFIED: grimp, перечень импортов].

`src.brain` сегодня НЕ импортирует `src.calendar`, `src.parser`, `src.collector`, `src.notifier` — эти запреты защищают от появления связи (как и D-09) и контракт на них проходит.

### Pattern 2: Контракт chat-app

**What:** запрет импорта `src` пакетом `app`; `app.core` — namespace-каталог (нет `__init__.py`), поэтому `root_packages` с порцией.
```ini
# Source: проверено на копии chat-app: без нарушения "1 kept"; при добавленной строке `from src.config import TZ`
# в app/db.py и в app/core/config.py — "BROKEN", exit 1.
[importlinter]
root_packages =
    app
    app.core
include_external_packages = True

[importlinter:contract:app-no-assistant-core]
name = backend chat-app не импортирует внутренние модули assistant-core
type = forbidden
source_modules =
    app
forbidden_modules =
    src
```
`src` должен быть установлен или доступен на пути — НЕ требуется: внешний пакет определяется по самому оператору импорта [VERIFIED: в `.venv` chat-app `src` отсутствует, нарушение всё равно поймано].

**Запуск chat-app:** `lint-imports` кладёт в `sys.path` только текущий каталог (`importlinter/cli.py:147-149`), а пакет `app` лежит в `backend/`. Из корня репозитория без `PYTHONPATH` результат: `Could not find package 'app' in your Python path.` (exit 1) [VERIFIED: запуск]. Решение при `.importlinter` в корне (D-07): запускать `PYTHONPATH=backend lint-imports --no-logo --no-cache` с `cwd=/opt/chat-app`. Альтернатива — положить конфиг в `backend/` и запускать с `cwd=backend`; противоречит D-07, не рекомендуется.

### Pattern 3: Тест «контракт падает на нарушении» (D-11)

**What:** pytest создаёт в `tmp_path` синтетический пакет `synthpkg` с контрактом той же формы (forbidden, inline-импорт запрещённого модуля), запускает `lint-imports` подпроцессом и проверяет код возврата 1; во втором тесте — чистый пакет, код 0. Прототип проверен: нарушение → exit 1 с сообщением `synthpkg.brain.uc -> synthpkg.connectors.gw (l.2)`, чистый пакет → exit 0.
```python
# Source: прототип, выполнен с import-linter 2.15
import subprocess, sys, textwrap
from pathlib import Path

LINT = Path(sys.executable).parent / "lint-imports"   # НЕ .resolve(): иначе уйдём из venv

CONTRACT = """\
[importlinter]
root_package = synthpkg

[importlinter:contract:c]
name = brain not adapters
type = forbidden
source_modules =
    synthpkg.brain
forbidden_modules =
    synthpkg.connectors
"""

def _build(tmp: Path, violate: bool) -> None:
    for d in ("synthpkg", "synthpkg/brain", "synthpkg/connectors"):
        (tmp / d).mkdir(parents=True, exist_ok=True)
        (tmp / d / "__init__.py").write_text("")
    (tmp / "synthpkg/connectors/gw.py").write_text("X = 1\n")
    body = "from synthpkg.connectors.gw import X\n    return X\n" if violate else "return 1\n"
    (tmp / "synthpkg/brain/uc.py").write_text("def f():\n    " + body)
    (tmp / ".importlinter").write_text(CONTRACT)

def _run(tmp: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(LINT), "--no-logo", "--no-cache"], cwd=tmp, capture_output=True, text=True, timeout=60)

def test_contract_fails_on_intentional_violation(tmp_path):
    _build(tmp_path, violate=True)
    r = _run(tmp_path)
    assert r.returncode != 0 and "BROKEN" in r.stdout

def test_contract_passes_on_clean_package(tmp_path):
    _build(tmp_path, violate=False)
    assert _run(tmp_path).returncode == 0
```
Тест не зависит от реального кода репозитория. Подпроцесс наследует окружение: имя `synthpkg` не пересекается с `app`/`src`.

**Страж против «пустого» контракта (рекомендуется, не заменяет D-11):** отдельный тест читает реальный `.importlinter` через `configparser`, строит граф `grimp.build_graph(*root_packages, include_external_packages=...)` и проверяет, что каждый внутренний модуль из `source_modules`, `forbidden_modules` и из обеих сторон `ignore_imports` присутствует в `graph.modules`. Причина: import-linter 2.15 НЕ ругается на несуществующий запрещённый модуль (проверено: добавленный в `forbidden_modules` несуществующий `src.doesnotexist` дал «KEPT», exit 0). Тест ловит опечатки и потерю порций namespace-пакетов. Для chat-app внешний запрещённый модуль `src` пропускать (его в графе нет).

### Pattern 4: Конструкция гейта

**What:** `scripts/gate.py`, stdlib-only. Скелет (имена функций — на усмотрение планировщика):
```python
# Source: проектный набросок; все вызываемые команды проверены на этой машине
import hashlib, os, shutil, sqlite3, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

CHAT = Path("/opt/chat-app")
CORE = Path(os.environ.get("ASSISTANT_CORE_DIR", "/opt/assistant-core"))   # D-01
LIVE_DB = CORE / "data" / "assistant.db"

def sha256(p: Path) -> str: ...
def make_db_copy(tmp: Path) -> Path:               # <- единственная точка замены в Фазе 4 (DAT-04)
    dst = tmp / "assistant-copy.db"
    src = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    out = sqlite3.connect(dst); src.backup(out); out.close(); src.close()
    return dst

def run(cmd, cwd, env_extra=None, timeout=900):   # список аргументов, shell=False всегда
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)

def pytest_counts(junit_xml: Path) -> dict: ...    # tests/failures/errors/skipped из <testsuite>
# Красим, если: код != 0, или failures/errors > 0, или skipped > 0, или tests == 0 (код 5 «ничего не собрано»)
```
Конкретные команды (все проверены):
- chat-app pytest: `[CHAT/"backend/.venv/bin/pytest", "backend/tests", "-p", "no:cacheprovider", f"--junitxml={xml}"]`, `cwd=CHAT`, env `SQLITE_DB_PATH=<копия>`.
- assistant-core pytest: `[CORE/".venv/bin/pytest", str(CORE/"tests"), "-p", "no:cacheprovider", f"--junitxml={xml}"]`, `cwd=CORE` (cwd важен: тесты создают относительный каталог, см. Pitfall 5).
- lint-imports chat-app: `[CHAT/"backend/.venv/bin/lint-imports", "--no-logo", "--no-cache"]`, `cwd=CHAT`, env `PYTHONPATH=backend`.
- lint-imports assistant-core: `[CORE/".venv/bin/lint-imports", "--no-logo", "--no-cache"]`, `cwd=CORE`.
- shield: `[CORE/".venv/bin/python3", str(repo/"scripts/security_shield.py"), str(repo), "--all"]` или без `--all` — см. Open Questions №1.
- Вывод шагов в консоль не печатать целиком (shield печатает remote и e-mail автора git: в таблицу гейта и в BASELINE/сырые выводы они попадать не должны — требование сквозного критерия №7).
- Если `lint-imports`/`pytest` отсутствуют — красный шаг с понятным русским сообщением («не установлен dev-зависимость, см. requirements-dev.txt»), а не traceback.
- Временный каталог удалять в `finally` (в нём копия боевой БД и junit-файлы).
- `--basetemp=<tmp>/pytest-core` для assistant-core (рекомендуется): тогда архив `server_backup_*.tar.gz` с копией `.env` и сессии, который создаёт `test_gdrive_client`, удаляется вместе с каталогом гейта, а не остаётся в `/tmp/pytest-of-root`. Это добавка флага к документированной команде, смысл теста не меняется.

Время полного гейта ≈ 50–60 с, память приемлема для 2 ГБ (assistant-core pytest — самый тяжёлый; параллельный запуск двух pytest не делать).

### Pattern 5: Синтетическая персона (набросок полей)

Ключи — по значениям, которые реально зашиты сегодня (CONCERNS.md, `security.py`, `config.py`, `calendar/client.py`, `live_ticker.py`, `db.py`) и по форме blueprint §3.1; схему `persona.yaml` НЕ предвосхищать (D-12). Все значения вымышленные; e-mail, телефоны и токены в файл не класть.
```python
# Source: проектный набросок; формы значений сверены с blueprint §3.1 и CONCERNS.md
SYNTHETIC_PERSONA = {
    "id": "synthetic-test-persona",
    "display_name": "Тестовый Тест Тестович",
    "honorific": "тестовый наставник",
    "organizations": {"university": "Тестовый университет Альфа", "company": "Тестовая компания Бета"},
    "telegram": {"authorized_user_id": 100000001, "bot_username": "synthetic_test_bot"},  # без двоеточия и 35 знаков — не токен
    "workspaces": [   # все три clearance
        {"id": "synthetic-public",   "label": "Синтетический открытый проект", "path": "/synthetic/public",
         "clearance": "public", "forbidden_remote_substrings": [], "forbidden_keywords": []},
        {"id": "synthetic-internal", "label": "Синтетическая кафедра",         "path": "/synthetic/internal",
         "clearance": "internal", "forbidden_remote_substrings": [], "forbidden_keywords": []},
        {"id": "synthetic-nda",      "label": "Синтетическая закрытая работа", "path": "/synthetic/nda",
         "clearance": "restricted_nda",
         "forbidden_remote_substrings": ["git.synthetic.example/forbidden"],
         "forbidden_keywords": ["synthetic_marker_alpha", "synthetic_marker_beta"]},
    ],
    "timesheet": {"default_project": "Синтетический проект учёта", "daily_norm_hours": 6.0},
    "schedule_source": {"base_url": "https://schedule.synthetic.example/"},
    "lms": {"base_url": "https://lms.synthetic.example/"},
    "default_area": "Синтетическая область",
    "subjects": {"синтетическая физика": "СинтФиз"},   # короткие названия предметов
    "lesson_slots": {1: ("09:00", "10:30")},          # слоты расписания
}
```
Ограничения на значения, продиктованные сканерами секретов (см. Pitfall 4): не использовать имена ключей `api_key`/`secret_key`/`auth_token` со значением из 16+ букв/цифр в кавычках; не использовать три реальных NDA-ключевых слова из `CORPORATE_NDA_KEYWORDS` (их собственные синтетические аналоги — как выше); числовые идентификаторы — целые, не строки вида `цифры:длинная_строка`.

Фикстура: `conftest.py` с `@pytest.fixture def synthetic_persona(): return copy.deepcopy(SYNTHETIC_PERSONA)` (глубокая копия, чтобы тест не мутировал общий словарь). Импорт — относительный: `from .synthetic_persona import SYNTHETIC_PERSONA` (в обоих наборах каталог тестов — пакет с `__init__.py`, а в chat-app `app` находится через rootdir-вставку `backend/` в `sys.path`).

Тесты каркаса (D-14), все синхронные и зелёные сегодня:
1. фикстура грузится и возвращает `dict`;
2. все ключи идентифицирующих полей присутствуют, значения непусты (рекурсивный обход);
3. ни одна строка (рекурсивно, без учёта регистра) не содержит токенов из ОДНОЙ константы `OWNER_TOKEN_DENYLIST` (`ГУАП`, `GUAP`, `Тидекс`, `Tydex`, части ФИО — Попов/Дмитр…, личный git-аккаунт);
4. каждое идентифицирующее поле отличается от значения, зашитого сегодня (константа `CURRENT_HARDCODED_DEFAULTS` в тесте: ФИО, `Тидекс`, 8.5, `https://guap.ru/rasp`, `https://pro.guap.ru`, пути `/opt/work-tydex`, `/opt/personal/guap-physics`, id четырёх рабочих пространств…);
5. множество значений clearance всех рабочих пространств равно ровно `{"public", "internal", "restricted_nda"}` и других нет;
6. (рекомендуется) пути рабочих пространств лежат под `/synthetic/`, домены оканчиваются на `.example`.

Список «Ожидают Фазы 3» (D-15; в `docs/BASELINE.md` и в докстринге `synthetic_persona.py`, без skip/xfail) — предложение:
1. PER-01: загрузка персоны из `config/persona.yaml` + Pydantic-валидация; персона по умолчанию без `PERSONA_CONFIG_PATH`.
2. PER-02: персона записывается в `personas`/`workspaces`/`connector_bindings`; несколько привязок на роль.
3. PER-03/PER-04: `/api/v1/security/overview` и аудит строятся из рабочих пространств персоны (3 clearance), NDA-проверки воспроизводятся из данных без ослабления.
4. PER-05: веб-дефолты области и белая метка из `/api/v1/persona/current`.
5. PER-06: параметры коннекторов (проект учёта, норма часов, адреса, предметы/слоты) читаются из персоны.
6. PER-07/BCK-02: промпты секретаря/маршрутизатора/методиста рендерятся из шаблонов с этой персоной и отличаются от дефолтных; тесты хардкода переписаны на загруженную персону.
7. PER-08: сканер хардкода не находит токены владельца вне allowlist; denylist теста заменяется данными персоны по умолчанию.
8. PER-09: `test_persona_config.py` — те же кодовые пути дают для синтетической персоны иные промпты, список пространств, дефолты и scope-решения.

### Anti-Patterns to Avoid
- **Наивный `forbidden`-контракт без порций namespace-пакетов** — молча «KEPT» (Pitfall 1).
- **Инлайн-комментарий в строке `ignore_imports`** (`a -> b  # коммент`) — ломает парсинг: `not a valid import expression`, exit 1 [VERIFIED]. Комментарий — отдельной полной строкой выше записи (проверено: так работает).
- **Передавать `DATABASE_URL` в assistant-core pytest «для галочки»** — не действует (Pitfall 3), создаёт ложное чувство защиты.
- **Запускать `security_shield.py` без `--all` в гейте и считать это проверкой** — на чистом дереве он ничего не сканирует.
- **`xfail`/`skip` для проверок Фазы 3** — запрещено D-15; проверки перечисляются текстом.
- **Печатать/сохранять вывод shield целиком** — он содержит remote и e-mail автора.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Проверка «слой A не импортирует слой B» | AST-сканер импортов в pytest | `import-linter` (`forbidden`) | Учитывает inline-импорты, цепочки, wildcard-игнор, ошибку на устаревшей записи игнора |
| Перечень реальных нарушений | grep по `import` | `grimp.build_graph(...)` / вывод `lint-imports` | grep не отличает inline/relative-импорты и не даёт номера строк надёжно |
| Копия SQLite-БД | `shutil.copy` файла БД | `sqlite3.Connection.backup()` | Консистентный снимок, не ломает при незавершённой записи/WAL |
| Подсчёт результатов pytest | regex по произвольному выводу | `--junitxml` + `xml.etree` | Точные счётчики `tests/failures/errors/skipped` |
| Временные каталоги | ручные пути в `/tmp` | `tempfile.mkdtemp()` + `finally: shutil.rmtree` | Права 0700, нет остатков с копией БД |
| Хеширование | своя контрольная сумма | `hashlib.sha256` | Стандарт, D-03/D-16 |

**Key insight:** в этой фазе нет ничего, что стоило бы писать «с нуля» кроме тонкой оркестрации (гейт); вся ценность — в корректной настройке готовых инструментов и в недоверии к их «зелёному» результату (пустой контракт, пустой shield).

## Common Pitfalls

### Pitfall 1: Контракт молча «ничего не проверяет» (namespace-пакеты)
**What goes wrong:** `lint-imports` с наивным конфигом D-08 печатает «KEPT, 1 kept, 0 broken» при пяти реальных нарушениях; на несуществующий запрещённый модуль не реагирует.
**Why it happens:** `src/connectors/`, `src/sender/` (assistant-core) и `app/core/` (chat-app) — каталоги без `__init__.py`; grimp не включает их в граф (в графе 33 модуля вместо 45), импорты внутрь них отбрасываются. Контракт «forbidden» не проверяет существование модулей [VERIFIED: запуски на копиях].
**How to avoid:** `root_packages` с «порциями» (`src`, `src.connectors`, `src.sender`; `app`, `app.core`) — документированный приём: «in the special case of namespace packages, the name of the portion may be supplied» [CITED: import-linter.readthedocs.io/en/stable/get_started/configure/]; плюс тест-страж Pattern 3. Добавление пустых `__init__.py` тоже решило бы проблему (проверено на копии), но это правка продакшен-дерева вне списка допустимого критерием 5 — не делать без решения владельца.
**Warning signs:** «Analyzed 33 files» вместо 45; «KEPT» без строки «ignored imports» у контракта, в котором известны нарушения.

### Pitfall 2: Устаревшая запись `ignore_imports` — это красное, и это хорошо
**What goes wrong:** когда Фаза 2 уберёт импорт, а запись останется, `lint-imports` падает: `No matches for ignored import …` (exit 1) [VERIFIED].
**How to avoid:** это штатный механизм «долг только убывает»: удалять запись в том же коммите, что и рефакторинг. Прирост списка механически НЕ блокируется — только ревью; при желании добавить в тест-страж проверку `len(ignore_imports) <= 5` (убывающая верхняя граница), на усмотрение планировщика.

### Pitfall 3: Окружение не перебивает `.env` в assistant-core
**What goes wrong:** `DATABASE_URL` из окружения игнорируется (`load_dotenv(override=True)`).
**How to avoid:** см. «Защита боевой БД»; хеш-контроль вместо переопределения; в BASELINE зафиксировать как наблюдение для Фазы 4 (DAT-02).

### Pitfall 4: Новые файлы могут покраснить существующий тест chat-app и shield
**What goes wrong:** `test_security_audit_all` (chat-app) требует `data["status"] == "passed"` и `audited_count == 4`; он выполняет `git ls-files` в `/opt/chat-app` И `/opt/assistant-core` (первые 100 файлов) и ищет `SECRET_PATTERNS` (6 регулярок, `security.py:15-22`) и `FORBIDDEN_FILES` [VERIFIED: чтение `security.py` и теста]. Файлы, которые Фаза 1 добавит в assistant-core, проверяются тестом chat-app. `security_shield.py` добавляет ещё `Generic Bearer Secret` (`api_key|secret_key|auth_token = '…16+ символов…'`) и три NDA-ключевых слова в «публичных» репозиториях.
**How to avoid:** в персоне, тестах, BASELINE и сырых выводах — никаких строк, похожих на ключи/токены; не называть значения `api_key=`/`secret_key=`/`auth_token=` с длинными литералами; не цитировать три реальных NDA-слова (ни в `docs/`, ни в `.planning/`). Прогнать гейт и `pytest backend/tests` ПОСЛЕ добавления каждого нового файла. Не добавлять файлы с именами `*.key`, `*.pem`, `token.json`, `.env*`.
**Warning signs:** красный `test_security_audit_all` сразу после коммита нового файла.

### Pitfall 5: Загрязнение рабочего каталога и временных каталогов тестами assistant-core
**What goes wrong:** три набора (`test_live_ticker.py:121`, `test_hitl_safety_guardrails.py:12`, `test_bot_menu.py:13`) передают `Database(f"sqlite+aiosqlite:///{db_file}")` как путь, и в текущем каталоге появляется настоящий каталог `sqlite+aiosqlite:` (в корне assistant-core уже лежит такой, 61 → 70 файлов за один прогон; он игнорируется git по правилу `data/`). `test_gdrive_client` оставляет архив с копией `.env` и сессии в `/tmp/pytest-of-root`.
**How to avoid:** всегда `cwd=/opt/assistant-core` для pytest assistant-core (мусор остаётся в известном игнорируемом месте); `--basetemp` во временный каталог гейта; в BASELINE записать как наблюдение (не чинить: код тестов не в объёме Фазы 1, а смысл ассертов трогать нельзя).

### Pitfall 6: Кэш import-linter и pytest в репозитории
**What goes wrong:** `lint-imports` без `--no-cache` создаёт каталог кэша (`.import_linter_cache`) в `cwd`; pytest — `.pytest_cache` (последний уже в `.gitignore` обоих репозиториев).
**How to avoid:** гейт передаёт `--no-cache`; добавить `.import_linter_cache/` в `.gitignore` обоих репозиториев на случай ручного запуска (это конфигурация, не логика; решение планировщика). Использование `-p no:cacheprovider` в гейте сохраняет дерево чистым.

### Pitfall 7: Relative-импорт против путей в двух наборах
**What goes wrong:** `from tests.synthetic_persona import …` в одном наборе работает, в другом — нет (в chat-app rootdir-вставка добавляет `backend/`, в assistant-core — корень репозитория через `pythonpath = .`).
**How to avoid:** относительный импорт `from .synthetic_persona import …` из `conftest.py` и тестов — работает в обоих (оба каталога — пакеты с `__init__.py`; `backend/tests/__init__.py` существует).

### Pitfall 8: `lint-imports` из venv
**What goes wrong:** в тесте D-11 вызов `lint-imports` по `PATH` берёт чужой исполняемый файл или не находит.
**How to avoid:** `Path(sys.executable).parent / "lint-imports"` (без `.resolve()`: симлинк `.venv/bin/python` ведёт на системный `/usr/bin/python3`, и после `resolve()` каталог `bin` уже не venv'а). Если файла нет — тест падает с понятным сообщением, а не пропускается.

## Code Examples

### Разбор результата pytest из junitxml
```python
# Source: stdlib xml.etree; формат junitxml pytest
def pytest_counts(xml_path):
    root = ET.parse(xml_path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return {k: int(suite.get(k, 0)) for k in ("tests", "failures", "errors", "skipped")}
```

### Таблица итога (формат на усмотрение; пример)
```
Репозиторий       Проверка                 Результат
chat-app          pytest (14 тестов)       ✓
chat-app          import-linter            ✓
chat-app          security_shield          ✓
assistant-core    pytest (127 тестов)      ✓
assistant-core    import-linter            ✓
assistant-core    security_shield          ✓
оба               персона (дрейф SHA-256)  ✓
оба               боевая БД не изменена    ✓
ИТОГ: ЗЕЛЁНЫЙ
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| «CI зелёный» во внешнем CI | локальный скрипт-гейт (решение владельца) | 2026-10-01 | Нет внешнего сервиса, новые сервисы запрещены |
| Один `root_package` | `root_packages` с порциями namespace-пакетов | документировано в import-linter | Единственный способ видеть namespace-каталоги без правки дерева |

**Deprecated/outdated:** ничего критичного; import-linter 2.15 (2026-09-04) — актуальная версия на дату исследования.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Зарезервированный домен верхнего уровня `.example` (RFC 2606) подходит для вымышленных адресов | Pattern 5 | Низкий: домен используется только как строка в данных теста, сети не касается |
| A2 | `/opt/assistant-core/.env` содержит `DATABASE_URL` (вывод из эксперимента с приоритетом, сам файл не читался) | Защита боевой БД | Низкий: вывод «переопределение окружением не действует» подтверждён экспериментом независимо от причины |
| A3 | Режим `--all` + замороженный список известных ложных срабатываний — лучший способ включить `security_shield.py` в гейт | Open Questions №1 | Средний: решение по политике безопасности; ждёт владельца |
| A4 | Файлы `scripts/security_shield.py` в обоих репозиториях остаются как есть (D-01) | Pattern 4 | Низкий |
| A5 | Размеры/время (≈50–60 с, память) укладываются в 2 ГБ при последовательном запуске | Pattern 4 | Низкий: оба прогона выполнены на этой машине при свободной памяти ≈1 ГБ |

## Open Questions

1. **Как гейт должен запускать `security_shield.py`? (нужно решение владельца)**
   - Что известно: [VERIFIED: запуск] без `--all` скрипт сканирует только индексированные/изменённые файлы (`git diff --cached`, затем `git diff`); на чистом дереве обоих репозиториев он пишет «No staged or modified files found to scan» и возвращает 0 — то есть проверка ничего не проверяет, а результат зависит от состояния рабочего дерева; неотслеживаемые (untracked) файлы не сканируются никогда. С `--all` (все `git ls-files`) оба репозитория дают код 1: chat-app — 6 находок (3 ключевых слова в строке 250 `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md`, три — в собственном списке ключевых слов `scripts/security_shield.py`, строки 39–41), assistant-core — 9 находок (те же 3 в `scripts/security_shield.py` и 6 срабатываний `Generic Bearer Secret` на фиктивные ключи в тестах: `test_debrief_parser.py:16,50`, `test_notion_client.py:53`, `test_voice.py:22,46,101`). Все 15 — ложные срабатывания эвристик (определения самого списка слов, пример конфигурации в blueprint, учебные значения в тестах), реальных секретов не найдено; значения при проверке маскировались.
   - Что неясно: считать ли это корзиной (в) по D-17 (вынести владельцу) или принять замороженный baseline.
   - Рекомендация: **вариант Б (рекомендуется)** — гейт запускает `--all` и сравнивает находки с замороженным списком «известные ложные срабатывания» в `gate.py` (ключ — относительный путь + текст находки без номера строки; 15 записей; новая находка или сбой запуска — красный; запись можно только удалять) — полностью аналогично `ignore_imports`, сам скрипт и ассерты не меняются. **Вариант А (запасной)** — гейт запускает режим по умолчанию (семантика pre-commit: проверяет то, что вот-вот попадёт в коммит), а `--all`-находки только записываются в BASELINE; проще, но гейт на чистом дереве зелёный «по умолчанию». Планировщику — заложить в плане чекпойнт «решение владельца» до реализации шага shield; пока решения нет, реализовывать вариант Б и вынести его в итог плана.

2. **Пустые `__init__.py` в `src/connectors`, `src/sender`, `app/core` — добавлять ли?**
   - Что известно: убрали бы потребность в порциях `root_packages` (проверено на копии); но это изменение продакшен-дерева, а критерий 5 разрешает только конфигурацию линтера, гейт, каркас и baseline.
   - Рекомендация: в Фазе 1 НЕ добавлять; использовать порции + страж-тест; предложить владельцу/Фазе 2 как отдельное решение.

3. **Что делать с `live_ticker → connectors`?** Известное нарушение вне контракта D-08; решение (расширить контракт на `live_ticker` либо оставить) — к обсуждению Фазы 2; в Фазе 1 только зафиксировать в BASELINE.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 (системный) | `scripts/gate.py`, shield | ✓ | 3.12.3 | — |
| `/opt/chat-app/backend/.venv` (pytest, pytest 9.1.1, anyio) | chat-app pytest | ✓ | Python 3.12.3 | — |
| `/opt/assistant-core/.venv` (pytest, pytest-asyncio 1.4.0) | assistant-core pytest | ✓ | Python 3.12.3 | — |
| `lint-imports` в обоих `.venv` | FND-02, гейт | ✗ (не установлен) | устанавливается 2.15 | нет: ставится `pip install` (сеть доступна, сухой прогон прошёл) — шаг с чекпойнтом человека из-за вердикта SUS |
| `sqlite3` (stdlib) | копия БД | ✓ | входит в Python | — |
| git | shield | ✓ | — | — |
| Доступ к PyPI | установка import-linter | ✓ | — | — |
| systemd-сервисы | не требуются (должны оставаться остановленными) | остановлены | chat-app inactive, assistant-worker failed, dev-bridge inactive | не включать |
| `/opt/work-tydex`, `/opt/personal/guap-physics` | тесты chat-app (Security Tile) | ✗ отсутствуют | — | тесты проходят: аудит возвращает «virtual_airgap» для отсутствующих каталогов; ничего создавать не нужно |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `lint-imports` — установить в оба `.venv` (после подтверждения владельцем из-за SUS).

## Validation Architecture

`.planning/config.json` отсутствует — раздел включён по умолчанию.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (chat-app: плагин anyio 4.15.1; assistant-core: pytest-asyncio 1.4.0, `asyncio_mode = auto`) |
| Config file | chat-app: нет (`rootdir=/opt/chat-app`); assistant-core: `/opt/assistant-core/pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`, `pythonpath = .`) |
| Quick run command | chat-app: `cd /opt/chat-app && SQLITE_DB_PATH=<копия> backend/.venv/bin/pytest backend/tests/test_synthetic_persona.py backend/tests/test_architecture_contract.py -q`; assistant-core: `cd /opt/assistant-core && .venv/bin/pytest tests/test_synthetic_persona.py tests/test_architecture_contract.py -q` (новые тесты не используют БД) |
| Full suite command | `python3 /opt/chat-app/scripts/gate.py` (после появления гейта); до этого — две документированные команды из CLAUDE.md |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FND-01 | оба pytest зелёные; число тестов 14 и 127 зафиксировано; боевая БД не изменена | gate + документ | `python3 /opt/chat-app/scripts/gate.py` (шаги «pytest» и «БД не изменена») ; сверка `docs/BASELINE.md` с выводом | ❌ Wave 0 (`gate.py`, `BASELINE.md`) |
| FND-02 | реальный контракт зелёный на текущем коде | gate | `lint-imports --no-logo --no-cache` в каждом репозитории (chat-app с `PYTHONPATH=backend`) | ❌ Wave 0 (`.importlinter`) |
| FND-02 | контракт падает на нарушении; на чистом пакете зелёный | unit | `…/pytest backend/tests/test_architecture_contract.py -q` / `tests/test_architecture_contract.py -q` | ❌ Wave 0 |
| FND-02 | контракт не «пустой» (все модули контракта есть в графе) | unit | тот же файл, тест-страж | ❌ Wave 0 |
| FND-02 | разовая ручная проверка на реальном коде: временно убрать одну запись `ignore_imports` → красный → вернуть (записать в SUMMARY) | manual | `lint-imports` до/после правки конфига | — |
| FND-03 | фикстура грузится; поля непусты; нет токенов владельца; отличается от дефолта; ровно 3 clearance | unit | `…/pytest …/test_synthetic_persona.py -q` в обоих наборах | ❌ Wave 0 |
| FND-03 | две копии `synthetic_persona.py` идентичны | gate | шаг «дрейф» гейта (SHA-256) | ❌ Wave 0 |
| FND-04 | гейт даёт итог «ЗЕЛЁНЫЙ» на зелёном состоянии, «КРАСНЫЙ» при красном шаге, код возврата 0/1 | unit (чистые функции) + manual | `…/pytest backend/tests/test_gate.py -q`; ручная демонстрация красного (например `ASSISTANT_CORE_DIR=/nonexistent`) | ❌ Wave 0 |
| FND-04 | правило «100% pytest/атомарный коммит/revert» записано | doc check | `grep -c "Правила" docs/BASELINE.md` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** быстрые тесты нового файла + соответствующий шаг гейта.
- **Per wave merge:** полный гейт (≈1 мин).
- **Phase gate:** полный гейт «ЗЕЛЁНЫЙ», `git status` обоих репозиториев чист (кроме запланированных коммитов), хеш боевой БД равен `baef14f7…`, `git diff` не затрагивает продакшен-код (`backend/app`, `src`).

### Wave 0 Gaps
- [ ] `/opt/chat-app/scripts/gate.py`, `/opt/chat-app/docs/BASELINE.md`, `/opt/chat-app/docs/baseline/*.txt`
- [ ] `.importlinter` и `requirements-dev.txt` в обоих репозиториях; установка `import-linter` в оба `.venv` (чекпойнт человека)
- [ ] `backend/tests/{conftest.py, synthetic_persona.py, test_synthetic_persona.py, test_architecture_contract.py}` и `tests/{…}` в assistant-core
- [ ] (рекомендуется) `backend/tests/test_gate.py` — чистые функции: агрегирование итога, разбор вывода shield, сравнение хешей

## Security Domain

`security_enforcement` не отключён — раздел включён. Фаза не добавляет сетевых поверхностей; релевантны гигиена секретов и безопасный запуск подпроцессов.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (нет аутентификации в этой фазе) |
| V3 Session Management | no | — |
| V4 Access Control | no (но сохраняется air-gap: NDA-рабочие пространства в персоне только вымышленные) | — |
| V5 Input Validation | yes (ограниченно) | подпроцессы: список аргументов, `shell=False`, абсолютные пути, таймауты; разбор вывода shield — по строгому regex |
| V6 Cryptography | yes (ограниченно) | `hashlib.sha256` для контрольных сумм; ничего самописного |
| V14 Configuration / секреты | yes | не читать `.env`/`credentials.json`/`token.json`/`*.session`; временный каталог 0700 (`mkdtemp`) и удаление в `finally`; не сохранять в артефактах remote/e-mail из вывода shield |

### Known Threat Patterns for этого стека

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Утечка секретов/e-mail в артефакты (BASELINE, сырые выводы, RESEARCH/PLAN) | Information Disclosure | не включать вывод shield; фильтровать строки «Origin Remote»/«Author Email»; страж `--all`/`test_security_audit_all` после каждого нового файла |
| Копия боевой БД остаётся на диске | Information Disclosure | `mkdtemp` (0700) + удаление в `finally`; не класть копию в репозиторий |
| Копия `.env`/сессии в архиве `test_gdrive_client` в `/tmp` | Information Disclosure | `--basetemp` в каталог гейта с удалением; зафиксировать как наблюдение |
| Случайная запись в боевую БД | Tampering | копия + хеш до/после (SHA-256), красный итог при расхождении |
| Подмена гейта «зелёным» из-за пустого контракта/пустого shield | Repudiation / Tampering | страж-тест контракта; `--all` либо явное признание ограничения |
| Инъекция команд через путь/окружение | Tampering | `subprocess.run(list, shell=False)`; `ASSISTANT_CORE_DIR` — только путь, проверять существование |
| Установка подозрительного пакета | Tampering (supply chain) | чекпойнт `human-verify` для SUS-пакетов, версия закреплена в BASELINE |

## Рекомендуемое разбиение на планы (для планировщика)

1. **План 1 (волна 1): окружение и baseline.** Чекпойнт `human-verify` на установку `import-linter` (SUS) → `requirements-dev.txt` ×2 → установка в оба `.venv` → прогон обоих pytest (chat-app на копии), сырые выводы в `docs/baseline/`, каркас `docs/BASELINE.md` (числа 14/127, SHA 8d081d9/6e0850b на старте, версии).
2. **План 2 (волна 2, параллельно с 3): import-linter.** `.importlinter` ×2, `test_architecture_contract.py` ×2 (включая страж), ручная демонстрация красного, `.gitignore` для кэша; коммиты раздельные по репозиториям (D-19).
3. **План 3 (волна 2): синтетическая персона.** `synthetic_persona.py` + `conftest.py` + `test_synthetic_persona.py` ×2 (идентичные копии), список «Ожидают Фазы 3» в BASELINE и докстринге.
4. **План 4 (волна 3): гейт и документы.** `scripts/gate.py` (+ `test_gate.py`), шаг дрейфа SHA-256, чекпойнт решения по shield (Open Questions №1), раздел «Правила» в BASELINE, одна строка в CLAUDE.md (D-05, с пометкой в SUMMARY), финальный прогон гейта «ЗЕЛЁНЫЙ» с записью итогов и проверкой «продакшен-код не менялся» (`git diff --stat` по `backend/app` и `src`).

Все коммиты — атомарные; изменения assistant-core коммитятся в его репозиторий (ветка `main`), остальное — в chat-app (ветка `master`).

## Sources

### Primary (HIGH confidence)
- Фактические запуски на этой машине 2026-10-01: оба pytest (по два прогона), `lint-imports` 2.15 на копиях `src/` и `backend/app` (naive/multi/final/strict/stale/nonexistent/chat-app-варианты), `security_shield.py` с и без `--all`, `pip install --dry-run import-linter` в обоих `.venv`, `systemctl is-active`, проверка приоритета окружения над `.env` (без чтения `.env`).
- Чтение кода: `/opt/chat-app/backend/app/core/config.py`, `/opt/chat-app/backend/app/db.py:1-14`, `/opt/chat-app/backend/app/api/v1/security.py:1-120`, `/opt/chat-app/backend/tests/test_security_api.py`, `/opt/chat-app/scripts/security_shield.py`, `/opt/assistant-core/src/config.py`, `/opt/assistant-core/pytest.ini`, `/opt/assistant-core/src/connectors/gdrive/client.py:185-217`, `/opt/assistant-core/tests/*` (выборочно).
- [pypi.org/project/import-linter](https://pypi.org/project/import-linter/) — автор, версия 2.15, дата 2026-09-04, Python 3.10–3.14, лицензия.
- [import-linter.readthedocs.io/en/stable/contract_types/](https://import-linter.readthedocs.io/en/stable/contract_types/) — опции контракта `forbidden`, семантика и wildcard `ignore_imports`.
- [import-linter.readthedocs.io/en/stable/get_started/configure/](https://import-linter.readthedocs.io/en/stable/get_started/configure/) — `root_packages`, порции namespace-пакетов, `include_external_packages`, поиск `.importlinter`.

### Secondary (MEDIUM confidence)
- `gsd-tools query package-legitimacy check --ecosystem pypi import-linter grimp` — вердикт SUS (причины: `too-new`, `unknown-downloads`, `no-repository`).

### Tertiary (LOW confidence)
- Нет; единственное допущение из памяти — A1 (`.example` по RFC 2606).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — версии и состав зависимостей проверены `pip` и PyPI; пакет помечен SUS по метаданным сервиса, не по признакам подделки.
- Architecture: HIGH — контракты, их провалы и успехи воспроизведены запусками на копиях кода; прототип теста D-11 выполнен.
- Pitfalls: HIGH — каждая ловушка воспроизведена (namespace, `.env override`, shield, загрязнение каталогов, связь с `test_security_audit_all` подтверждена чтением кода; её срабатывание на новых файлах — логический вывод).
- Решение по shield: MEDIUM — зависит от владельца.

**Research date:** 2026-10-01
**Valid until:** 2026-10-31 (стабильные инструменты; перепроверить версию import-linter при установке)
