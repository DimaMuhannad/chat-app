---
gsd_state_version: "1.0"
milestone: v2.0
status: Awaiting next milestone
stopped_at: Milestone v2.0 archived (override closeout); development moves to /opt/assistant-core GSD project
last_updated: "2026-10-10T14:17:00.119Z"
last_activity: 2026-10-09
last_activity_desc: Milestone v2.0 completed and archived
state_head: 568ecf2605cbe7266f5da317e3ef1a3c8f204c64
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 44
  completed_plans: 43
current_phase: 9
current_phase_name: Динамическое меню и интерфейс Telegram-бота, декларативные алиасы и аудит эргономики
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-09)

**Core value:** Профиль владельца целиком живёт в данных, а платформа работает для любой персоны — без регрессии поведения и без ослабления HITL и air-gap NDA.
**Current focus:** v2.0 закрыт. Планирование chat-app заморожено; следующий шаг — `/gsd-onboard` в `/opt/assistant-core` (отдельный GSD-проект ассистента).

## Current Position

Phase: Milestone v2.0 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-10-10 - Completed quick task 261010-cgx: cross-AI adapter protects gate environment, labels fallback gate, refuses symlinked gate path (WR-05, WR-06, T-uo4-02)

## Состояние окружения: ЗАМОРОЖЕН (с 2026-10-01)

Проект заморожен намеренно. Проверено 2026-10-01 командами только для чтения:

| Сервис | Состояние | Автозапуск |
|--------|-----------|------------|
| assistant-worker | failed (вероятно, SIGKILL при остановке; не проверялось) | disabled |
| chat-app | inactive | disabled |
| dev-bridge | inactive | disabled |

- Процессов uvicorn и демона нет. Фаза 1 стартует из этого состояния.
- Разморозка — явное решение владельца; ни одна фаза не включает сервисы автоматически.
- `/usr/local/bin/systemctl` подделывает успех `stop`/`restart` для dev-bridge (OPS-01): состояние проверять через `systemctl is-active`.
- Baseline тестов НЕ снят: прогон chat-app пишет в боевую `assistant.db`; снимается в Фазе 1 на копии БД.
- Репозитории: `/opt/chat-app` (ветка master, здесь `.planning/`), `/opt/assistant-core` (ветка main).

## Performance Metrics

**Velocity:**
- Total plans completed: 18
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | - | - |
| 02 | 4 | - | - |
| 03 | 10 | - | - |

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01-01 | 30 min | 3 tasks | 7 files |
| Phase 01 P02 | 10 min | 2 tasks | 9 files |
| Phase 01 P03 | 6 min | 2 tasks | 9 files |
| Phase 01 P04 | 8 min | 3 tasks | 4 files |
| Phase 02 P01 | 4 min | 2 tasks | 12 files |
| Phase 02 P02 | 8 min | 2 tasks | 6 files |
| Phase 02 P03 | 5 min | 2 tasks | 5 files |
| Phase 02 P04 | 4 min | 3 tasks | 9 files |
| Phase 03 P01 | 8 min | 2 tasks | 11 files |
| Phase 03 P02 | 10min | 2 tasks | 16 files |
| Phase 03 P03 | 9min | 2 tasks | 12 files |
| Phase 03 P04 | 8 min | 2 tasks | 9 files |
| Phase 03 P05 | 14 min | 2 tasks | 5 files |
| Phase 03 P06 | 6 min | 2 tasks | 8 files |
| Phase 03 P07 | 35 min | 3 tasks | 16 files |
| Phase 03 P08 | 12 min | 2 tasks | 18 files |
| Phase 03 P09 | 12 min | 3 tasks | 15 files |
| Phase 03 P10 | 30 min | 3 tasks | 12 files |
| Phase 04 P01 | 15 min | 2 tasks | 9 files |
| Phase 04 P02 | 15 min | 2 tasks | 10 files |
| Phase 04 P03 | 20 min | 2 tasks | 11 files |
| Phase 04 P04 | 15 min | 2 tasks | 5 files |
| Phase 05 P01 | 15 min | 2 tasks | 6 files |
| Phase 05 P02 | 20 min | 2 tasks | 8 files |
| Phase 05 P03 | 20 min | 2 tasks | 6 files |
| Phase 05 P04 | 25 min | 2 tasks | 7 files |
| Phase 06 P01 | 15 min | 2 tasks | 3 files |
| Phase 06 P02 | 20 min | 2 tasks | 8 files |
| Phase 08 P01 | 20 min | 2 tasks | 5 files |
| Phase 08 P02 | 25 min | 2 tasks | 6 files |
| Phase 08 P03 | 25 min | 2 tasks | 10 files |
| Phase 08 P04 | 15 min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Полный журнал — в PROJECT.md (`<decisions>` и Key Decisions). Кратко:

