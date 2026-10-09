# Milestones

## v2.0 Универсальная платформа (Shipped: 2026-10-09)

**Phases completed:** 9 phases, 44 plans, 46 tasks

**Key accomplishments:**
- Stdlib-only `python3 scripts/gate.py` runs both pytest suites (chat-app on a sqlite3-backup copy of the live DB), hash-controls the live `assistant.db`, and prints a Russian table ending in ITOG: ZELENYJ/KRASNYJ; start baseline (14 + 127 passed) captured, import-linter 2.15 / grimp 3.17 installed after owner approval.
- Namespace-aware import-linter contracts in both repos (assistant-core 2 kept / 5 debt entries, chat-app 1 kept / 0 debt) with tests that prove they fail on a deliberate violation, cannot be empty and cap the debt, wired into the gate as one row per repository.
- A second fictional persona (three workspaces, one per clearance level) with a deepcopy fixture and seven green scaffold tests in both repositories, kept identical by a SHA-256 drift row in the quality gate, with the eight Phase 3 checks listed as text only.
- One command `python3 scripts/gate.py` now runs both pytest suites (68 + 139 tests), both import-linter contracts, `security_shield --all` in both repos against a frozen list of 15 known false positives, the persona drift check and the live-DB hash check, and prints «ИТОГ: ЗЕЛЁНЫЙ» (rc 0)
- Вопрос о табеле идёт через Protocol-порт BaseTimesheetProvider, адаптер AadhkTimesheetProvider и корень композиции src/composition.py; ядро src/core защищено контрактом core-is-pure, долг ignore_imports снижен с 5 до 4, поведение секретаря закреплено тестом, написанным до правки.
- Три async-порта (BaseScheduleProvider, BaseCalendarSink, BaseLMSProvider) с адаптерами поверх неизменённых клиентов, пометка REQUIRES_CONFIRMATION для submit_grade и delete_task, DI-протоколы клиентов бота и единый conformance-тест всех четырёх пар порт - адаптер с проверкой разделения ролей.
- EmailBotHandler получает клиент ЛК, отправщик почты, сервис табеля и фабрику Google Drive через конструктор (значения по умолчанию собирает src.composition), поведение трёх непокрытых путей бота заморожено характеризационными тестами, закоммиченными до рефакторинга, долг ignore_imports равен 0, import-linter: 3 kept, 0 broken.
- LiveTickerService получает сервис табеля через конструктор (контракт live-ticker-no-adapters без долга, lint-imports 4 kept, 0 broken), добавлены шесть неизменяемых доменных событий и внутрипроцессный EventBus на asyncio с изоляцией сбоя подписчика и без утечки содержимого события в журнал; фаза 2 принята: гейт «ИТОГ: ЗЕЛЁНЫЙ», 223 теста assistant-core.
- Побайтовые эталоны восьми системных промптов (секретарь, маршрутизатор, методист, проверка области, ответы на почту, дебриф, утренний и вечерний дайджест) закреплены в git и 11 тестами по месту вызова LLM до любой правки src/brain; пререквизит W10 выполнен.
- Персона popov-da-default проходит путь config/persona.yaml, Pydantic-загрузчик (safe_load, extra=forbid), таблицы personas/workspaces/connector_bindings из init_db(), seed-CLI, копия БД в тестах chat-app, DatabaseService и GET /api/v1/persona/current; боевая БД не тронута, гейт зелёный.
- Схема персоны утверждена целиком (4 рабочих пространства с NDA-правилами, 6 ролей коннекторов с несколькими привязками, Telegram только плейсхолдерами `${VAR}`, 6 областей задач, 7 текстов интерфейса, формы имени, каталог методиста), `config/persona.yaml` содержит все сегодняшние значения владельца, демон засевает персону в БД при старте, shield получил одно одобренное исключение (18 известных находок).
- `synthetic_to_config()` превращает словарь каркаса Фазы 1 в структуру `persona.yaml`, вторая персона засевается в БД тестов chat-app тем же seed-CLI, а `owner_tokens()` вычисляет токены профиля владельца из данных персоны; обе пары файлов под контролем гейта.
- Security Tile и Web-аудит строятся из таблицы `workspaces` персоны `settings.PERSONA_ID` (реестр-константа удалена, NDA-признак - `clearance`, подстроки remote и сообщение - данные пространства, без данных - 503), а явный NDA-чек-лист из 42 проверок на настоящих git-репозиториях закоммичен до правки и проходит после неё без изменения единой строки `assert`.
- `/api/v1/persona/current` отдаёт полный белый список (с `task_areas` и `ui.texts`), новые задачи и проекты без области получают `default_area` персоны (без персоны - 503), а `index.html` не содержит ни одного токена владельца и заполняется из API через `loadPersona`/`applyPersona` только через textContent и Option.
- Системные промпты секретаря, маршрутизатора и методиста (и проверка области методиста) стали Jinja2-шаблонами персоны, которые `render_prompt` рендерит в песочнице со `StrictUndefined`; для персоны по умолчанию текст совпадает с эталонами 03-01 байт в байт, Jinja2 3.1.6 и MarkupSafe 3.0.3 установлены с одобрения владельца.
- Промпты генератора ответов на почту, дебрифа, утреннего и вечернего дайджеста стали Jinja2-шаблонами персоны (даты и дни недели - переменные рендера, имя, титул и организации - данные персоны); для персоны по умолчанию текст совпадает с эталонами 03-01 побайтно, а синтетическая персона на тех же кодовых путях даёт 8 других промптов без токенов владельца.
- Проект учёта и норма часов, слоты пар и короткие названия предметов, адреса сайта расписания и личного кабинета, каталоги методиста, каталог файлов секретаря и правила области методиста читаются из привязок персоны в момент вызова (новый `src/persona/bindings.py`); для персоны по умолчанию значения и тексты прежние, синтетическая персона на тех же кодовых путях получает свои.
- Каркас второй персоны переключён с констант-копий профиля владельца на данные персоны по умолчанию, сканер хардкода с baseline, который может только сокращаться, стоит в обоих репозиториях, PER-09 доказан сводным `test_persona_config.py`, BASELINE фиксирует итог Фазы 3, отступления и порядок разморозки; гейт зелёный (assistant-core 326, chat-app 127).
- Создан локальный Python-пакет `/opt/assistant-shared` с легковесным SQL-мигратором и базовой миграцией `0001_initial_schema.sql`. Метод `init_db()` в `assistant-core/src/storage/db.py` отрефакторен с удалением 475 строк устаревшего ad-hoc DDL.
- Реализована единая фабрика соединений SQLite с WAL-режимом и защитой от блокировок `busy_timeout=5000`, подтверждена безопасность одновременной записи двух процессов, удален хардкод пути боевой базы, а набор тестов `chat-app` полностью изолирован от внешнего репозитория `assistant-core`.
- Фаза 4: общая библиотека безопасности `assistant-shared` (единые шаблоны секретов, NDA-правила, pre-commit hook); по итогам код-ревью исправлено 17 из 21 находки уровня Critical/Warning (04-REVIEW-FIX.md).
- Фаза 5: единый HITL-примитив `ConfirmationStore` / `pending_confirmations`; все DELETE chat-app без подтверждения отвечают 409, Telegram-карточки `hitl:*` и `resume_action`.
- Фаза 6: изоляция пула ключей Gemini по персоне (ContextVar), Air-Gap NDA-почты для LLM, Zero-Trust scopes коннекторов, тесты параллельной работы персон, ликвидация хардкода (HARDCODE_BASELINE пуст в обоих репозиториях).
- Фаза 7: компоненты Git-источников по SSH, оценки прогресса и Notion-синхронизации через HITL с обезличиванием NDA (без точки входа в рантайме — см. Known Gaps).
- Фаза 8: Function Calling секретаря (календарь, напоминания, черновики писем, поиск писем) со строгими HITL-карточками и буфером pending_sync.
- Фаза 9: динамический CommandRegistry по коннекторам персоны, декларативные алиасы и управление меню из чата, edge caching < 250 мс, телеметрия 👍/👎, проактивные алерты коннекторов; 09-03 перенесён.

**Closeout:** override_closeout — фазы 4–9 без VERIFICATION.md, аудит `gaps_found` (20/42 требований подтверждены), решение владельца 2026-10-09: закрыть цикл и перенести пробелы в отдельный GSD-проект assistant-core.
**Known verification overrides:** 2 newly acknowledged (debug-сессия bot-calendar-reminder-context, 03-UAT.md), 0 carried forward.

### Known Gaps

- HIT-02..04 — web-карточки HITL не доставляются в Telegram (`send_web_hitl_card` без вызовов).
- GIT-01..04, NTN-01..02 — нет точки входа: `GitEvaluator` не создаётся в рантайме.
- FIN-01 — выполнено по факту, формально не подтверждено (нет frontmatter у 06-05/06-06).
- DAT-01..04, SEC-01..03, HIT-01, ISO-01..04 — partial: SUMMARY есть, VERIFICATION нет.
- Таблицы фазы 9 создаются вне миграций `assistant-shared`; subject/sender/date NDA-писем доступны LLM в `search_emails`.
- Подробности: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`; перенос — `.planning/BACKLOG.md`.

---
