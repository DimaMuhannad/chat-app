# Phase 06: Готовность к мультитенантности - Context

**Gathered:** 2026-10-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Фаза 6 обеспечивает полную готовность платформы к мультитенантности и изоляции нескольких персон в рамках одного процесса, строгий внутренний Air-Gap для корпоративных данных и доводит проект до выполнения финального критерия завершения:
- `ISO-01`: `key_rotator.py` не мутирует глобальный `config.GEMINI_API_KEY`; ключи изолированы в контексте персоны (`ContextVar` / фабрика); `test_key_rotator.py` проходит.
- `ISO-02`: Внутренний Air-Gap (`WorkspaceScope`) в `assistant-core`: тело и вложения входящей почты (`EmailMessage`) и файлов из рабочих пространств `restricted_nda` никогда не передаются в LLM (обрабатываются строго локально). Верифицируется тестом с «ловушкой» вместо LLM-клиента.
- `ISO-03`: Zero-Trust scopes для коннекторов: коннектор объявляет `required_scopes`, ядро сверяет их со `scopes` персоны в фабрике композиции (fail-fast отказ при нехватке прав); процесс `chat-app` не держит учетные данные LMS (проверяемый тест).
- `ISO-04`: Интеграционный тест параллельной работы персоны по умолчанию и второй синтетической персоны подтверждает отсутствие cross-talk (ключи, кэши, рабочие пространства, привязки коннекторов, подтверждения).
- `FIN-01`: Метрика завершения проекта подтверждена: сканер хардкода (PER-08) работает с пустым allowlist (`HARDCODE_BASELINE = {}`) — в кодовой базе обоих репозиториев нет ГУАП, Тидекс, ФИО, персональных путей и аккаунтов вне данных персоны; персона по умолчанию ведет себя ровно как раньше; 100% pytest.

</domain>

<decisions>
## Implementation Decisions

### 1. Изоляция API-ключей Gemini и сессий (ISO-01)
- **D-01:** Ротатор ключей `GeminiKeyRotator` изолируется через `ContextVar` + фабрику `get_key_rotator(persona_id)`. Контекст вызова изолирован на уровне асинхронного таска, исключая cross-talk и race-condition между запросами параллельных персон. — **Reversibility:** costly — ядро взаимодействия с LLM во всех use-cases.
- **D-02:** Полностью удаляется строка `config.GEMINI_API_KEY = active_key`. Компоненты запрашивают `genai.Client` исключительно через ротатор или контекстную переменную.
- **D-03:** Метод `sync_active_key_to_env` выполняет запись в `.env` только при явной передаче аргумента `env_path` (для 100% совместимости с `test_key_rotator.py`). В боевом режиме (`env_path=None`) запись на диск отключена. — **Reversibility:** reversible.
- **D-04:** Пул ключей для персоны считывается из профиля персоны (`persona.gemini_keys`), а при их отсутствии — fallback на системные переменные окружения `GEMINI_API_KEYS` / `GEMINI_API_KEY`.

### 2. NDA Air-Gap для входящей почты и контекста (ISO-02)
- **D-05:** Сопоставление входящих писем (`EmailMessage`) с рабочими пространствами выполняется декларативно по привязке `account_id` или доменов отправителей/получателей к `workspace_id` персоны с уровнем допуска `restricted_nda`. — **Reversibility:** costly — затронет структуры `EmailMessage` и сборщик почты.
- **D-06:** При попадании письма из `restricted_nda` в выборку диалога или сводки (`SecretaryDialog`, `Summarizer`), в LLM передаются только обезличенные метаданные: Отправитель, Тема, Дата с пометкой `«[NDA: тело и вложения скрыты Air-Gap]»`. Поля `body_plain`, `body_html`, `snippet` и вложения полностью вырезаются. — **Reversibility:** costly — защита от утечек корпоративной тайны.
- **D-07:** Попытка генерации автоответа в `ReplyGenerator` для письма из `restricted_nda` блокируется с возбуждением исключения `AirGapViolationError` и возвратом статуса «Автогенерация ответа запрещена политикой Air-Gap».
- **D-08:** Архитектура тестовой «ловушки» (`LLM Trap`): Mock/Spy клиент `genai.Client`, перехватывающий все prompts/contents и проверяющий строгим assert полное отсутствие фрагментов тел, сниппетов, вложений и NDA-токенов при любых сценариях обработки почты `restricted_nda`.

