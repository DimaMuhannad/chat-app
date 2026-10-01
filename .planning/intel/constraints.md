# Ограничения — constraints.md

Источники: SPEC-документы (blueprint, precedence 0; multi-project, precedence 1) и жёсткие ограничения из проектного CLAUDE.md (переданы оркестратором).
Контент пересказан; личные контакты, логины, e-mail, хосты и конфиденциальные ключевые слова в файл НЕ копировались.
Записи из MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md, помеченные "частично оспорено", пересекаются с blueprint — см. WARNINGS в INGEST-CONFLICTS.md; здесь они сохранены, ничего не отброшено.

## Правило зависимостей Clean Architecture (три слоя)
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 1)
- type: nfr
- content: Core Platform не импортирует ничего из Persona Plugins и Studio UI. Persona Plugins реализуют порты Core и не знают друг о друге. Studio UI обращается к Core только через REST/WebSocket и никогда напрямую к внутренним модулям assistant-core (сегодня нарушается через общий файл БД). Use-cases (IntentRouter, SecretaryDialog, Methodist) зависят только от портов. Хранилище — SQLite, принадлежащая персоне, ключи по persona_id/thread_id, без абсолютных межрепозиторных путей. Studio UI: Manager View (обзор workspace/персон) и Editor View, Security Tile, Task Dashboard, Git Registry, Artifacts Panel; транспорт аутентифицированный.

## Доменные сущности
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 2.1)
- type: schema
- content: Неизменяемые dataclass: `ScheduleEvent` (external_id, title, starts_at, ends_at, location опционально); `WorkRecord` (shift_date, hours, project_tag — вместо хардкода названия компании); `AcademicSubmission` (submission_id, title, deadline, is_public); `Task` (title, area — свободная строка, status). Enum `WorkspaceClearance`: public, internal, restricted_nda. В списке сущностей ядра также упомянуты `EmailMessage`, `Workspace`, `Persona` (отдельная схема для `EmailMessage` в blueprint не приведена).

## Порты коннекторов (BaseConnector и наследники)
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 2.2)
- type: api-contract
- content: `BaseConnector` (Protocol, runtime_checkable): `connector_id`, `required_scopes` (кортеж строк, Zero-Trust), async `health_check() -> bool`. `BaseScheduleProvider`: async `fetch_events(since)`, async `diff_against(known)`. `BaseTimesheetProvider`: async `fetch_shifts(start, end)`, async `monthly_pacing(start, end, norm_hours_per_day)`. `BaseLMSProvider`: async `list_tasks()`, async `submit_grade(submission_id, grade)`; `submit_grade` и `delete_task` ОБЯЗАНЫ быть обёрнуты `@requires_confirmation`. Все методы I/O — async.

## HITL-примитив (ConfirmationStore и requires_confirmation)
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 2.3)
- type: api-contract
- content: `PendingConfirmation` (action_id, persona_id, summary, payload, created_at). Protocol `ConfirmationStore`: async `create(action)`, async `resolve(action_id, approved) -> PendingConfirmation`. Декоратор `requires_confirmation(summary_fn)` для деструктивных методов (submit_grade, delete_task, clear_dialog_history, DELETE /projects/{id} и т.п.): первый вызов сохраняет запись и поднимает `ConfirmationRequired(action_id)` вместо выполнения; `resume_action(action_id, approved=True)` — единая точка возобновления, вызываемая и из Telegram callback, и из `POST /api/v1/confirmations/{id}`, и повторно вызывающая исходный метод с сохранённым payload. Назначение: закрыть риск аудита — HITL есть в Telegram, но отсутствует в Web Studio (сегодня `DELETE /api/v1/projects/{id}` без серверной защиты). Паттерн-референс: LangGraph `interrupt()` / `Command(resume=...)`.

## Событийная шина и доменные события
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 2.4)
- type: api-contract
- content: `DomainEvent` (event_id uuid, occurred_at). События: ScheduleChanged, TimesheetSynced, TaskCreated, SecurityViolationDetected, DialogMemoryCleared, DelegatedToSpecialist (from_agent, to_agent, reason). Protocol `EventBus`: async `publish(event)`, `subscribe(event_type, handler)`. На старте — внутрипроцессная asyncio-реализация; задел на внешний брокер при реальном разделении процессов (Фаза 3).

