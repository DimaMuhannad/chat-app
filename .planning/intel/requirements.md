# Требования — requirements.md

PRD-документов в наборе нет. По указанию оркестратора требования выведены из блока "Roadmap миграции" (раздел 4) и раздела 5 документа
`docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` (тип SPEC, precedence 0). Определение "готово" (Definition of Done) каждой фазы использовано как acceptance.
Формулировки пересказаны, а не выдуманы: ничего сверх источника не добавлено. Конфликтующих вариантов acceptance между PRD нет (PRD отсутствуют).

Порядок фаз: 0 -> 1 -> 2 -> 3 -> 4 -> 5. Сквозной гейт на каждой фазе (см. constraints.md, "Сквозные гейты миграции"): 100% pytest на каждом шаге,
атомарный коммит с возможностью revert, с Фазы 2 обязателен тест "вторая синтетическая персона".

## REQ-phase0-safety-net
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 4, Фаза 0)
- description: Страховочная сеть перед рефакторингом (оценка 1-2 недели, риск низкий). Контракт `import-linter` (domain не импортирует adapters); текущий pytest фиксируется как baseline; каркас "второй синтетической персоны" (пока с заглушками).
- acceptance: CI зелёный; baseline задокументирован.
- scope: CI, тестовый baseline, архитектурные контракты импортов, каркас синтетической персоны

## REQ-phase1-ports-extraction
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 4, Фаза 1; раздел 2.2)
- description: Извлечение портов без изменения поведения (2-3 недели, риск средний: возможны несовместимые сигнатуры, нужны adapter-wrapper'ы). Создать `core/ports/*`; привести `GuapLmsClient`, `AadhkIngestionService`, `GoogleCalendarClient` к совместимости с протоколами; inline-импорты в `secretary_dialog.py` и `bot_handler.py` заменить конструкторной инъекцией (по образцу существующего `MethodistService`). По аудиту: `src/calendar/client.py` — низкий объём переделки; `src/connectors/aadhk/parser.py` — умеренный; `src/connectors/guap_lms/client.py` — самый глубокий (становится первой реализацией интерфейса, а не самим интерфейсом).
- acceptance: 100% текущих тестов проходят без изменения фикстур; Protocol-проверка подтверждает соответствие.
- scope: assistant-core, core/ports, коннекторы (schedule, timesheet, LMS), dependency injection

## REQ-phase2-persona-config
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 4, Фаза 2; раздел 3)
- description: `persona.yaml` и SQLite-схема персон (2 недели, риск средний-высокий: промпты влияют на поведение LLM, нужен golden-набор ответов до рефакторинга). Таблицы из раздела 3.2; `PROJECTS_REGISTRY` и хардкод-дефолты `'ГУАП'`/`'Тидекс'` становятся данными; промпты переносятся в Jinja2-шаблоны.
- acceptance: `PROJECTS_REGISTRY` удалён как код; новый `test_persona_config.py` подтверждает, что вторая синтетическая персона даёт отличные от дефолтной промпты и scope-решения; 100% pytest.
- scope: config/persona.yaml, таблицы personas/workspaces/connector_bindings/pending_confirmations, security.py (реестр), промпты, Security Tile (источник данных)

## REQ-phase3-eventbus-db-decoupling
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 4, Фаза 3; раздел 2.4; раздел 7 п.1)
- description: Внутренняя шина событий; chat-app перестаёт напрямую открывать БД assistant-core; `SECRET_PATTERNS`/`FORBIDDEN_FILES`/`run_cmd()` выносятся в общий пакет (устраняет дрейф `security_shield.py` и `security.py`). Оценка 3-4 недели; риск САМЫЙ ВЫСОКИЙ в плане (единственная фаза, затрагивающая границу процессов в проде): нужен staged rollout и двойная запись в переходный период. Стратегия развязки БД — открытый вопрос (см. INGEST-CONFLICTS.md).
- acceptance: `pytest backend/tests` проходит против свежей пустой БД без доступа к `/opt/assistant-core`; существует одна security-реализация, импортируемая из обоих мест.
- scope: EventBus, граница chat-app/assistant-core, общий security-пакет, миграция данных

## REQ-phase4-zero-trust-hitl
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 4, Фаза 4; раздел 2.3)
- description: Унификация HITL (2 недели, риск средний: важно сохранить Telegram UX 1:1). `@requires_confirmation` + `pending_confirmations`; Telegram-flow переводится на примитив без изменения UX; тот же примитив добавляется на `DELETE /api/v1/projects/{id}` и `documents/{id}` в chat-app.
- acceptance: `test_hitl_safety_guardrails.py` и `test_bot_group_isolation.py` проходят без изменения ассертов; новый `test_web_hitl_guardrails.py`: прямой HTTP DELETE без токена возвращает 409, а не 200.
- scope: HITL-примитив, Telegram bot_handler, chat-app DELETE endpoints, ConfirmationStore

## REQ-phase5-multitenancy-readiness
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 4, Фаза 5)
- description: Готовность к мультитенантности (2-3 недели, риск средний: тонкие concurrency-баги при удалении глобального состояния). Убрать мутацию глобального `config.GEMINI_API_KEY` в `key_rotator.py`; ввести `WorkspaceScope`-enum для NDA air-gap внутри assistant-core (не только в chat-app).
- acceptance: интеграционный тест одновременно инстанцирует 2 персоны и подтверждает отсутствие cross-talk; 100% прочих тестов.
- scope: key_rotator, глобальное состояние, NDA air-gap в assistant-core, изоляция персон

## REQ-default-persona-backward-compat
- source: /opt/chat-app/docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md (раздел 5)
- description: Дефолтный плагин `popov-da-default` переносит текущее поведение 1:1 (меняется только место хранения: код -> данные); загружается по умолчанию при отсутствии `PERSONA_CONFIG_PATH`; поведение в проде не меняется ни на одном шаге до явного переключения персоны. Тесты, проверяющие хардкод напрямую (например `test_search_local_files_catalog`, `test_fast_intent_router.py`), переписываются на проверку того же поведения через загруженную дефолтную персону — не удаляются и не ослабляются. Чистые safety/correctness-тесты (`test_hitl_safety_guardrails.py`, `test_bot_group_isolation.py`, `test_phase1.py`, `test_phase2_filter.py`, `test_key_rotator.py`, `test_voice.py`, parsing-тесты AADHk) не трогаются, кроме фикстур персоны.
- acceptance: все существующие тесты (20 в assistant-core и 4 в chat-app с персона-зависимым контентом) проходят на каждом шаге миграции.
- scope: default persona, обратная совместимость, тестовый набор