### 3. Zero-Trust Scopes и изоляция коннекторов (ISO-03)
- **D-09:** Коннекторы объявляют требуемые разрешения через атрибут класса `required_scopes: ClassVar[tuple[str, ...]]` в базовых портах (`BaseLmsClient`, `BaseTimesheetProvider`, `BaseScheduleSourceProvider`, `BaseCalendarSyncProvider` и т.д.). — **Reversibility:** costly — контракт портов ядра.
- **D-10:** Валидация скоупов производится в фабрике композиции (`src/composition.py`): сверка `binding.scopes` персоны с `connector.required_scopes`. При отсутствии хотя бы одного требуемого скоупа фабрика выбрасывает `MissingScopeError` (fail-fast отказ в инициализации).
- **D-11:** Если у персоны нет привязки для определенной роли коннектора, коннектор не создается (возвращается `None` или заглушка `DisabledProvider`), предотвращая фоновую активность.
- **D-12:** Изоляция учетных данных LMS в `chat-app` подтверждается проверяемым автотестом `backend/tests/test_credentials_isolation.py`: инспекция настроек `Settings`, `os.environ` и роутеров на полное отсутствие полей `PRO_GUAP_*` и `LMS_*`. — **Reversibility:** reversible.

### 4. Ликвидация остаточного хардкода (FIN-01)
- **D-13:** В боевых модулях `src/` (22 файла) специфичные строковые литералы (ГУАП, Тидекс, ФИО, кафедры) заменяются на динамические данные из `current_persona()` (`ui.texts`, `workspaces`, `persona.name`). — **Reversibility:** costly — затрагивает 22 файла ядра.
- **D-14:** Вспомогательные скрипты в `scripts/` параметризуются через аргументы CLI (`argparse`) или считывают конфигурацию из `current_persona()`.
- **D-15:** Исторический артефакт `reconcile_report.json` в корне репозитория перемещается в `docs/baseline/` (или удаляется как устаревший снимок), исключаясь из корня сканирования.
- **D-16:** Ликвидация хардкода выполняется в два последовательных плана:
  1. Очистка ядра `src/` с контролем неизменности поведения через тесты 1:1.
  2. Параметризация `scripts/` и обнуление `HARDCODE_BASELINE = {}`.

### Claude's Discretion
- Точные имена исключений (`AirGapViolationError`, `MissingScopeError`).
- Вспомогательные хелперы маскирования текста письма `mask_nda_email_body()`.
- Конкретная структура тестового шпиона `SpyGenAIClient` в фикстурах pytest.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §ISO-01 — ISO-04, §FIN-01 — формальные требования мультитенантности и метрики завершения.
- `.planning/ROADMAP.md` §Phase 6: Готовность к мультитенантности — цели, критерии успеха и зависимости фазы.
- `.planning/PROJECT.md` §Success Metric — условие завершения проекта с пустым allowlist сканера.

### Architecture, Baseline & Domain
- `tests/hardcode_baseline.py` & `backend/tests/hardcode_baseline.py` — baseline остаточного хардкода (33 файла для обнуления).
- `tests/test_hardcode_scanner.py` & `backend/tests/test_hardcode_scanner.py` — правила работы сканера хардкода.
- `src/brain/key_rotator.py` — текущая реализация ротатора ключей и точка удаления мутации `config.GEMINI_API_KEY`.
- `tests/test_key_rotator.py` — набор тестов ротатора ключей для сохранения паритета.
- `src/core/domain/entities.py` — доменные сущности `EmailMessage`, `Workspace`, `WorkspaceClearance`.
- `src/core/domain/ports.py` — базовые порты и интерфейсы коннекторов для объявления `required_scopes`.
- `src/persona/models.py` & `config/persona.yaml` — схема персоны, привязки коннекторов и правила рабочих пространств.
- `backend/app/core/config.py` — конфигурация настроек студии `chat-app`.

</canonical_refs>