## Схема persona.yaml
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 3.1)
- type: schema
- content: Файл `config/persona.yaml`, корневой ключ `persona`. Поля: `id`, `display_name`, `honorific`, `timezone`; `telegram.authorized_user_ids` (значения подставляются из переменных окружения, не хранятся в файле); `workspaces[]` (id, label, clearance из enum, path, color, forbidden_remote_substrings[], forbidden_keywords[]); `connectors.schedule|timesheet|lms` (provider, scopes[], config{}); `prompts` (secretary_system_prompt, intent_router_prompt, methodist_prompt — пути к Jinja2-шаблонам). Дефолтная персона `popov-da-default` — 100% эквивалент сегодняшнего поведения (в т.ч. norm 8.5 ч/день для timesheet-коннектора). Конкретные значения (личные данные, ключевые слова NDA) в intel не копируются — см. исходный файл.

## Схема SQLite для персон
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 3.2)
- type: schema
- content: Новые таблицы дополняют, а не заменяют существующие `projects`/`tasks`. `personas` (id PK, display_name, config_json — валидированный снапшот persona.yaml, created_at). `workspaces` (id PK, persona_id FK, label, path, clearance CHECK in public/internal/restricted_nda, forbidden_remote_substrings JSON, forbidden_keywords JSON, color) — заменяет `PROJECTS_REGISTRY` (security.py), Web UI-таблица рендерится без изменений, т.к. `/security/overview` уже отдаёт project-agnostic JSON. `connector_bindings` (id, persona_id FK, role schedule|timesheet|lms, provider, scopes JSON, config_json). `pending_confirmations` (action_id PK, persona_id FK, summary, payload_json, created_at, resolved_at, approved) — backing store для requires_confirmation.

## Zero-Trust least-privilege для коннекторов
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (разделы 2.2, 3.1, 6)
- type: nfr
- content: Каждый коннектор декларирует `required_scopes`; персона декларирует `scopes` в блоках `connectors.*`. Ядро отказывается поднимать коннектор (например GuapLmsClient) для процесса, которому персона не выдала соответствующий scope (например `lms.*`). Процесс chat-app не должен держать credentials LMS — это должно стать проверяемым фактом. Плагины регистрируются на уровне персоны, а не в глобальном реестре; для опасных методов — "зарегистрировать, но не вызывать автоматически".

## Сквозные гейты миграции
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 4, абзац "Сквозные требования"); CLAUDE.md (раздел 2, п.4)
- type: nfr
- content: 100% pytest на КАЖДОМ шаге, не только в конце. Каждая фаза коммитится атомарно с возможностью revert. Начиная с Фазы 2 обязателен тест "вторая синтетическая персона" — единственное доказательство, что универсализация реальна. Не допускается регрессия: существующие тесты не удаляются и не ослабляются.

## Гарантии обратной совместимости
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 5)
- type: nfr
- content: Профиль дефолтной персоны переносится 1:1 в `config/persona.yaml`; без `PERSONA_CONFIG_PATH` загружается именно он; поведение прода не меняется до явного переключения. Подробности и список неприкосновенных тестов — в requirements.md (REQ-default-persona-backward-compat).

## HITL обязателен для любого деструктивного действия
- source: CLAUDE.md (раздел 2, п.4; передано оркестратором); /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 2.3)
- type: nfr
- content: Любое деструктивное действие (стирание памяти, удаление данных, выставление оценок, DELETE endpoint-ы) проходит через Human-in-the-Loop подтверждение; без серверной защиты на Web API деструктивные операции недопустимы.

## Air-gap изоляция корпоративных/NDA workspace
- source: CLAUDE.md (раздел 2, п.4; передано оркестратором); /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (разделы 5.1, 5.3)
- type: nfr
- content: Строгая air-gap изоляция для workspace с допуском restricted_nda: код и данные закрытого контура не должны попадать в публичные репозитории, логи и контекст агентов публичных проектов. Субагентам, запущенным в сессиях публичных проектов, запрещено читать директории закрытого контура. NDA air-gap должен действовать и внутри assistant-core (Фаза 5), не только в chat-app.

## 100% прохождение pytest
- source: CLAUDE.md (раздел 2, п.4; раздел 3; передано оркестратором); /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (раздел 3.2)
- type: nfr
- content: Все наборы pytest (`backend/tests` в chat-app, `tests` в assistant-core) должны проходить на 100% на каждом шаге. Ни один коммит не считается завершённым без прогона тестов. Правило 3 итераций (MULTI 3.2): если за 3 попытки падение не устранено — зафиксировать блок через `notion_dev.py block` и вернуть задачу в Backlog.

## Async-first I/O
- source: CLAUDE.md (раздел 4; передано оркестратором)
- type: nfr
- content: Весь ввод-вывод — async: БД через `aiosqlite`, сеть через `httpx`/`aiohttp`. Все порты blueprint объявлены async.