- [Phase 08]: 08-01: схемы tools_schema.py построены на google.genai types.Tool; строгий антигаллюцинационный промпт (D-05, ACT-02); SecretaryDialogEngine перехватывает function_calls и формирует ActionProposal без физической мутации базы или календаря.
- [Phase 08]: 08-02: Telegram HITL карточки предложений с кнопками подтверждения и отмены (D-01, ACT-03); регистрация в ConfirmationStore с TTL 15 мин; дедупликация повторных кликов; исполнение строго в action-хэндлерах.
- [Phase 08]: 08-03: FastIntentRouter расширен интентами calendar_schedule, create_reminder, draft_reply; уточняющий вопрос при неполном времени встречи без произвольных часов (D-03); двухшаговый tool calling поиска писем (D-02); буфер pending_sync в SQLite и кнопка повтора синхронизации при сетевых сбоях (D-04).
- [Phase 08]: 08-04: Сквозное E2E-тестирование подтвердило работу двухшагового Tool Calling («письмо Новиковой»), сетевой отказоустойчивости pending_sync с кнопкой retry, и уточняющего диалога при отсутствии времени события. Phase 8 принята: Quality Gate ЗЕЛЁНЫЙ (171 + 404 = 575 тестов).

- [Владелец W2/W6]: 4 рабочих пространства по умолчанию; пути — данные, репозитории не переносятся.
- [Владелец W5/W9]: одна общая БД с владельцем схемы, WAL, без шины и двойной записи; одна security-библиотека + pre-commit hook.
- [Владелец W1/W7/W8]: Фаза 7 — git по SSH и Notion через HITL; роли расписания разделены.
- [Нумерация, 2026-10-01]: фазы 1–7 (было 0–6) — GSD резервирует номер 0; старая Фаза N = новая Фаза N+1.
- [Владелец W10]: снимок промптов — пререквизит Фазы 3.
- [Roadmapper, ждёт подтверждения]: Phase 7 после Phase 6; «CI» = локальный гейт; HITL на все DELETE chat-app.
- [Phase 01]: Гейт не переопределяет БД для assistant-core (load_dotenv override=True); защита обоих репозиториев - контроль SHA-256 боевой assistant.db до/после, chat-app идёт на копии
- [Phase 01]: Владелец разрешил локальные коммиты прямо в main /opt/assistant-core на всю Фазу 1 (без push, без .planning/ в том репозитории)
- [Phase 01]: 01-02: root_packages lists namespace portions (src, src.connectors, src.sender; app, app.core) instead of adding __init__.py; allow_indirect_imports=True; live_ticker->connectors only recorded for Phase 2
- [Phase 01]: Plan 01-03: persona Phase 3 checks listed as text only (no skip/xfail); real owner Telegram ID not copied (reserved range); NDA keywords read at test time from security_shield
- [Phase 01]: Plan 01-04: владелец выбрал shield b-all-frozen (--all + замороженный список 15), 2026-10-02; красный на новой находке, сбое shield или устаревшей записи
- [Phase 02]: Характеризация _get_tydex_context закоммичена до правки src; порт без дефолтов профиля (многоточие), адаптер пробрасывает *args/**kwargs
- [Phase 02]: core-is-pure запрещает ядру все 13 прочих модулей верхнего уровня src; долг ignore_imports 5 -> 4
- [Phase 02]: 02-02: все методы портов async; синхронный разбор payload парсера закрывает адаптер ScheduleParserSource
- [Phase 02]: 02-02: BaseCalendarSink нейтрален к поставщику (event_id), REQUIRES_CONFIRMATION для submit_grade/delete_task только декларативна до Фазы 5, адаптер ЛК не подключён к боевым потокам
- [Phase 02]: 02-03: дефект /timesheet (NameError cur_m_name) не исправлен по решению владельца; поведение заморожено тестом test_cmd_timesheet_characterization, исправление - в backlog
- [Phase 02]: 02-03: Google Drive внедряется в EmailBotHandler фабрикой (drive_client_factory), а не экземпляром: сохраняется свежий клиент на колбэк
- [Phase 02]: 02-04: EventBus - одна конкретная шина без Protocol, доставка по точному типу, в журнал сбоя только имя обработчика и тип события; шина не подключена к боевым потокам (D-17)
- [Phase 02]: 02-04: LiveTickerService получает timesheet_service через конструктор, контракт live-ticker-no-adapters с пустым долгом, lint-imports 4 kept, 0 broken; Фаза 2 принята: гейт зелёный, 223 теста assistant-core
- [Phase 03]: 03-01: эталоны 8 промптов D-08 (+debrief_call) закоммичены в assistant-core до правки src; тест снимает текст по месту вызова LLM через фейк и не импортирует константы промптов; методисту в тесте секретаря нужен свой фейк (иначе реальный genai.Client уходит в сеть), реальный клиент в тестах снимка запрещён autouse-фикстурой
- [Phase 03]: 03-02: seed-CLI сначала проверяет файл персоны, потом открывает БД; chat-app читает персону только из таблиц (без PyYAML)
- [Phase 03]: 03-03: task_areas и methodist обязательны в схеме персоны; правила restricted_nda и Telegram-плейсхолдеры проверяются валидаторами (fail-closed)
- [Phase 03]: 03-03: единственное исключение shield для config/persona.yaml (3 находки), число известных находок 18 (OQ1), снимается правилом Фазы 4
- [Phase 03]: 03-04: synthetic_to_config приспосабливает вторую персону к схеме (SYNTHETIC_PERSONA и каркас Фазы 1 не тронуты); токены профиля вычисляются owner_tokens из данных персоны, пара persona_tokens.py под дрейфом SHA-256 в гейте
- [Phase 03]: 03-05: Security Tile строится из workspaces персоны (clearance вместо id, правила remote и сообщение - данные пространства), без данных 503; характеризация NDA-чек-листа закоммичена до правки, assert-строки сохранены дословно; Web по-прежнему не проверяет слова NDA (1:1, закрывает Фаза 4)
- [Phase 03]: 03-06: область по умолчанию из персоны при создании (без персоны 503, явная область персоне не нужна); /persona/current отдаёт task_areas и ui.texts явным белым списком; index.html без токенов владельца, данные персоны в DOM только через textContent/Option, область выводится через escapeHtml; DDL assistant-core DEFAULT остаётся долгом до Фазы 6
- [Phase 03]: 03-07: Jinja2 3.1.6 и MarkupSafe 3.0.3 поставлены с двумя точными закреплениями после одобрения владельца (одиночная установка потянула бы MarkupSafe 3.0.4); render_prompt - SandboxedEnvironment + StrictUndefined + keep_trailing_newline, рендер один раз до цикла попыток моделей; 4 промпта (secretary, intent_router, methodist, methodist_scope_check) = эталоны 03-01 побайтно, константы удалены
- [Phase 03]: 03-08: имена runtime-переменных дайджестов date_str, weekday, tomorrow_date_str, tomorrow_weekday; все 8 промптов D-08 - шаблоны персоны и рендерятся в эталоны побайтно; дебриф рендерится до try; синтетическая персона даёт 8 других промптов на тех же кодовых путях (PER-09, промпты); пробрасывание PersonaConfigError из внешнего try дайджестов - вопрос к 03-10
- [Phase 03]: 03-09: параметры коннекторов (проект и норма табеля, слоты и предметы, адреса расписания и ЛК, каталоги и правила методиста) читаются из привязок персоны в момент вызова через src/persona/bindings.py; сигнатуры композиции не менялись, шов - необязательные settings/base_url
- [Phase 03]: 03-09: один источник слотов, описание события календаря берёт слоты из персоны, у пары 20:20 для персоны по умолчанию появилась строка Пара: 7 (единственное отличие поведения); SCHEDULE_URL из окружения сильнее персоны

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3] Открыт вопрос: где живёт загрузчик персоны до появления общей библиотеки (Фаза 4).
- [Phase 4] Открыт вопрос: физическое расположение общей библиотеки; артефакты в корне assistant-core (пустой `assistant.db`, каталог `sqlite+aiosqlite:`).
- [Phase 1] Тесты chat-app пишут в боевую `assistant.db` — прогонять только через `python3 scripts/gate.py` (работает на копии БД, хеш боевой БД контролируется). Baseline: 14 + 127 тестов, все зелёные.
- [Phase 1 → 2] Открытые замечания код-ревью (`01-REVIEW-DISPOSITION.md`, 14 открыто, критичных нет): WR-03 (в гейте нет нижней границы числа тестов, наследуется `PYTEST_ADDOPTS`) стоит закрыть до рефакторинга Фазы 2; WR-05 (гейт оставляет каталоги `gate-*` в `/opt/assistant-core/sqlite+aiosqlite:/tmp/`, ~70 МБ); WR-07 (ФИО/git-аккаунт владельца открытым текстом в `test_synthetic_persona.py` обоих репозиториев как deny-list; заменит PER-08 в Фазе 3).
- [Phase 2] Нарушение `src.notifier.live_ticker -> src.connectors.aadhk.parser` записано в BASELINE; 5 записей `ignore_imports` в assistant-core убирает PRT-04.
- [Перед разморозкой chat-app] API без аутентификации и CORS `*` (v2: AUTH2-01/02) — решение владельца.
- [Операционное] Ключ в юните dev-bridge (OPS-02) — владелец не ротирует; assistant-worker уходит в SIGKILL (OPS-03); `notion_dev.py` в chat-app с битым импортом (OPS-04, вне миграции).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261009-uo4 | adapter cross-AI runs target repository gate (GATE-05) | 2026-10-09 | 6b3b2ac | [261009-uo4-adapter-cross-ai-runs-target-repository-](./quick/261009-uo4-adapter-cross-ai-runs-target-repository-/) |
| 261010-ivt | shield rules from workspace data, web audit checks NDA keywords (SECF-01, SECF-02) | 2026-10-10 | 568ecf2 | [261010-ivt-shield-rules-from-workspace-data-web-aud](./quick/261010-ivt-shield-rules-from-workspace-data-web-aud/) |
| 261010-cgx | cross-AI adapter protects gate environment, labels fallback gate, refuses symlinked gate path (WR-05, WR-06, T-uo4-02) | 2026-10-10 | 27886b3 | [261010-cgx-cross-ai-adapter-gate-environment-protecti](./quick/261010-cgx-cross-ai-adapter-gate-environment-protecti/) |

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| v2 | AUTH2-01/02 аутентификация и CORS; UI2-01/02; PLT2-01 | Deferred | 2026-10-01 | v1 |

Решено владельцем 2026-10-01 (из открытых вопросов): Web-подтверждения — через Telegram; HITL на всех DELETE chat-app; в Notion по NDA — только агрегаты (бывший NTN2-01 вошёл в GIT-04); «CI зелёный» = локальный скрипт-гейт.

## Session Continuity

Last session: 2026-10-04T21:35:00.000Z
Stopped at: Phase 07 plans generated (4 plans ready), ready for Plan 07-01
Resume file: .planning/phases/07-git-istochniki-i-dashbordy-notion/07-01-PLAN.md

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