## KISS и YAGNI
- source: CLAUDE.md (раздел 4); /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (раздел 3.1)
- type: nfr
- content: Избегать переусложнения; предпочитать типизированные dataclass и Pydantic-модели. Принципы агентной разработки: Occam's Razor, KISS, YAGNI, Boy Scout Rule, Hanlon's Razor.

## Язык пользовательского вывода — строго русский
- source: CLAUDE.md (раздел 4); /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (раздел 3.1)
- type: nfr
- content: Любой текст, адресованный пользователю (чат, Telegram, UI), — строго на русском. Код, комментарии, коммиты и PR могут быть на английском или русском. Запрещены локальные ссылки с протоколом `file:///`; обязательны diff-блоки со статусом Git.

## Политика сканирования секретов (Pre-Commit Secret Shield)
- source: /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (раздел 5.2)
- type: nfr
- content: Автономный скрипт `scripts/security_shield.py` как Git pre-commit hook или шаг CI. Четыре проверки: (1) поиск секретов — приватные ключи, персональные токены GitHub, ключи Google Gemini API, токены Telegram-ботов и Notion API; (2) блокировка коммита файлов с учётными данными (.env, credentials.json, token.json, *.session, *.pem, *.key); (3) проверка origin remote — для проектов с префиксом `tydex` remote не должен указывать на публичный личный аккаунт; (4) контекстный air-gap — отсутствие закрытых ноу-хау Тидекс в кодовой базе публичных проектов. ЧАСТИЧНО ОСПОРЕНО: пп.3-4 жёстко привязаны к Тидекс, blueprint предписывает настраиваемые `forbidden_remote_substrings`/`forbidden_keywords` на workspace; "автономность" скрипта спорит с общим пакетом Фазы 3 (см. WARNINGS).

## Плитка безопасности (Security Tile) в Web Studio
- source: /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (раздел 5.3)
- type: nfr
- content: Интерактивная плитка в боковой панели и верхнем статус-баре: (1) бейдж допуска проекта — два уровня (публичный/академический и закрытый NDA); (2) монитор утечек — статус pre-commit hook и сканера секретов (Passed/Alert); (3) Remote Safeguard — предупреждение при `git push` в неавторизованный remote; (4) контекстный брандмауэр агента — блокировка чтения закрытой директории субагентами в сессиях публичных проектов. ЧАСТИЧНО ОСПОРЕНО: два уровня бейджа против трёх значений `WorkspaceClearance` в blueprint; жёстко прописанный путь закрытого контура против `workspaces.path` (см. WARNINGS).

## Мультиаккаунтная изоляция Git и SSH
- source: /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (разделы 2.1-2.4)
- type: protocol
- content: Два GitHub-аккаунта: личный/академический (публичные и закрытые репозитории) и корпоративный (строго закрытые, NDA). Для каждого — отдельный SSH Host Alias с выделенным ключом и `IdentitiesOnly yes`; клонирование корпоративных репозиториев идёт через алиас. Условная маршрутизация `includeIf "gitdir:..."` подставляет корпоративного автора и `core.sshCommand` внутри каталога закрытого контура, исключая коммит под личным e-mail/ключом. Репозитории разнесены по двум изолированным родительским каталогам на хосте. Адреса, логины и e-mail в intel не копируются. ЧАСТИЧНО ОСПОРЕНО: ровно 2 аккаунта и фиксированная раскладка каталогов против N workspace с clearance (см. WARNINGS).

## Единые рельсы разработки (Unified Dev Rails)
- source: /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (раздел 3)
- type: protocol
- content: В корне каждого репозитория — файл директив агента (`GEMINI.md`/`AGENTS.md`): роль агента, архитектурные границы, языковой протокол, стандарты оформления (эмодзи-заголовки жирным, diff-блоки). Префиксы коммитов: feat, fix, refactor, test, docs, infra; атомарные коммиты; тест-гейт (pytest или vitest). Сессионный след в карточке задачи Notion: [Changeset], [Design Decisions], [Quality Gates Status], [Technical Debt Introduced].

## Раздельный контроль задач в Notion
- source: /opt/chat-app/docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md (раздел 4)
- type: protocol
- content: Двусторонняя связь Relation между базой проектов и базой инженерных задач; база проектов содержит 4 фундаментальных направления (ассистент/Studio, приборный сектор компании, кафедра физики, исследования и публикации); каждая задача связывается с одним или несколькими проектами. CLI `scripts/notion_dev.py` умеет list/create/block с фильтром по проекту. ЧАСТИЧНО ОСПОРЕНО: фиксированный список из 4 проектов и фиксированные значения `--project` против конфигурируемых данных персоны (см. WARNINGS).
