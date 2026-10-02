# Phase 3: Персона как данные - Research

**Researched:** 2026-10-02
**Domain:** перенос профиля владельца из кода в данные (persona.yaml + SQLite-таблицы), Jinja2-промпты со снимком, white-label веб-интерфейс, NDA-правила как данные, сканер хардкода
**Confidence:** HIGH по фактам о коде и окружению (прочитано и проверено в этой сессии); MEDIUM по проектным решениям, помеченным [ASSUMED] (схема персоны, форма API)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Владелец (не специалист) на обсуждении выбрал режим «все 4 темы с рекомендациями Claude» и по каждой теме ответил «решай сам». Все решения ниже приняты Claude по KISS/YAGNI и CLAUDE.md и НЕ являются решениями уровня W1–W10. Планировщик обязан им следовать, если исследование не опровергнет их фактами; при опровержении — вернуть вопрос владельцу простыми словами с вариантами (AskUserQuestion, по-русски, рекомендуемый вариант первым).

#### Где живёт персона и как её видят оба репозитория (PER-01, PER-02) — закрывает открытый вопрос ROADMAP
- **D-01:** Источник правды — файл `config/persona.yaml` в assistant-core (там уже есть PyYAML 6.0.3 и pydantic 2.13). Загрузчик и Pydantic-модели персоны живут ТОЛЬКО в assistant-core (например, `src/persona/`). Персона по умолчанию `popov-da-default` поставляется вместе с кодом и грузится при отсутствии `PERSONA_CONFIG_PATH`; переменная `PERSONA_CONFIG_PATH` подменяет файл (так в тестах загружается вторая персона). — **Reversibility:** costly — на формате файла и именах полей строятся промпты, коннекторы и UI; смена формата затрагивает оба репозитория.
- **D-02:** Таблицы `personas`, `workspaces`, `connector_bindings` (схема blueprint разд. 3.2, роли привязок W8) создаются СУЩЕСТВУЮЩИМ механизмом инициализации схемы — `src/storage/db.py` assistant-core (chat-app таблиц сегодня не создаёт вообще). Загрузка персоны в таблицы — идемпотентная (upsert), `personas.config_json` хранит валидированный снимок. Новый «владелец схемы» не вводится (Фаза 4). `pending_confirmations` не создаётся.
- **D-03:** chat-app НЕ читает YAML и НЕ получает зависимость PyYAML: он читает персону и рабочие пространства из таблиц общей БД через `DatabaseService` (aiosqlite) и отдаёт её веб-интерфейсу через `/api/v1/persona/current`. Загрузчик в двух репозиториях не дублируется. — **Reversibility:** reversible — замена на «chat-app читает YAML сам» локальна.
- **D-04:** ОБЯЗАТЕЛЬНО проверить в research: боевая БД сегодня НЕ содержит таблиц персон (сервисы заморожены, assistant-core ещё не запускался с новой схемой), а гейт гоняет chat-app pytest на КОПИИ боевой БД (`scripts/gate.py`, Фаза 1 D-03). Значит, тесты chat-app (`test_security_api.py` ждёт ровно 4 пространства) должны получать персону из таблиц в копии БД. Рекомендуемый путь: шаг подготовки копии в `gate.py` (в той же функции защиты БД) прогоняет инициализацию схемы и загрузку персоны assistant-core НА КОПИИ; для запуска pytest chat-app вручную (команда из CLAUDE.md) нужен эквивалент — фикстура. Боевая `assistant.db` по-прежнему не меняется (контроль SHA-256 гейта остаётся). Если путь не работает — вернуть владельцу.
- **D-05:** Идентификаторы Telegram и иные внешние ID подставляются из окружения (`${TELEGRAM_USER_ID}`), в файле не хранятся (PER-01). Поведение при незаданной переменной — на усмотрение планировщика, но без молчаливой подстановки пустой строки там, где это открывает доступ (авторизованные пользователи).
- **D-06:** Вторая синтетическая персона (Фаза 1: `synthetic_persona.py`, dict, две копии с контролем SHA-256 в гейте) становится загружаемой теми же кодовыми путями. Как совместить это с дрейф-проверкой гейта (например, YAML-фикстура, порождаемая из dict, либо замена шага гейта) — решает планировщик; ослаблять проверки Фазы 1 нельзя. Список «Ожидают Фазы 3» из `docs/BASELINE.md` — исходный чек-лист включаемых проверок.

#### Промпты (PER-07, W10)
- **D-07:** Первый план фазы — снимок точного текста ВСЕХ системных промптов до любых правок (пререквизит W10). Снимок — файлы-эталоны в тестовых данных assistant-core; тест рендерит шаблон с персоной по умолчанию и сравнивает символ в символ. Golden-набор ответов LLM не нужен.
- **D-08:** Переносим в Jinja2-шаблоны ВСЕ промпты, где зашит профиль владельца, а не только три из плана: `SECRETARY_SYSTEM_PROMPT` (`src/brain/secretary_dialog.py`), `ROUTER_SYSTEM_PROMPT` (`intent_router.py`), `METHODIST_SYSTEM_PROMPT` и `SCOPE_CHECK_PROMPT` (`methodist.py`), а также `SYSTEM_PROMPT` (`reply_generator.py`), `DEBRIEF_SYSTEM_PROMPT` (`debrief_parser.py`) и два встроенных `system_instruction` в `summarizer.py` (строки ~154 и ~383). Причина: механизм снимка строится один раз, а без этого Фаза 6 («в коде нет ГУАП/Тидекс/ФИО») вынуждена повторять работу. Обязательный минимум — три промпта из ROADMAP (критерий 1); остальные идут по той же схеме отдельным планом/волной. Если у какого-то промпта риск несовпадения слишком высок (текст собирается динамически), планировщик вправе оставить его в baseline-allowlist сканера (D-16) с явной записью.
- **D-09:** Шаблоны — `prompts/*.jinja2` (имена по blueprint 3.1: `secretary_default.jinja2`, `intent_router_default.jinja2`, `methodist_default.jinja2`; остальные — по аналогии), пути к ним — поле `prompts:` в персоне. Рендер должен быть байт-в-байт: `StrictUndefined`, без автоэкранирования, сохранение завершающего перевода строки. В шаблоны уходят только статические данные персоны (имя, титул, организации, нормы); то, что промпт получает во время работы (память, контекст дня), остаётся как сейчас — исследователь обязан это выяснить построчно.
- **D-10:** Jinja2 не установлена ни в одном `.venv` и не указана в `requirements`. Добавить зависимость в `requirements.txt` assistant-core и установить в `.venv` (изменение окружения вне git — записать версию в `docs/BASELINE.md`, как это сделано для import-linter в Фазе 1 D-06). В chat-app Jinja2 не нужна.

#### Веб-интерфейс как white-label (PER-05)
- **D-11:** В персоне — отдельные поля `task_areas` (список областей задач; у владельца: ГУАП и Тидекс) и `default_area` (у владельца: ГУАП). Область задачи — НЕ то же самое, что рабочее пространство (пространств 4, областей 2): области из пространств не выводятся, чтобы вид интерфейса не изменился (иначе появились бы лишние кнопки). Существующие строки `area` в БД не трогаем.
- **D-12:** `index.html` не содержит ФИО, титула, «ГУАП» и «Тидекс» в статике: страница при загрузке запрашивает `/api/v1/persona/current` и заполняет шапку, кнопки фильтра областей, список областей в форме задачи, подсказки и описательные тексты Security Tile (сегодня — строки ~70, 218, 265-266, 442, 464, 506, 582-583, 659, 932, 947). Пока данные не пришли — нейтральные пустые места, не имя владельца. Конечный вид с персоной по умолчанию — тот же.
- **D-13:** Дефолт области новых задач/проектов берётся из персоны: убрать `area: str = "ГУАП"` в `backend/app/models/dashboard_schemas.py` (строки 8, 33) и `data.get("area", "ГУАП")` в `backend/app/db.py` (строки 149, 244) — подставлять `default_area` текущей персоны. SQL-`DEFAULT 'ГУАП'` в DDL assistant-core (`src/storage/db.py:148,162`) не меняет существующие таблицы — как с этим обойтись, решает исследователь, не ломая существующие данные.

#### Security Tile и NDA-правила (PER-03, PER-04, W3, W4)
- **D-14:** `PROJECTS_REGISTRY` удаляется как код; `/api/v1/security/overview` строится из `workspaces`. Вывод с персоной по умолчанию ИДЕНТИЧЕН сегодняшнему, включая порядок записей (сегодня: chat-app, assistant-core, tydex-optics, guap-physics), эмодзи в названиях, `account`, `clearance_label`, `color`, статусы и цвета, air-gap при отсутствии каталога. Поэтому данные пространства должны нести ровно сегодняшние строки (blueprint 3.1 сокращает названия — при расхождении побеждает 1:1 с текущим выводом, не blueprint). Признак `is_tydex` по id/префиксу заменяется на `clearance`; правила `forbidden_remote_substrings` / `forbidden_keywords` читаются из данных пространства.
- **D-15:** Скрипты `scripts/security_shield.py` (обе копии) в Фазе 3 НЕ переводятся на данные: в Фазе 4 они всё равно переписываются в тонкую обёртку над общей библиотекой, двойная работа не нужна. Вместо этого тест эквивалентности NDA (W3) ведёт явный чек-лист ВСЕХ сегодняшних проверок из `security.py` и обеих копий скрипта и включает проверку «не расходятся»: правила скриптов совпадают с данными персоны по умолчанию, а набор блокируемых нарушений не стал уже (негативные случаи обязательны). ВНИМАНИЕ для исследователя: определение «Тидекс» в скриптах — по подстроке `tydex` в ПУТИ репозитория, в `security.py` — по remote/id; чек-лист должен зафиксировать обе логики и не сузить ни одну. Тест перезапускается в Фазе 4 против общей библиотеки.

#### Остаточный долг и сканер хардкода (PER-08)
- **D-16:** Тест-сканер ищет токены профиля (ГУАП/GUAP, Тидекс/Tydex, ФИО, персональные пути, аккаунты) в коде обоих репозиториев вне явного allowlist (файлы данных персоны, фикстуры тестов, docs). Токены берутся из данных персоны по умолчанию (замена константы-denylist из Фазы 1 D-14). В Фазе 3 фиксируется baseline-allowlist (остаточный долг), который НЕ может расти; сокращается по мере миграции. Ожидаемый остаточный долг: обе копии `security_shield.py`, стартовые данные и дефолты `'Тидекс'` в `src/storage/db.py` (строки ~199, 1448-1468, 1881, 1905, 2807), любые промпты, оставленные по D-08. Фаза 6 доводит allowlist до пустого.
- **D-17:** Тесты с прямой проверкой хардкода (`backend/tests/test_dashboard_api.py:50` `"area": "ГУАП"`, фикстуры Фазы 1 и аналоги в assistant-core) переписываются на проверку через персону — не удаляются и не ослабляются (критерий 5).

#### Параметры коннекторов (PER-06)
- **D-18:** Параметры, зашитые в код, читаются из персоны / `connector_bindings`: `default_project` «Тидекс» (известные места: `src/main.py:296`, `bot_handler.py:1114,1170`, `secretary_dialog.py:144`), норма 8.5 ч/день, короткие названия предметов и слоты расписания, адреса сайта расписания и личного кабинета, каталог методических файлов. Точный перечень — по результатам аудита исследователя (требование PER-06). Роли привязок: `schedule_source`, `calendar_sync`, `timesheet`, `lms` (на роль допускается несколько привязок, W8); `git_source` и `notion` — только объявлены в схеме. Точка внедрения — фабрики `src/composition.py` из Фазы 2 (D-12): они получают конфигурацию привязки из персоны, а не знают значения сами.

#### Процесс
- **D-19:** Порядок: снимок промптов (первый план) → модели/загрузчик/таблицы персоны → рабочие пространства и NDA из данных (chat-app) → веб-интерфейс и `/persona/current` → промпты в Jinja2 → параметры коннекторов → сканер хардкода и `test_persona_config.py`. Коммиты атомарные, раздельные по репозиториям (assistant-core — `main`, chat-app — `master`, без push); каждый шаг — гейт `python3 /opt/chat-app/scripts/gate.py` зелёный; сервисы остаются остановленными, перезапусков нет. Тестовые утверждения не ослабляются.
- **D-20:** Шаблонный код и черновики тестов допускается делегировать Antigravity только через `scripts/agy_task.sh` (skill `agy-delegate`) с ревью патча Claude; запускать `agy` напрямую запрещено; NDA-рабочие пространства агентам не отдаются.

### Claude's Discretion

Все четыре темы отданы владельцем на усмотрение Claude. Планировщик дополнительно вправе выбрать: структуру пакета `src/persona/`, имена полей Pydantic-моделей сверх blueprint 3.1, формат файла baseline-allowlist, способ подготовки персоны в тестах chat-app (D-04), разбиение на планы и волны — если это не нарушает D-01..D-20.

### Deferred Ideas (OUT OF SCOPE)

- Переписывание `security_shield.py` в тонкую обёртку над общей библиотекой и pre-commit hook — Фаза 4.
- Миграции схемы и единый владелец схемы для таблиц персон — Фаза 4.
- Две персоны одновременно в одном процессе, `WorkspaceScope`, пустой allowlist сканера — Фаза 6.
- Реализация `git_source` и `notion` (роли только объявлены) — Фаза 7.
- Редактирование персоны из веб-интерфейса — вне миграции, новая возможность.
- Стартовые данные и дефолты `'Тидекс'` в `src/storage/db.py` — остаются в baseline-allowlist, переносятся не позже Фазы 6.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Описание | Какие находки research это обеспечивают |
|----|----------|-----------------------------------------|
| PER-01 | `config/persona.yaml`, Pydantic, загрузчик, `popov-da-default` без `PERSONA_CONFIG_PATH`, ID из окружения | Раздел «Схема персоны», «Загрузчик», D-05 (две ловушки: fail-open `_is_authorized`, снимок в БД хранит плейсхолдер) |
| PER-02 | Таблицы `personas`, `workspaces`, `connector_bindings`, 6 ролей, несколько привязок на роль | DDL ниже; отклонения от blueprint (составной ключ, `position`, `account`, `clearance_label`) обоснованы 1:1 выводом Security Tile |
| PER-03 | `PROJECTS_REGISTRY` удалён, Security Tile из `workspaces`, вывод идентичен | Дословные сегодняшние значения; порядок записей отличается от blueprint; fail-closed при пустой персоне |
| PER-04 | NDA-правила — данные, `is_tydex` → `clearance`, тест эквивалентности | Явный чек-лист из 20+ проверок (разд. «NDA-чек-лист»), семантика ключевых слов, расхождение Web и скриптов |
| PER-05 | UI из `/api/v1/persona/current`, дефолт области из персоны | Фактическая картина: 5 кнопок фильтра и 6 опций формы (не 2), тексты Security Tile, DDL-дефолт |
| PER-06 | Параметры коннекторов из данных | Аудит с файлами и строками (разд. «Аудит хардкода»), инжекция через `composition.py`, ловушка характеризационных тестов Фазы 2 |
| PER-07 | Промпты в Jinja2 со снимком | Построчная карта статики и динамики, падежи имени, ловушка `.gitignore` (`data/`), ловушка `{{`, ловушка завершающего перевода строки |
| PER-08 | Сканер хардкода + baseline, который не растёт | Дизайн сканера, текущие счётчики по файлам, ловушка `shield --all` на NDA-словах в `persona.yaml` |
| PER-09 | `test_persona_config.py` со второй персоной | Конвертер dict → конфиг, загрузка JSON как YAML (chat-app без PyYAML), определение «scope-решений» |
| BCK-01 | Дефолтная персона 1:1 | Снимки, эталон порядка и строк Security Tile, правило «env-переопределения сильнее персоны» |
| BCK-02 | Тесты хардкода переписаны, не ослаблены | Список тестов и способ переписывания каждого |
</phase_requirements>

## Summary

Фаза переносит профиль владельца из кода в данные без изменения видимого поведения. Главные факты, которые меняют план по сравнению с CONTEXT: (1) боевая БД не содержит таблиц персон (проверено только на чтение: 34 таблицы, ни одной из трёх); (2) `tests/data/` в assistant-core игнорируется git (`.gitignore:20: data/`), поэтому эталоны промптов нельзя класть в `tests/data/`; (3) положить три NDA-слова в `config/persona.yaml` нельзя без решения владельца: `security_shield.py --all` краснит любой отслеживаемый файл с ними, а список известных находок гейта заморожен тестом на ровно 15; (4) у интерфейса не 2 области задач, а 6 значений (5 кнопок фильтра, 6 опций формы), а Security Tile Web-аудита не проверяет ключевые слова вообще (проверяют только скрипты); (5) имя владельца в промптах стоит в 4 падежах, поэтому «имя из персоны» требует форм имени в данных, а длинные описания дисциплин, ящиков и регламентов остаются литеральным текстом шаблона `*_default.jinja2` (данные персоны, а не код).

Рекомендованная архитектура: загрузчик и модели в новом пакете `src/persona/` assistant-core (чистый, без импорта `src.config`, который делает `load_dotenv(override=True)`); таблицы создаёт `Database.init_db()`; для подготовки БД есть одна точка кода: CLI `python -m src.persona.seed --db PATH [--persona-config FILE]`. chat-app читает таблицы через `DatabaseService`; его тестовая фикстура на сессию делает копию БД (sqlite backup, источник только на чтение), засевает персону вызовом seed-CLI в venv assistant-core и подменяет `settings.SQLITE_DB_PATH`. Это решает D-04 и для гейта, и для ручного запуска по CLAUDE.md, и не пишет в боевую БД. Вторая персона: тот же `synthetic_persona.py` (два байт-в-байт файла, SHA-256 остаётся) получает чистую функцию-конвертер dict → конфиг; chat-app пишет конфиг как JSON (JSON — подмножество YAML, `yaml.safe_load` его читает), поэтому PyYAML в chat-app по-прежнему не нужен.

**Primary recommendation:** Порядок волн как в D-19, но (a) перед заменой `PROJECTS_REGISTRY` отдельным коммитом зафиксировать характеризационный тест NDA-чек-листа на текущем коде (паттерн Фазы 2), (b) схему персоны утвердить целиком в волне 2 (все поля для UI, промптов и коннекторов), чтобы не менять её три раза, (c) два вопроса вынести владельцу до исполнения: NDA-слова в `persona.yaml` против замороженного списка shield, и адреса почты владельца внутри шаблонов и эталонов.

## Project Constraints (from CLAUDE.md)

- Весь пользовательский вывод — по-русски (Telegram-бот, веб-интерфейс); код и коммиты — по-русски или по-английски.
- KISS/YAGNI; типизированные dataclass и Pydantic-модели.
- Async-first: БД через `aiosqlite`, сеть через `httpx`/`aiohttp`.
- 100% pytest в обоих репозиториях; команды: `/opt/chat-app/backend/.venv/bin/pytest backend/tests`, `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests`.
- Гейт: `python3 /opt/chat-app/scripts/gate.py` (оба pytest, import-linter, security_shield; exit 0 = «ЗЕЛЁНЫЙ»).
- HITL для деструктивных действий; строгий air-gap NDA; NDA-пространства агентам Antigravity не отдаются.
- `agy` только через `scripts/agy_task.sh` (никогда напрямую); результат возвращается патчем на ревью.
- Перезапуск сервисов только если менялись; в этой фазе сервисы остаются остановленными (STATE.md, требование 6 сквозных критериев), проверка опирается на тесты.
- Из памяти проекта: весь текст владельцу по-русски; вопросы владельцу только через AskUserQuestion с вариантами.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Хранение и валидация персоны (YAML, Pydantic, `${ENV}`) | assistant-core: `src/persona/` | — | D-01: единственный загрузчик; chat-app без PyYAML |
| Таблицы `personas/workspaces/connector_bindings` | Database/Storage (`src/storage/db.py`) | — | D-02: существующий механизм `init_db()`; все SQL assistant-core уже там |
| Чтение персоны и пространств для Web | API/Backend chat-app (`DatabaseService`, `/persona/current`) | Database | D-03: читает таблицы, не файл |
| Security Tile / NDA-аудит из данных | API/Backend chat-app (`security.py`) | Database | Правила приходят из `workspaces`; логика проверок остаётся в `security.py` |
| Белая-метка интерфейса (имя, области, тексты) | Browser/Client (`index.html` + JS) | API (`/persona/current`) | Статика нейтральна; данные подставляются после fetch |
| Рендер промптов | assistant-core `src/persona/prompts.py` (Jinja2 sandbox) | `src/brain/*` потребители | Один путь рендера для всех промптов и обеих персон |
| Параметры коннекторов | Корень композиции `src/composition.py` | `src/persona` (источник) | D-18: фабрики получают конфиг привязки; адаптеры значений не знают |
| Сканер хардкода и baseline | Тесты обоих репозиториев (pytest) | gate | PER-08; без внешнего CI |
| Подготовка БД для тестов chat-app | Тестовая фикстура chat-app (+ seed-CLI assistant-core) | gate (контроль SHA-256) | D-04; боевая БД не меняется |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.6 [VERIFIED: `pip index versions jinja2` в `/opt/assistant-core/.venv`, последняя 3.1.6] | Рендер системных промптов | Решение владельца (PER-07); `SandboxedEnvironment` + `StrictUndefined` |
| MarkupSafe | 3.0.3 [VERIFIED: pip index versions] | Транзитивная зависимость Jinja2 | Ставится вместе с ней |
| PyYAML | 6.0.3 уже в `.venv` assistant-core [VERIFIED: `pip list`; «Required-by: ctranslate2, huggingface_hub»] | `yaml.safe_load` персоны | Только транзитивная: добавить прямой `pyyaml>=6.0` в `requirements.txt` (в нём его сейчас нет) |
| Pydantic | 2.13.5 в обоих `.venv` [VERIFIED: pip list] | Модели и валидация персоны | Уже стандарт проекта |
| aiosqlite | 0.22.1 в обоих `.venv` [VERIFIED: pip list] | Чтение/запись таблиц персон | CLAUDE.md: async-first |
| pytest / anyio / pytest-asyncio | 9.1.1 / 4.15.1 / 1.4.0 (auto) [VERIFIED: docs/BASELINE.md, pytest.ini] | Тесты | Уже настроены |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| import-linter | 2.15 [VERIFIED: docs/BASELINE.md] | Контракты слоёв | Добавить `src.persona` в `core-is-pure` и (по желанию) контракт «persona чиста» |
| stdlib `json`, `sqlite3`, `subprocess`, `re` | — | seed-CLI в тестовой фикстуре, backup копии БД, сканер | chat-app без новых зависимостей |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Один шаблон-обобщение на всех персон | Отдельный шаблон на персону (`*_default.jinja2` + шаблоны синтетической персоны) | Обобщённый шаблон утащит факты владельца (ящики, группы, приказы) в промпт чужой персоны; отдельные шаблоны — данные персоны, 1:1 тривиален. Рекомендовано второе |
| Генерировать PyYAML-файл из dict в chat-app | JSON-файл (подмножество YAML) | Не нужен PyYAML в chat-app; `yaml.safe_load` в assistant-core читает JSON |
| Подготовка копии только в `gate.py` | Фикстура chat-app на сессию | Фикстура работает и под гейтом, и при ручном запуске по CLAUDE.md; шаг в гейте остаётся допустимым, но избыточен |

**Installation (только после одобрения владельца, см. аудит пакетов):**
```bash
cd /opt/assistant-core && .venv/bin/pip install "jinja2==3.1.6"   # MarkupSafe 3.0.3 подтянется сама
# requirements.txt: добавить строки jinja2>=3.1,<4 и pyyaml>=6.0
```
**Version verification:** `pip index versions jinja2` вернул 3.1.6 (последняя); `pip download jinja2==3.1.6 markupsafe --no-deps` в каталог scratchpad прошёл (сеть доступна, колёса скачаны, `.venv` не менялся). Системный `python3` содержит Jinja2 3.1.2: на нём прогнаны все проверки рендера из этого документа.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| jinja2 | PyPI | 3.1.6 опубликована 2025-03-05 (проект Pallets, >10 лет) | seam: «unknown» (инструмент не получает число) | github.com/pallets/jinja | SUS (только `unknown-downloads`) | Flagged: планировщик добавляет `checkpoint:human-verify` перед установкой (как для import-linter в Фазе 1) |
| markupsafe | PyPI | 3.0.3 (2025-09-27, Pallets) | unknown | github.com/pallets/markupsafe | SUS (`unknown-downloads`) | Ставится транзитивно с jinja2; один и тот же чекпоинт |
| pyyaml | PyPI | 6.0.3 (2025-09-25) | unknown | pyyaml.org | SUS (`unknown-downloads`) | Уже установлена транзитивно; ничего не ставится, только строка в `requirements.txt` |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** jinja2, markupsafe, pyyaml. Причина у всех трёх одна и та же: сервис `package-legitimacy` не может получить число загрузок PyPI (`weeklyDownloads: null`); сигналы существования, репозитория и отсутствия postinstall в норме. Планировщик вставляет `checkpoint:human-verify` перед `pip install` (достаточно одного на jinja2+markupsafe). [VERIFIED: `gsd-tools query package-legitimacy check --ecosystem pypi jinja2 pyyaml markupsafe`]

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
 PERSONA_CONFIG_PATH│ config/persona.yaml (default, shipped)       │
 (env, optional) ──►│ config/prompts/*_default.jinja2              │
                    └───────────────┬─────────────────────────────┘
                                    │ yaml.safe_load + ${ENV} resolve
                                    ▼
                  assistant-core: src/persona/{models,loader}.py (Pydantic)
                     │                    │                       │
       current_persona() (ContextVar)     │ seed CLI              │ render_prompt()
                     │                    ▼                       ▼
        ┌────────────┴─────┐   Database.init_db() + upsert   Jinja2 SandboxedEnvironment
        │ composition.py   │   ┌───────────────────────┐     (StrictUndefined,
        │ brain/*          │   │ SQLite assistant.db    │      keep_trailing_newline)
        │ models/schedule  │   │ personas / workspaces  │            │
        │ main.py          │   │ connector_bindings     │            ▼
        └──────────────────┘   └───────────┬───────────┘     system_instruction → Gemini
                                           │ read-only (aiosqlite)
                                           ▼
                     chat-app: DatabaseService.get_persona / list_workspaces
                        │                                   │
        /api/v1/persona/current (whitelist)     /api/v1/security/overview, /audit
                        │                          (workspaces → audit_path → NDA rules)
                        ▼
                 index.html (fetch → шапка, области, тексты Security Tile)

 Тесты chat-app:  conftest (session) → sqlite backup копии БД → seed-CLI (venv assistant-core)
                  → settings.SQLITE_DB_PATH = копия → тесты читают персону из таблиц
 Гейт: оба pytest + lint-imports + shield + дрейф synthetic_persona + SHA-256 боевой БД
```

### Recommended Project Structure
```
/opt/assistant-core/
├── config/
│   ├── persona.yaml                     # popov-da-default (данные; в allowlist сканера)
│   └── prompts/                         # *_default.jinja2 (данные; НЕ каталог с именем data/)
├── src/persona/
│   ├── models.py                        # Pydantic v2: PersonaConfig, WorkspaceConfig, BindingConfig, ...
│   ├── loader.py                        # load_persona(path|None, env) -> PersonaConfig; ${ENV}; safe_load
│   ├── current.py                       # current_persona(), use_persona() (ContextVar), reset_cache()
│   ├── prompts.py                       # render_prompt(persona, key, **runtime_vars)
│   └── seed.py                          # python -m src.persona.seed --db PATH [--persona-config FILE]
├── src/storage/db.py                    # + 3 CREATE TABLE IF NOT EXISTS, upsert_persona/get_persona
├── src/composition.py                   # фабрики получают binding-конфиг
├── tests/fixtures/prompts_snapshot/     # эталоны промптов (НЕ tests/data/: игнорируется git)
└── tests/test_{prompt_snapshot,persona_loader,persona_storage,persona_config,
              connector_params,hardcode_scanner,nda_script_parity}.py
/opt/chat-app/backend/
├── app/api/v1/persona.py                # GET /persona/current
├── app/api/v1/security.py               # workspaces из БД; PROJECTS_REGISTRY удалён
├── app/db.py                            # get_persona(), list_workspaces(), resolve_default_area()
├── app/core/config.py                   # + PERSONA_ID: str = "popov-da-default"
└── tests/{conftest.py, test_persona_api.py, test_nda_equivalence.py,
          test_hardcode_scanner.py, test_index_whitelabel.py}
```

### Pattern 1: Характеризация до рефакторинга (унаследовано из Фазы 2)
**What:** тест, фиксирующий сегодняшнее поведение, коммитится ОТДЕЛЬНО и ДО правки продакшен-кода; потом правка; тест остаётся зелёным. Проверка порядка — `git log -S`/`merge-base`.
**When to use:** снимок промптов (волна 1), NDA-чек-лист на текущем `security.py` и скриптах (перед заменой `PROJECTS_REGISTRY`), вывод `/security/overview` с 4 записями (дословный эталон), `format_academic_lesson_line`, `_search_local_files_context`.
[VERIFIED: `.planning/phases/02-.../02-01-SUMMARY.md` — «Характеризационный тест закоммичен отдельно до правки src»]

### Pattern 2: Захват промпта по месту вызова
**What:** для динамических промптов (`SCOPE_CHECK_PROMPT.format(question=...)`, два `system_instruction` в `summarizer.py`) эталон снимается подменой клиента Gemini: фейковый `client.aio.models.generate_content` запоминает `config.system_instruction` и `contents`. Это реальный текст, который уходит модели, без рефакторинга метода. Те же захваты проверяют ПОСЛЕ переноса, что потребитель получает ровно тот же текст (двойная проверка: «шаблон = эталон» и «вызов LLM = эталон»).
**Example:** ссылки на места вызова: `secretary_dialog.py:698`, `intent_router.py:247`, `methodist.py:614` и `:479`, `reply_generator.py:103,143`, `debrief_parser.py:118`, `summarizer.py:199,407`.

### Pattern 3: Один путь кода для обеих персон
`current_persona()` возвращает персону из `ContextVar` (если установлена `use_persona(p)`), иначе кэш загрузки `PERSONA_CONFIG_PATH` или встроенного дефолта. Потребители (`brain/*`, `composition.py`, `models/schedule.py`) вызывают его во время работы, а не при импорте модуля, иначе вторая персона в тесте не подхватится. ContextVar пригодится и Фазе 6 (ISO-04) [ASSUMED: форма API на усмотрение планировщика].

### Pattern 4: Фиксированный список остаточного долга по образцу гейта Фазы 1
Baseline сканера: словарь `(путь, токен-класс) → максимум вхождений`; тест красный и на ПРЕВЫШЕНИИ, и на УСТАРЕВШЕЙ записи (счётчик в коде стал меньше записанного: запись надо уменьшить в том же коммите). Готовая модель — `compare_shield_findings()` в `scripts/gate.py:354-368` [VERIFIED: прочитано]. Хранить как `tests/hardcode_baseline.py` (обычный dict) в обоих репозиториях.

### Anti-Patterns to Avoid
- **Класть эталоны в `tests/data/`:** каталог игнорируется (`.gitignore:20`), эталоны не попадут в коммит. Использовать `tests/fixtures/prompts_snapshot/`.
- **Импортировать `src.config` из `src/persona/`:** `load_dotenv(..., override=True)` перебивает окружение; seed-CLI всегда получает путь БД аргументом.
- **Менять вызовы `get_monthly_pacing(project_name="Тидекс")` на вызовы без аргумента:** характеризационные тесты Фазы 2 проверяют именно `{"project_name": "Тидекс"}` (`tests/test_composition_di.py:247,351,592,637`). Правильно: оставить аргумент и брать значение из персоны.
- **Подставлять пустую строку вместо незаданного `${TELEGRAM_USER_ID}`:** `EmailBotHandler._is_authorized` возвращает `True` при `allowed_user_id is None` (`bot_handler.py:100-103`): пустое значение открывает бота всем.
- **Показывать «0 пространств, чисто» при отсутствующей персоне:** Security Tile обязан падать закрыто (503 или статус `alert`), а не рисовать «защищено».

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Шаблонизация промптов | Свой `str.replace`/f-строки в runtime | Jinja2 `SandboxedEnvironment` | Решение PER-07; песочница закрывает SSTI, если шаблон когда-нибудь станет пользовательским |
| Разбор YAML | Свой парсер/`yaml.load` | `yaml.safe_load` | `yaml.load` без Loader исполняет теги Python |
| Валидация схемы персоны | Ручные `if key in dict` | Pydantic v2 (`extra="forbid"`, валидаторы) | Ловит опечатки в именах полей и дубли привязок до записи в БД |
| Копия боевой БД для тестов | `shutil.copy` | `sqlite3.Connection.backup()` с `mode=ro` | Уже так сделано в `gate.py:97-113`; консистентный снимок без файлов рядом с боевой БД |
| Сравнение найденного и разрешённого долга | Новый формат | Паттерн `compare_shield_findings` | Уже проверен тестами Фазы 1 |
| Поиск репозиториев для NDA-теста | Мок `subprocess` | Настоящие временные git-репозитории (`git init`, `git remote add`) | Обе реализации (Web и скрипт) вызывают реальный `git`; мок скроет расхождения |

**Key insight:** сложность фазы не в Jinja2 и не в YAML, а в 1:1-эквивалентности: порядок записей, эмодзи, падежи имени, завершающий перевод строки, набор блокируемых нарушений. Всё, что можно зафиксировать эталоном до правки, фиксируется эталоном.

## Runtime State Inventory

Фаза «хардкод → данные», runtime-состояние есть. Сервисы заморожены и не запускаются.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Боевая `assistant.db` (7.7 МБ): 34 таблицы, таблиц персон нет; `tasks.area` содержит значения «ГУАП» и «Тидекс», проектов 5, задач 3, напоминаний 2, документов 1 [VERIFIED: sqlite3 `mode=ro&immutable=1`]. DDL `tasks.area ... DEFAULT 'ГУАП'`, `projects.area ... DEFAULT 'ГУАП'`, `timesheet_records.project_name ... DEFAULT 'Тидекс'` (`src/storage/db.py:148,162,199`) | Строки `area` не трогать (D-11). Существующие таблицы `CREATE TABLE IF NOT EXISTS` не изменит; DDL-дефолт оставить в baseline-allowlist, а все пути вставки (chat-app `db.py:149,244` и Pydantic) передают `area` явно из персоны. Миграция данных не нужна; код-правка |
| Live service config | Сервисы остановлены и сняты с автозапуска (STATE.md). Конфигурации вне git, содержащей строки профиля, не найдено в пределах доступного (файлы unit не читались по OPS-02) | Нет; проверено по STATE.md, unit-файлы не открывались |
| OS-registered state | systemd-юниты `assistant-worker`, `chat-app`, `dev-bridge`: имена не содержат переименовываемых строк | Нет. Новые переменные (`PERSONA_CONFIG_PATH`, `PERSONA_ID`) в юниты НЕ добавляются; дефолты кода воспроизводят сегодняшнее поведение (BCK-01) |
| Secrets/env vars | `TELEGRAM_USER_ID`, `SCHEDULE_URL`, `SCHEDULE_TARGET_ID`, `GMAIL_EMAIL`/`MAILRU_EMAIL`/`GUAP_*` читаются из окружения в `src/config.py` (`.env` не читался) | Код-правка: имена переменных не меняются. Правило: env-переопределение остаётся сильнее персоны (см. A1) |
| Build artifacts | `.venv` обоих репозиториев: Jinja2 отсутствует; PyYAML только транзитивный; в корне assistant-core лежат каталог `sqlite+aiosqlite:` и пустая `assistant.db` (побочные эффекты тестов, Фаза 1) | Установить Jinja2 в `.venv` assistant-core (изменение окружения вне git, записать версию в `docs/BASELINE.md`); `requirements.txt`: `jinja2`, `pyyaml` |

## Аудит хардкода профиля (PER-06, PER-08)

Состояние assistant-core: токены профиля (ГУАП/GUAP/Тидекс/Tydex/Попов/аккаунт/ящики) найдены в 21 файле `src/` и 12 файлах `scripts/` [VERIFIED: `grep -rIlE` в этой сессии]. Мигрировать нужно только то, что перечислено в PER-06 и D-08; остальное остаётся в baseline (Фаза 6).

### Мигрирует в Фазе 3 (PER-06 / D-08 / D-13)

| Параметр | Где зашит (проверено) | Куда в персоне | Заметка |
|----------|----------------------|----------------|---------|
| Проект учёта по умолчанию «Тидекс» | `src/main.py:296`, `src/notifier/live_ticker.py:123`, `src/notifier/bot_handler.py:1114,1170`, `src/brain/secretary_dialog.py:144`; дефолты `src/connectors/aadhk/parser.py:64,104,409,433` | `connectors.timesheet[0].config.default_project` | Вызовы сохраняют аргумент `project_name=` (ловушка характеризации Фазы 2) |
| Норма 8.5 ч/день | `parser.py:432` (`daily_norm: float = 8.5`), тексты `bot_handler.py:1124`, `secretary_dialog.py:152` («по 8.5 ч»); промпты | `...config.daily_norm_hours` | Форматировать `f"{norm:g}"` (8.5 → «8.5», 6.0 → «6»); текст характеризации `test_composition_di.py:41` ждёт «по 8.5 ч» |
| Короткие названия предметов | `src/models/schedule.py:94-99` и ДУБЛЬ `src/calendar/client.py:13-18`: «физические основы нанотехнологий»→«ФОНТ», «основы проектной деятельности в профессии»→«ОПДвП», «основы проектной деятельности»→«ОПД», «физика»→«Физика» | `connectors.schedule_source[0].config.subjects` | Один источник вместо двух; `live_ticker.py:30` импортирует `SUBJECT_SHORT_NAMES` из `models.schedule` |
| Слоты расписания | `src/models/schedule.py:76-84`: `"09:30": 1, "11:10": 2, "13:00": 3, "15:10": 4, "17:00": 5, "18:40": 6, "20:20": 7`; допуск ±15 минут в `get_guap_pair_number` | `...config.lesson_slots` (список объектов `{number, start}`) | Формат синтетической персоны `{1: ("08:15","09:45")}` содержит конец пары; у владельца конца нет в коде: поле `end` необязательное |
| Адрес сайта расписания | `src/config.py:18` `SCHEDULE_URL = os.getenv("SCHEDULE_URL", "https://guap.ru/rasp")`; дефолт параметра `parser/schedule_parser.py:27` — другой: `"https://rasp.guap.ru/"`; `main.py:582-583` передаёт `config.SCHEDULE_URL` | `...config.base_url` | Два разных значения в коде. Боевое значение определяет `.env` (не читался): см. A1 |
| Адрес личного кабинета | `src/connectors/guap_lms/client.py:33` `self.base_url = "https://pro.guap.ru"`; ссылка в `main.py:438` | `connectors.lms[0].config.base_url` | Хост ещё в проверке `"pro.guap.ru" in str(r_post.url)` (client.py:103) и в `sso.guap.ru` — часть протокола входа, остаётся в baseline |
| Каталог методических файлов | `src/brain/methodist.py:75-76` (`/opt/assistant-core/data/methodist/{raw,knowledge_base}`), `src/brain/secretary_dialog.py:268` и список `catalog` из 7 файлов (`:273-324`) | `methodist.raw_dir`, `methodist.kb_dir`, `methodist.file_catalog` | Пути абсолютные: хранить как есть (W6). Тест `test_search_local_files_catalog` (`tests/test_secretary_dialog.py:141`) требует существования каталога на диске |
| Правила области методиста | `methodist.py:447-470`: списки `out_of_scope_keywords` (содержит «тидекс», «табель») и `academic_keywords` (содержит «попов», «гастелло», «коваленко») | `scope.out_of_scope_keywords`, `scope.academic_keywords` | Это и есть «scope-решения» второй персоны (см. Open Questions 5) |
| Дефолт области | chat-app `db.py:149,244`, `dashboard_schemas.py:8,33`; assistant-core `storage/db.py:1540,1629` (Python-дефолты без вызывающих в `src/`) | `default_area` | assistant-core: либо аргумент обязательный, либо `None` → персона |
| Промпты | см. раздел «Промпты» | `prompts.*` | 8 мест по D-08 + 1 пропущенное |

### Остаётся в baseline-allowlist (остаточный долг, не мигрируем)
`src/storage/db.py` (36 вхождений: DDL-дефолты, стартовые данные 1446-1512, факты памяти 2807-2842); `src/collector/email_collector.py` (33: категории `guap_student`/`guap_dept`, имена IMAP-папок, домены отправителей); `src/notifier/bot_handler.py` (47: тексты интерфейса Telegram, `/lms_create ... Попов`), `src/notifier/live_ticker.py` (18: подписи экранов), `src/notifier/telegram.py`, `src/sender/email_sender.py:33` (подпись `From`), `src/config.py` (10: имена переменных `GUAP_*`), `src/models/second_brain.py:24-25` (enum `Area`, связан со схемой Notion), `src/brain/debrief_parser.py` (`_guess_area`, `_guess_project`), `src/connectors/*` (SSO-хосты), `scripts/*` (12 файлов, включая обе копии `security_shield.py`), `src/main.py` (остаток после выноса проекта учёта). Точные счётчики baseline генерируются программой в последнем плане, а не вручную: числа выше — состояние на дату исследования.

## Промпты (PER-07, D-07..D-10): построчная карта

Все длины и признаки получены разбором AST (без импорта модулей, `.env` не затрагивался) [VERIFIED: скрипт в scratchpad].

| Промпт | Файл:строки | Символов | Завершается `\n` | Динамика | Падежи/формы имени |
|--------|-------------|----------|------------------|----------|--------------------|
| `SECRETARY_SYSTEM_PROMPT` | `secretary_dialog.py:37-62` | 2718 | да | нет (0 фигурных скобок); контекст дня идёт отдельно в `user_prompt` (`:675-683`), не в системном | род. «Попова Дмитрия Александровича», им. «Попов Дмитрий Александрович», дат. «Дмитрию Александровичу», «Попова Д.А.» |
| `ROUTER_SYSTEM_PROMPT` | `intent_router.py:28-65` | 3269 | да | нет; 2 скобки — JSON-пример (`{`…`}`) | род. «Попова Дмитрия Александровича» |
| `METHODIST_SYSTEM_PROMPT` | `methodist.py:23-48` | 4434 | да | нет | им. «Попов Дмитрий Александрович», «Д.А. Попова», «Д.А. Попова» |
| `SCOPE_CHECK_PROMPT` | `methodist.py:50-60` | 646 | да | `.format(question=...)` (`:479`); в тексте `{question}` и экранированные `{{`/`}}` | нет |
| `SYSTEM_PROMPT` | `reply_generator.py:12-30` | 1346 | да | нет | им. «Попов Дмитрий Александрович», подпись «Дмитрий Александрович Попов» |
| `DEBRIEF_SYSTEM_PROMPT` | `debrief_parser.py:26-53` | 1861 | НЕТ | нет; склеивается с `user_prompt` через `f"{DEBRIEF_SYSTEM_PROMPT}\n\n{user_prompt}"` (`:118`) | род. «Попова Дмитрия Александровича», «Дмитрия Александровича», твор. «Дмитрием Александровичем» |
| `system_instruction` утренний | `summarizer.py:154-193` | динамика | — | f-строки: дата `%d.%m.%Y` и день недели | «Попов Д.А.» |
| `system_instruction` вечерний | `summarizer.py:383-402` | динамика | — | f-строки: дата, день недели, дата завтра | «Попов Д.А.» |
| Описание скриншота (OCR) | `bot_handler.py:1022` | — | — | — | токенов профиля нет; в D-08 не упомянут; переносить не нужно |

**Выводы для плана:**
1. **Падежи.** Имя владельца стоит в 4 падежах и в 3 краткостях. Генерировать падежи из одного поля невозможно, поэтому персоне нужны формы имени (`name_forms`: nominative, genitive, dative, instrumental, short, short_genitive, signature) [ASSUMED: схема на усмотрение планировщика]. Без этого параметризация даст неграмотный русский.
2. **Что параметризовать.** Идентичность (формы имени, титул, названия вуза и компании, норма, проект учёта) идёт через `{{ }}`. Длинные описания дисциплин, почтовых ящиков, студенческих групп, приказов и регламентов остаются литеральным текстом файла `*_default.jinja2`: это данные персоны, а не код (в allowlist сканера). D-09 («только статические данные: имя, титул, организации, нормы») этим не нарушается, но «всё в переменные» привело бы к десяткам полей без пользы (YAGNI). Для второй персоны — собственные шаблоны в тестовых фикстурах.
3. **`DEBRIEF_SYSTEM_PROMPT` без завершающего `\n`:** файл шаблона не должен его иметь. Редакторы и `Write` часто добавляют перевод строки; эталон надо сравнивать побайтно (`read_bytes()`), `keep_trailing_newline=True` сохраняет то, что есть в файле.
4. **Ловушка `{{`:** в `SCOPE_CHECK_PROMPT` сырой строки Python стоит `{{`/`}}` (экранирование `.format`). Результат после `.format` — одинарные скобки. В Jinja-шаблоне пишется ОДИНАРНАЯ скобка, плейсхолдер `{{ question }}`; копирование `{{` из исходника даёт `TemplateSyntaxError` [VERIFIED: прогон на Jinja2 3.1.2].
5. **Динамика summarizer.** Если выносить, шаблону нужны переменные `date_str`, `weekday` (и `tomorrow_*` для вечернего); эталон снимается захватом по месту вызова (паттерн 2) при фиксированных входах. Допустимо оставить в baseline-allowlist с явной записью (D-08).
6. **Потребители.** `tests/test_fast_intent_router.py:8` импортирует `ROUTER_SYSTEM_PROMPT` (импорт без использования): при удалении константы импорт надо поправить; это не ослабление.
7. **Эталон хранить в `tests/fixtures/prompts_snapshot/`**, файлы без перевода строки в конце ровно там, где его нет в оригинале; рядом `MANIFEST.json` (имя, длина, SHA-256). Писать/читать в бинарном режиме.
8. **Содержимое эталона.** Тексты содержат адреса почты владельца и номер приказа. Это те же данные, что уже лежат в `src/brain/secretary_dialog.py`; shield их не флагует. Требование 7 сквозных критериев («нет e-mail») формально нарушается уже сегодня: вопрос владельцу (Open Questions 2).

**Проверенное поведение Jinja2** (прогон на системном `python3`, Jinja2 3.1.2) [VERIFIED: scratchpad]:
- `keep_trailing_newline=False` (умолчание) отрезает завершающий `\n`; с `True` сохраняет; шаблон без `\n` в конце остаётся без него.
- `StrictUndefined` бросает `UndefinedError` на неизвестной переменной.
- CRLF в исходнике нормализуется в `\n` (в промптах только `\n`, но файл шаблона должен быть с `\n`).
- `{% for %}` без `{%-` добавляет пустые строки; для списков используйте `{%-` и проверяйте эталоном.

## NDA-чек-лист (PER-04, W3, W4, D-15)

Сначала факты, потом чек-лист. Источники: `backend/app/api/v1/security.py` (Web), `scripts/security_shield.py` (обе копии БАЙТ-в-БАЙТ одинаковы: `diff` без различий [VERIFIED]).

### Принципиальные расхождения (чек-лист обязан их зафиксировать, а не «выровнять»)

| # | Расхождение | Web (`security.py`) | Скрипты (`security_shield.py`) |
|---|-------------|---------------------|-------------------------------|
| 1 | Определение NDA-репозитория | `clearance == "restricted_nda"` из реестра (`:140`, `:180`) — уже по допуску, не по id | `"tydex" in str(repo_path).lower()` (`:109`) — подстрока ПУТИ, включая родительские каталоги |
| 2 | Запрещённые слова NDA | НЕ проверяются вообще | Проверяются по строкам во всех НЕ-NDA репозиториях (`is_public_repo = not is_tydex_repo`, `:126`; цикл `:91-93`) |
| 3 | Набор секретных шаблонов | 6 шаблонов (`:13-20`) | 7: дополнительно «Generic Bearer Secret» (`:25`) |
| 4 | Какие файлы | `git ls-files`, первые 100 (`:100`) | staged → иначе modified; с `--all` — все `git ls-files` без лимита |
| 5 | Запрещённый файл | нарушение, но содержимое файла всё равно сканируется (`:104-117`) | нарушение и ранний выход для файла (`:73-78`) |
| 6 | Таймаут `git` | 10 с (`:73`) | нет |

**Семантика слов (важно для W4):** три слова хранятся как `CORPORATE_NDA_KEYWORDS` (`security_shield.py:38-42`; три слова здесь намеренно НЕ цитируются: shield `--all` краснит любой отслеживаемый файл, где они встречаются). Они запрещены в НЕ-NDA репозиториях («must never appear in public / student repos»), а внутри NDA-репозитория не проверяются. Формулировка W4 («restricted_nda — дополнительно remote, запрещённые слова») читается двояко; чтобы набор блокируемых нарушений не сузился, данные `forbidden_keywords` хранятся у NDA-пространства, а применяются к ВСЕМ остальным пространствам персоны (объединение по NDA-пространствам). Реализация «сканировать NDA-репозиторий его же словами» дала бы ложные срабатывания и другое поведение [ASSUMED: толкование W3/W4, Open Questions 4].

**Вывод для Web:** по умолчанию Web-аудит НЕ получает проверку слов в Фазе 3. Добавление расширило бы блокировку, но результат `test_security_audit_all` (`status == "passed"`) стал бы зависеть от числа отслеживаемых файлов: файлы с этими словами в chat-app (`docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md`, `scripts/security_shield.py`) стоят в `git ls-files` на позициях 107 и 118 [VERIFIED: `git ls-files | grep -n`, всего 118 файлов], то есть сегодня лишь на 7 позиций за окном в 100 файлов; любое удаление файлов выше по алфавиту втянет их в окно, и тест покраснеет. Правило 1:1 (BCK-01): Web-проверка слов не включается; чек-лист записывает «Web: нет проверки слов (расхождение, закрывает Фаза 4, SEC-01/02)». Новые отслеживаемые файлы с ранним алфавитным путём сдвигают окно в безопасную сторону, а не наоборот.

### Явный чек-лист (каждый пункт = тест на живых временных git-репозиториях; «+» позитив, «−» негатив)

| ID | Проверка | Surface | Тест |
|----|----------|---------|------|
| N01 | Каталога нет → `virtual_airgap`, `exists False`, `scanned_files 0`, `origin_url "N/A"`, `author_email "N/A"`, сообщение «Директория изолирована…» | Web | + для NDA и internal (оба сегодня отсутствуют на диске) |
| N02 | NDA-пространство: remote содержит запрещённую подстроку → «CRITICAL: Проект Тидекс скомпрометирован: remote указывает на личный публичный аккаунт!» | Web | + |
| N03 | NDA-пространство: remote БЕЗ подстроки → нет нарушения | Web | − |
| N04 | НЕ-NDA пространство с той же подстрокой в remote → нет нарушения (сегодня публичные репозитории владельца законно на этом аккаунте) | Web | − (негатив, ловит «расширили слишком» и «перепутали направление») |
| N05 | NDA-пространство без `origin` (код `git` ≠ 0) → нарушения по remote нет | Web | − |
| N06 | Запрещённые имена файлов (`.env` и его варианты, `credentials.json`, `token.json`, `*.session`, `*.session-journal`, `*.pem/.key/.pkcs12/.pfx`) → «Запрещенный файл обнаружен в репозитории: …» | Web | + по шаблону |
| N07 | Секретные шаблоны (6): Private Key, GitHub PAT, Google API Key, Telegram Bot Token, OpenAI/Anthropic, Notion | Web | + по шаблону; в тесте строки собираются из частей, чтобы файл теста не срабатывал на shield |
| N08 | Лимит 100 файлов: 101-й файл с секретом НЕ находится Web (зафиксированное поведение) | Web | фиксирует границу |
| N09 | Таймаут `git` 10 с → `(1, текст ошибки)` | Web | юнит |
| S01 | Определение NDA по подстроке `tydex` в пути (регистр не важен, любой родительский каталог) | скрипты | + (`.../Tydex-X/…`), − (путь без подстроки) |
| S02 | NDA-репозиторий + remote с аккаунтом → «CRITICAL: Tydex private project remote points to personal public account …» | скрипты | + |
| S03 | НЕ-NDA + то же remote → без нарушения | скрипты | − |
| S04 | Запрещённое слово в НЕ-NDA репозитории → «Found proprietary corporate keyword» (по строке, по слову) | скрипты | + для каждого из 3 слов, из данных NDA-пространства |
| S05 | То же слово в NDA-репозитории → без нарушения | скрипты | − |
| S06 | 7 секретных шаблонов, включая Generic Bearer (регистр не важен) | скрипты | + (Generic Bearer — только скрипты) |
| S07 | Запрещённый файл → «Forbidden file pattern committed» и ранний выход для файла (секрет внутри не добавляет нарушение) | скрипты | + |
| S08 | `--all` читает все tracked-файлы (без лимита 100); без `--all` — staged, затем modified | скрипты | + |
| S09 | Ошибка чтения файла → «Read error» как нарушение | скрипты | + |
| P01 | Правила скриптов == данные пространства по умолчанию: `CORPORATE_NDA_KEYWORDS` совпадает с `forbidden_keywords` NDA-пространства; подстрока аккаунта из исходника скрипта равна `forbidden_remote_substrings` (читается из файла скрипта в рантайме теста, не копируется литералом) | оба | «не расходятся» |
| P02 | `SECRET_PATTERNS` и `FORBIDDEN_FILES` Web — подмножество скриптов; разница ровно «Generic Bearer Secret» (регистрируется, не лечится в Фазе 3) | оба | фиксирует дрейф |
| P03 | Две копии скрипта — один хеш (assistant-core и chat-app) | оба | дрейф |
| D01 | Каждая проверка из N/S воспроизводится на ДАННЫХ: тот же набор репозиториев, но реестр построен из `workspaces` (clearance + remote-подстроки + слова); результаты Web-из-данных ≥ сегодняшних (набор блокируемых нарушений не уже) | Web из данных | эквивалентность |
| D02 | Синтетическая персона: нарушения определяются её данными (другая подстрока, другие слова), а правила владельца на её репозитории не действуют | Web из данных | PER-09 |
| D03 | «Не уже»: пространство с `clearance=restricted_nda`, но с ПУСТЫМ списком подстрок → блокировка не включается молча: проверка либо падает при загрузке конфигурации, либо отмечается в статусе (Open Questions) | данные | негатив |

**Важное следствие для Фазы 4 (записать в BASELINE):** путь-подстрока `tydex` скриптов — правило, которое тонкая обёртка обязана сохранить либо заменить поиском пространства по пути (иначе NDA-репозиторий, чей путь содержит `tydex`, но не зарегистрирован как NDA, перестанет проверяться). Тест P01/S01 перезапускается против общей библиотеки.

## Схема персоны, таблицы и API [ASSUMED: проектирование, Claude's Discretion]

### Таблицы
```sql
CREATE TABLE IF NOT EXISTS personas (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  config_json TEXT NOT NULL,            -- валидированный снимок; ${ENV}-плейсхолдеры НЕ разворачиваются
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workspaces (
  persona_id TEXT NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
  id TEXT NOT NULL,
  position INTEGER NOT NULL,             -- порядок вывода: chat-app, assistant-core, tydex-optics, guap-physics
  label TEXT NOT NULL,
  path TEXT NOT NULL,
  clearance TEXT NOT NULL CHECK (clearance IN ('public','internal','restricted_nda')),
  account TEXT NOT NULL DEFAULT '',
  clearance_label TEXT NOT NULL DEFAULT '',
  color TEXT,
  forbidden_remote_substrings TEXT NOT NULL DEFAULT '[]',
  forbidden_keywords TEXT NOT NULL DEFAULT '[]',
  PRIMARY KEY (persona_id, id)
);
CREATE TABLE IF NOT EXISTS connector_bindings (
  id TEXT PRIMARY KEY,                   -- f"{persona_id}/{role}/{binding_id}"
  persona_id TEXT NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('schedule_source','calendar_sync','timesheet','lms','git_source','notion')),
  provider TEXT NOT NULL,
  scopes TEXT NOT NULL,
  config_json TEXT NOT NULL,
  position INTEGER NOT NULL DEFAULT 0
);
```
Отличия от blueprint 3.2 и причины: (1) `position` — порядок обязателен (в blueprint 3.1 `guap-physics` стоит перед `tydex-optics`, а в сегодняшнем выводе наоборот; D-14: 1:1 побеждает); (2) `account` и `clearance_label` — это строки таблицы Web, сегодня разные у каждого пространства («🌐 Public / Open Source» у chat-app и «🌐 Public / Academic» у assistant-core), вывести из `clearance` нельзя; (3) составной ключ `(persona_id, id)` вместо `id TEXT PRIMARY KEY`: две персоны могут иметь пространство с одним id (ISO-04 в Фазе 6), а менять ключ позже — пересборка таблицы. Загрузка: в ОДНОЙ транзакции `DELETE` строк этой персоны в `workspaces` и `connector_bindings`, затем `INSERT`; `PRAGMA foreign_keys=ON` уже включён в `Database.connection()` и `get_db()`. Это замена конфигурационных строк персоны, пользовательские данные (`tasks`, `projects`, `documents`) не затрагиваются; идемпотентность проверяется тестом «дважды = то же состояние».

### Сегодняшние значения пространств (эталон 1:1)
[VERIFIED: `backend/app/api/v1/security.py:31-68`, дословно]

| id | name | path | account | clearance | clearance_label | color |
|----|------|------|---------|-----------|-----------------|-------|
| `chat-app` | «🤖 Antigravity Web Studio (chat-app)» | `/opt/chat-app` | «DimaMuhannad (Personal / Academic)» | `public` | «🌐 Public / Open Source» | `blue` |
| `assistant-core` | «⚙️ Assistant Core Daemon» | `/opt/assistant-core` | «DimaMuhannad (Personal / Academic)» | `public` | «🌐 Public / Academic» | `green` |
| `tydex-optics` | «🔬 Оптические приборы и измерения (ООО «Тидекс»)» | `/opt/work-tydex` | «ООО «Тидекс» (Corporate Organization)» | `restricted_nda` | «🔴 Restricted NDA / Air-gap» | `red` |
| `guap-physics` | «🏛️ Кафедра физики ГУАП (Лабораторные и LMS)» | `/opt/personal/guap-physics` | «DimaMuhannad (ГУАП)» | `internal` | «🟡 Internal Academic» | `yellow` |

Каталоги `/opt/work-tydex` и `/opt/personal/guap-physics` на сервере отсутствуют (`test -e`: ABSENT; содержимое не читалось). Ключи ответа `/security/overview` (сохранить): `id, name, account, clearance, clearance_label, color, path, exists, audit_status, violations_count, origin_url, author_email`; верхний уровень: `status, shield_active, air_gap_enforced, total_projects, total_violations, projects, last_checked` [VERIFIED: `security.py:131-165`].

### Схема `persona.yaml` (набросок)
Корневой ключ `persona:`; поля — `id`, `display_name`, `name_forms{genitive,dative,instrumental,short,short_genitive,signature}`, `title`, `honorific`, `timezone`, `organizations{university,company}` (имя и краткое имя), `telegram{authorized_user_ids: ["${TELEGRAM_USER_ID}"], bot_username?}`, `default_area`, `task_areas[{value,label,filter_label?,show_in_filter}]`, `ui.texts{ключ: строка}`, `workspaces[…]`, `connectors{role: [{id?, provider, scopes, config}]}`, `scope{out_of_scope_keywords, academic_keywords}`, `methodist{raw_dir, kb_dir, file_catalog}`, `prompts{ключ: относительный путь}`. Pydantic `extra="forbid"`; уникальность `(role, id)`; `clearance` — `Literal` трёх значений (совпадает с `WorkspaceClearance`).

**Значения коннекторов берутся из кода, не из blueprint** [VERIFIED: `src/*/provider.py`, `tests/test_ports_conformance.py:112-132`]:

| Роль | `connector_id` в коде | `required_scopes` в коде | В blueprint 3.1 (расходится) |
|------|----------------------|--------------------------|------------------------------|
| `schedule_source` | `schedule_site` | `("schedule.read",)` | `guap_rasp_parser` |
| `calendar_sync` | `google_calendar` | `("calendar.read", "calendar.write")` | `calendar.write` |
| `timesheet` | `aadhk_timesheet` | `("timesheet.read", "timesheet.write")` | `aadhk` |
| `lms` | `lms_portal` | `("lms.read", "lms.write")` | `guap_lms`, `lms.grade` |

`ConnectorRole` сейчас содержит 4 значения (`entities.py`); для `git_source` и `notion` добавляются два члена enum («только объявлены»); существующие тесты Фазы 2 обращаются к конкретным членам и не проверяют полноту.

### `/api/v1/persona/current` (форма ответа)
Белый список, без Telegram-ID, NDA-слов, подстрок remote и путей: `id`, `display_name`, `short_name`, `title`, `organizations`, `default_area`, `task_areas[{value,label,filter_label,show_in_filter}]`, `ui.texts{…}`. API без аутентификации и с CORS `*` (OPS-05), поэтому в ответ идёт только то, что уже видно в интерфейсе. Выбор персоны: `settings.PERSONA_ID` (по умолчанию `popov-da-default`) [ASSUMED]; нет строки → 503.

### Что показывает интерфейс сегодня (проверено по `index.html`)
Область в D-11 описана как «ГУАП и Тидекс», фактически шире: кнопки фильтра (`:264-269`): «Все сферы» (служебная), «🏛️ ГУАП», «🔬 Тидекс», «🤖 AI & Dev» (значение `AI & Dev Projects`), «📚 Наука» (`Наука и статьи`), «🏠 Личное» (`Личное и семья`); опции формы (`:582-587`): те же и ещё «💰 Финансы» (значение `Финансы`), подписи в форме длиннее («🤖 AI & Dev Projects», «📚 Наука и статьи», «🏠 Личное и семья»). Блок D-12 перечисляет строки 70, 218, 265-266, 442, 464, 506, 582-583, 659, 932, 947; дополнительно найдено `:492` (`github-personal vs github-tydex`, подстрока tydex) и подпись «(2 GitHub Аккаунта)» без токена. Чтобы вид не изменился, `task_areas` должен содержать все 6 значений с двумя подписями, а тексты Security Tile (строки 442, 464, 492, 506) хранятся готовыми строками в `ui.texts` (шаблонное «склеивание» изменит видимые формулировки). Нейтральная заглушка до загрузки данных — пустые места (D-12). Список областей из дебрифа (`debrief_parser.py:30-37`) тоже 7 значений: тот же список; параметризовать вместе с промптом или оставить в baseline.

## Подготовка БД для тестов chat-app (D-04): результат проверки

**Путь работает, с одним уточнением: достаточно одной фикстуры, шаг в гейте не обязателен.**

1. Подтверждено: в боевой `assistant.db` нет `personas`, `workspaces`, `connector_bindings` [VERIFIED: sqlite3 `mode=ro&immutable=1`, 34 таблицы]. Тесты `test_dashboard_api.py` требуют существующих строк в `projects`, `reminders`, `documents` (≥1), поэтому «пустая временная БД» (Фаза 4) сейчас невозможна: нужна копия реальной.
2. Инициализация схемы вызывается только как `Database(path).init_db()` (assistant-core); конструктор принимает путь аргументом, `src/storage/db.py` не импортирует `src.config` [VERIFIED: прочитан заголовок файла], поэтому seed-CLI в `src/persona/seed.py` не трогает `.env` и не может случайно открыть боевую БД, если не передать ему её путь. CLI ОБЯЗАН отказать, если `--db` равен боевому пути (повтор защиты `gate.chat_pytest_env`).
3. `init_db()` на копии: `CREATE TABLE IF NOT EXISTS` для новых таблиц, остальное (ALTER-миграции, засев «если пусто») на копии с данными ничего не меняет. На ПУСТОЙ БД `init_db()` засеет стартовые данные владельца (`_seed_initial_data_if_empty`): тесты со второй персоной не должны опираться на содержимое `projects/tasks`.
4. Рекомендуемая фикстура chat-app (session, autouse): (a) `live = Path(settings.SQLITE_DB_PATH)`; (b) `sqlite3 backup()` из соединения `mode=ro` в `tmp_path_factory`; (c) `subprocess.run([CORE/.venv/bin/python, "-m", "src.persona.seed", "--db", copy], cwd=CORE)`; (d) `settings.SQLITE_DB_PATH = copy`; (e) финализатор удаляет копию. Боевая БД не открывается на запись ни при ручном запуске по CLAUDE.md, ни под гейтом; SHA-256-контроль гейта остаётся. Параметризованные фикстуры `persona_db(persona="default"|"synthetic")` дают вторую БД со второй персоной (для сравнения результатов).
5. Альтернатива из D-04 (шаг в `gate.py` после `make_db_copy`, вызывающий тот же seed-CLI) допустима и дополнительно полезна: ловит поломку seed-CLI ещё до pytest. Если выбрать только её, ручной запуск по CLAUDE.md останется без таблиц.
6. До Фазы 4 это единственная зависимость тестов chat-app от `/opt/assistant-core` кроме пути БД по умолчанию; Фаза 4 (DAT-04) заменяет её временной БД из общей схемы. Контракт `app-no-assistant-core` относится к пакету `app`, а не к тестам: нарушения нет [VERIFIED: `docs/BASELINE.md` — `root_packages = app, app.core`].

## Common Pitfalls

### Pitfall 1: эталоны промптов не попадают в git
**What goes wrong:** файлы лежат в `tests/data/prompts/`, коммит «успешен», снимка в репозитории нет.
**Why:** `.gitignore:20: data/` игнорирует любой каталог `data` на любой глубине [VERIFIED: `git check-ignore -v tests/data/prompts/x.txt`].
**How to avoid:** `tests/fixtures/prompts_snapshot/` [VERIFIED: `tests/fixtures/x.txt` не игнорируется]; тест проверяет, что каждый файл манифеста отслеживается (`git ls-files --error-unmatch` или хотя бы `git check-ignore` пуст).
**Warning signs:** `git status` после создания эталонов чист.

### Pitfall 2: NDA-слова в `persona.yaml` краснят гейт, а тест замораживает «15»
**What goes wrong:** `shield --all` флагует каждый отслеживаемый файл assistant-core с тремя словами (по одной находке на слово и строку): гейт красный на «новой находке»; `test_known_shield_false_positives_total_is_fifteen` (`backend/tests/test_gate.py:316-318`) требует ровно 15; правило 4 в `BASELINE.md` — список только сокращается.
**Why:** W3 требует слова в данных пространства, а shield по замыслу ловит их везде вне NDA-репозиториев.
**How to avoid:** решение владельца (Open Questions 1). Рекомендация: записать ОДНУ явную запись `("config/persona.yaml", "nda-keyword"): 3` и поправить закреплённое число с обоснованием в `BASELINE.md`; запись исчезает/заменяется правилом исключения для файлов данных персоны в Фазе 4 (SEC-01). Любой вариант — только с одобрения.
**Warning signs:** первый же `gate.py` после добавления файла.

### Pitfall 3: UI «2 области» против 6 фактических
Если `task_areas` содержит только ГУАП и Тидекс, пропадают 3 кнопки фильтра и 4 опции формы, то есть видимая регрессия против D-11/BCK-01. Использовать полный список (см. раздел выше).

### Pitfall 4: Порядок записей Security Tile
Blueprint 3.1 ставит `guap-physics` раньше `tydex-optics`, сегодняшний вывод — наоборот. Колонка `position` + эталонный тест на порядок `["chat-app","assistant-core","tydex-optics","guap-physics"]` (его уже косвенно держит `test_security_api.py` только по числу 4).

### Pitfall 5: Fail-open в двух местах
(a) `bot_handler.py:100-103`: `allowed_user_id is None` → доступ всем. Загрузчик персоны не должен превращать незаданный `${TELEGRAM_USER_ID}` в `""`; в strict-режиме (запуск демона) — `PersonaConfigError`, в тестовом режиме — пустой кортеж плюс список нераскрытых переменных. Сам `bot_handler` в Фазе 3 не меняется (иначе изменение поведения).
(b) Security Tile при отсутствующей персоне: не «0 проектов, чисто», а 503.

### Pitfall 6: Снимок в БД хранит ID Telegram
`personas.config_json` — «валидированный снимок»: хранить его до разворачивания `${ENV}`, иначе идентификатор владельца попадёт в БД в открытом виде (PER-01: в файле не хранится; в снимке тоже не нужно).

### Pitfall 7: Значения по умолчанию в нескольких местах расходятся
Адрес расписания: `config.py:18` даёт `https://guap.ru/rasp`, `ScheduleParser` — `https://rasp.guap.ru/`; blueprint — третий вариант. В персону по умолчанию кладётся то, что реально использует `main.py:582-583` (значение `config.SCHEDULE_URL`: env-переопределение остаётся сильнее). Блюпринт не источник значений.

### Pitfall 8: Модульные константы читаются при импорте
`SUBJECT_SHORT_NAMES`, `GUAP_BELL_SCHEDULE` импортируются другими модулями (`live_ticker.py:30-32`): если превратить их в вычисляемые при импорте, вторая персона в тесте не подхватится. Читать персону при вызове функции, а имена оставить для совместимости только если на них есть импорты.

### Pitfall 9: Тесты, привязанные к точному тексту
`test_composition_di.py:41` ждёт «по 8.5 ч»; `test_methodist.py:45` ждёт фразу отказа «специализированный агент-методист кафедры физики ГУАП» (она хардкодом в `methodist.py:513-515`, не в промпте); `test_brain.py:112,149` ждут заголовок «Мессенджеры (ОПД ГУАП)» (текст интерфейса, остаётся в baseline). Тест переписывается на значение из персоны только если ЗНАЧЕНИЕ переехало; если строка осталась в коде, тест не трогается.

### Pitfall 10: Файлы без перевода строки и `Write`
Шаблон `debrief` без `\n` в конце: перед коммитом проверить `read_bytes()[-1:]`; `MANIFEST.json` хранит длину.

### Pitfall 11: Web-аудит сканирует первые 100 файлов обоих репозиториев
Новые отслеживаемые файлы (`config/persona.yaml`, шаблоны, эталоны) не должны содержать строк, похожих на секреты (токены, длинные ключи после `api_key =`); эталоны промптов и фикстуры проверить на шаблоны `SECRET_PATTERNS` до коммита. Тест гейта `test_security_audit_all` ждёт `status == "passed"`.

### Pitfall 12: `core-is-pure` полнота
`tests/test_core_architecture.py:50-62` требует, чтобы каждый новый модуль верхнего уровня `src` входил в `forbidden_modules` контракта `core-is-pure`. Новый пакет `src.persona` без добавления в `.importlinter` краснит тест.

## Code Examples

### Окружение Jinja2 (проверено прогоном)
```python
# Source: прогон на jinja2 3.1.2 в scratchpad (эквивалентно 3.1.6); докум.: jinja.palletsprojects.com (SandboxedEnvironment)
from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

def make_env(base_dir: str) -> SandboxedEnvironment:
    return SandboxedEnvironment(
        loader=FileSystemLoader(base_dir),   # base_dir = каталог persona.yaml; выход за него запрещён загрузчиком
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,          # иначе финальный "\n" теряется
        trim_blocks=False, lstrip_blocks=False,
    )
```

### Сравнение «символ в символ»
```python
def test_default_prompts_match_snapshot(default_persona, manifest):
    for name, meta in manifest["prompts"].items():
        expected = (SNAP / f"{name}.txt").read_bytes()
        assert len(expected) == meta["length"]
        got = render_prompt(default_persona, name, **meta.get("vars", {})).encode("utf-8")
        assert got == expected          # побайтно, включая отсутствие "\n" у debrief
```

### Подстановка `${ENV}` без молчаливой пустой строки [ASSUMED: набросок]
```python
_ENV = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
def resolve_env(value: str, env, *, strict: bool, unresolved: list[str]) -> str:
    def sub(m):
        name = m.group(1)
        if name in env and env[name] != "":
            return env[name]
        if strict:
            raise PersonaConfigError(f"не задана переменная окружения {name}")
        unresolved.append(name)
        return m.group(0)               # оставляем плейсхолдер, не ""
    return _ENV.sub(sub, value)
```

### Эквивалентность NDA на настоящих git-репозиториях
```python
def make_repo(root: Path, remote: str | None, files: dict[str, str]) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    if remote:
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=root, check=True)
    for rel, text in files.items():
        (root / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root
# Секретные строки собирать из частей ("ghp_" + "a"*36), слова NDA брать из данных пространства,
# чтобы файл самого теста не нарушал shield --all.
```

### Конвертер синтетической персоны (общий файл, правится в обеих копиях синхронно)
```python
def synthetic_to_config(d: dict) -> dict:
    """dict каркаса Фазы 1 -> структура persona.yaml; lesson_slots: {1: (s, e)} -> [{number, start, end}]."""
    ...
# chat-app: json.dump(config, f)  # JSON читается yaml.safe_load в seed-CLI
# assistant-core: yaml.safe_dump(config)
```
Изменение `synthetic_persona.py` — в ОБЕИХ копиях одним коммитом (иначе красный шаг «дрейф SHA-256»); если добавляется отдельный общий модуль (например, `persona_tokens.py` для сканера), расширить `persona_drift_check` на новую пару, не ослабляя существующую проверку.

## Сканер хардкода (PER-08, D-16)

- **Токены** выводятся из персоны по умолчанию: `display_name` и формы имени, `short_name`, имена организаций (в обеих раскладках: ГУАП/GUAP, Тидекс/Tydex), подстрока аккаунта из `forbidden_remote_substrings`, пути пространств `/opt/work-tydex`, `/opt/personal/guap-physics`, домены (`guap.ru`), `bot_username`. Сравнение без учёта регистра. chat-app берёт токены из `personas.config_json` через `sqlite3` (по тому же снимку), assistant-core — из загрузчика; функция вычисления токенов лежит в общем файле тестов (пара копий + контроль SHA-256).
- **Что сканируется:** `git ls-files` по `*.py, *.html, *.js, *.css, *.sh, *.toml, *.ini, *.cfg, *.yaml, *.yml, *.json, *.jinja2` вне классов allowlist: `config/**` (данные персоны), `tests/**` и `backend/tests/**` (фикстуры и тесты), `docs/**`, `.planning/**`, `*.md`. Тесты как класс исключены в Фазе 3 (в них законно стоят значения владельца как ожидаемые данные); Фаза 6 ужесточает.
- **Baseline:** `tests/hardcode_baseline.py`: `{путь: {класс_токена: макс_число}}`; тест красный при превышении, при новом файле, при устаревшей записи. Числа создаются программой (`--rebuild` разово в последнем плане) и проверяются глазами: список остаточного долга из D-16 + раздел «Остаётся в baseline» выше — ожидаемый состав.
- **Нерешённое:** как считать вхождения в строках с несколькими токенами: считать по паре (строка, класс) для стабильности при правке соседних слов.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Промпты — константы в `brain/*.py` | Шаблоны Jinja2 в `config/prompts`, путь в персоне | эта фаза | Тест снимка заменяет golden-набор ответов (W10) |
| Реестр пространств — константа в `security.py` | Таблица `workspaces` | эта фаза | Security Tile читает данные; fail-closed |
| Denylist токенов — константа в `test_synthetic_persona.py` | Токены из данных персоны | эта фаза | Исчезает копия профиля в тестах |
| `Environment` Jinja2 по умолчанию | `SandboxedEnvironment` + `StrictUndefined` | эта фаза | Безопасность шаблонов без изменения вывода |

**Deprecated/outdated:** значения blueprint 3.1 для провайдеров и scopes (`guap_rasp_parser`, `aadhk`, `guap_lms`, `lms.grade`, адрес `https://rasp.guap.ru/`) расходятся с кодом Фазы 2; источник правды — код (таблица выше). Blueprint 3.1 не учитывает 4 пространства в сегодняшнем порядке и строки `account`/`clearance_label`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Боевой `.env` либо не задаёт `SCHEDULE_URL`, либо задаёт значение, равное тому, что реально работает; правило «env сильнее персоны» сохраняет 1:1 в любом случае. `.env` не читался | Аудит, Pitfall 7 | Если в персону записан не тот адрес, при удалении env получим другой сайт расписания; смягчено правилом приоритета env |
| A2 | `PERSONA_CONFIG_PATH` и `PERSONA_ID` не заданы в боевом окружении и юнитах (юниты не открывались, OPS-02) | Runtime State | Низкий: имена новые, значения по умолчанию безопасны |
| A3 | Схема `persona.yaml` (формы имени, `task_areas`, `ui.texts`, `scope`, `methodist`) — проектное решение, не требование | Схема | Менять дорого после Фазы 3 (D-01 costly); утвердить целиком в волне 2 |
| A4 | Составной ключ `(persona_id, id)` и колонки `position/account/clearance_label` в `workspaces` | Таблицы | Низкий; иначе ломается 1:1 вывод или ISO-04 |
| A5 | Толкование W4: слова NDA хранятся у NDA-пространства, применяются к остальным пространствам персоны | NDA-чек-лист | Если владелец имел в виду иное, меняется набор блокировок; тест D01 это покажет |
| A6 | «scope-решения» в PER-09 = (а) решения `MethodistService.check_scope`, (б) какие проверки применяются к пространству по допуску | PER-09 | Если имелось в виду иное, тест надо переписать |
| A7 | Выбор персоны chat-app по `settings.PERSONA_ID` с дефолтом `popov-da-default` | API | Низкий |
| A8 | Репозитории chat-app и assistant-core считаются `public` по W2 (публичность на GitHub не проверялась) | Pitfall 2 | Влияет только на тяжесть размещения NDA-слов в персоне |
| A9 | Форма `/persona/current` и необходимость `ui.texts` как готовых строк | API | Если владелец согласен на изменение формулировок, можно упростить |
| A10 | Решение держать длинный текст дефолтных промптов литералом в `*_default.jinja2` | Промпты | Если Фаза 6 захочет разложить на поля, понадобится вторая итерация шаблонов |

## Open Questions

1. **NDA-слова в файле персоны (требует решения владельца, до плана 2).**
   - Знаем: W3/PER-04 требуют слова в данных пространства; `shield --all` краснит любой отслеживаемый файл с ними; список из 15 известных находок заморожен тестом и правилом 4.
   - Неясно: можно ли один раз расширить список (запись для `config/persona.yaml`, число 3, закреплённое число 18).
   - Рекомендация (первым в опросе): разрешить одну явную запись с пометкой «снимается правилом Фазы 4»; альтернативы: хранить слова в закодированном виде (теряется читаемость) или вне репозитория (теряется воспроизводимость теста). Вопрос задавать простыми словами: «Сторож безопасности ругается на три секретных слова Тидекса везде, где их встретит. Нам нужно записать их в файл настроек. Разрешить ему сделать одно исключение для этого файла?»
2. **Адреса почты владельца в шаблонах и эталонах (низкий риск, подтверждение).**
   - Знаем: тексты промптов уже содержат адреса в `src/brain/secretary_dialog.py`; W10 требует посимвольный эталон; сквозной критерий 7 говорит «нет e-mail».
   - Рекомендация: принять как есть (перенос не увеличивает раскрытие), записать в BASELINE как известное отступление; вынести адреса в переменные окружения нельзя без изменения эталона.
3. **Области задач: 6, а не 2.** Факт опровергает формулировку «у владельца: ГУАП и Тидекс» в D-11, но не его цель («вид не изменился»). Планировщик берёт полный список; владельцу вопрос не нужен, если не хочет сокращать интерфейс.
4. **Толкование W4 для слов NDA** (см. A5): решить в плане, зафиксировать в чек-листе.
5. **Определение «scope-решений»** (A6): закрепить в плане 7 явным перечислением проверок теста.
6. **Шаг подготовки копии в гейте.** Фикстуры достаточно; добавлять ли дополнительный шаг в `gate.py`: на усмотрение планировщика.
7. **Случай D03:** что делать с NDA-пространством без правил (пустые подстроки): падать при загрузке или предупреждать. Рекомендация: пустой список подстрок у `restricted_nda` допустим только с явным `allow_empty_nda_rules: true`, иначе ошибка валидации (fail-closed).

### Решения владельца (2026-10-02, опрос в /gsd-plan-phase 3)

- **OQ1 — РЕШЕНО:** разрешена ОДНА явная запись-исключение сторожа безопасности для `config/persona.yaml` (3 находки); закреплённое число известных находок меняется с 15 на 18 (`test_known_shield_false_positives_total_is_fifteen` и правило 4 BASELINE обновляются соответственно); исключение снимается правилом в Фазе 4.
- **OQ2 — РЕШЕНО:** адреса почты владельца остаются в шаблонах `*_default.jinja2` и эталонах промптов как есть; отступление от сквозного критерия 7 записывается в `docs/BASELINE.md` как известное.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | оба репозитория | ✓ | 3.12.3 | — |
| pytest + anyio / pytest-asyncio | тесты | ✓ | 9.1.1 / 4.15.1 / 1.4.0 | — |
| import-linter | контракты | ✓ | 2.15 | — |
| PyYAML | загрузчик (assistant-core) | ✓ (транзитивно) | 6.0.3 | добавить прямую запись в `requirements.txt` |
| PyYAML | chat-app | ✗ (не нужен по D-03) | — | JSON-файл персоны в тестах |
| Jinja2 | шаблоны (assistant-core) | ✗ в обоих `.venv`; ✓ в системном python3 | 3.1.2 (system) | установить 3.1.6 в `.venv` assistant-core после одобрения |
| Сеть до PyPI | установка | ✓ (`pip download` прошёл) | — | — |
| git | NDA-тесты на временных репозиториях | ✓ | системный | — |
| `/opt/assistant-core/data/methodist/raw` | `test_search_local_files_catalog` | ✓ (тест зелёный на базе 223/223) | — | — |
| `/opt/work-tydex`, `/opt/personal/guap-physics` | Security Tile | ✗ отсутствуют (так и задумано: air-gap) | — | `virtual_airgap` |
| systemd-сервисы | не нужны | остановлены | — | проверка по тестам |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Jinja2 в `.venv` assistant-core (установка с чекпоинтом); PyYAML в chat-app не требуется.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1; assistant-core: pytest-asyncio 1.4.0 (`asyncio_mode = auto`); chat-app: `pytest.mark.anyio`, `ASGITransport` + `AsyncClient` |
| Config file | `/opt/assistant-core/pytest.ini` (`testpaths = tests`, `pythonpath = .`); chat-app: без `pytest.ini`, `backend/tests/conftest.py` |
| Quick run command | `cd /opt/assistant-core && .venv/bin/pytest tests/test_prompt_snapshot.py tests/test_persona_loader.py tests/test_persona_storage.py tests/test_persona_config.py tests/test_connector_params.py tests/test_hardcode_scanner.py tests/test_core_architecture.py tests/test_architecture_contract.py -q -p no:cacheprovider && .venv/bin/lint-imports --no-logo --no-cache` |
| Quick run (chat-app) | `cd /opt/chat-app && backend/.venv/bin/pytest backend/tests/test_persona_api.py backend/tests/test_security_api.py backend/tests/test_nda_equivalence.py backend/tests/test_hardcode_scanner.py backend/tests/test_index_whitelabel.py -q -p no:cacheprovider` (после появления фикстуры копия БД делается автоматически) |
| Full suite command | `python3 /opt/chat-app/scripts/gate.py` (ожидается «ИТОГ: ЗЕЛЁНЫЙ») |

Нижние границы числа тестов (проверено `--collect-only` в этой сессии): assistant-core ≥ 223, chat-app ≥ 68; после каждой волны число только растёт. [VERIFIED]

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PER-07 | Шаблон с дефолтной персоной = эталон побайтно; вызов LLM получает тот же текст; эталоны отслеживаются git | unit (капчур клиента) | `.venv/bin/pytest tests/test_prompt_snapshot.py -q` | ❌ Wave 0 (план 1) |
| PER-01 | Загрузка дефолта без `PERSONA_CONFIG_PATH`; подмена путём; `${ENV}`; strict; `extra=forbid`; безопасный `safe_load` | unit | `.venv/bin/pytest tests/test_persona_loader.py -q` | ❌ Wave 0 |
| PER-02 | Таблицы создаёт `init_db()`; идемпотентный upsert; несколько привязок на роль; снимок с плейсхолдером; FK | unit (aiosqlite `:memory:`) | `.venv/bin/pytest tests/test_persona_storage.py -q` | ❌ Wave 0 |
| PER-03 | `/security/overview` из таблиц: 4 записи, порядок, строки, цвета, air-gap; `PROJECTS_REGISTRY` отсутствует; 503 без персоны | integration | `backend/.venv/bin/pytest backend/tests/test_security_api.py -q` | ✅ переписывается (BCK-02) |
| PER-04 | NDA-чек-лист N01-N09, S01-S09, P01-P03, D01-D03 | integration (временные git-репо) | `backend/.venv/bin/pytest backend/tests/test_nda_equivalence.py -q` + `.venv/bin/pytest tests/test_nda_script_parity.py -q` | ❌ Wave 0 (характеризация ДО замены) |
| PER-05 | `/persona/current` белый список; `index.html` без токенов; дефолт области из персоны (создание без `area`) | integration + static | `backend/.venv/bin/pytest backend/tests/test_persona_api.py backend/tests/test_index_whitelabel.py backend/tests/test_dashboard_api.py -q` | ❌ / ✅ (dashboard переписывается) |
| PER-06 | Фабрики берут параметры из привязок; вызовы с `project_name=` из персоны; норма/предметы/слоты/адреса/каталог читаются из данных | unit | `.venv/bin/pytest tests/test_connector_params.py tests/test_composition_di.py -q` | ❌ / ✅ |
| PER-08 | Сканер находит токены вне allowlist; baseline не растёт и не устаревает; токены из данных | unit | оба репозитория: `tests/test_hardcode_scanner.py`, `backend/tests/test_hardcode_scanner.py` | ❌ Wave 0 |
| PER-09 | Синтетическая персона даёт другие промпты, пространства, дефолты, scope-решения на тех же путях | integration | `.venv/bin/pytest tests/test_persona_config.py -q` + `backend/.venv/bin/pytest backend/tests/test_persona_api.py -q` | ❌ Wave 0 |
| BCK-01 | 1:1: эталоны промптов, порядок и строки Security Tile, дефолты | сводный | `python3 /opt/chat-app/scripts/gate.py` | ✅ |
| BCK-02 | Переписанные тесты не слабее: тот же ассерт по значению из персоны; ни один тест не удалён | диф-проверка | `git -C <repo> diff --name-status <база>..HEAD -- tests/` без `D`; число тестов ≥ нижней границы | ✅ |

### Sampling Rate
- **Per task commit:** быстрый набор своего репозитория + `lint-imports` (до 60 с).
- **Per wave merge:** `python3 /opt/chat-app/scripts/gate.py`.
- **Phase gate:** гейт зелёный, `docs/BASELINE.md` обновлён (версии Jinja2/MarkupSafe, число тестов, новое состояние «Ожидают Фазы 3» → «Включено»), сервисы не запускались, SHA-256 боевой БД равен стартовому.

### Wave 0 Gaps
- [ ] `tests/fixtures/prompts_snapshot/*.txt` + `MANIFEST.json` + `tests/test_prompt_snapshot.py` — PER-07 (ПЕРВЫЙ коммит фазы, до правок `src/brain`)
- [ ] характеризационный `backend/tests/test_nda_equivalence.py` на текущем `security.py` и обеих копиях shield — PER-04 (до замены реестра)
- [ ] эталон вывода `/security/overview` (4 записи, порядок и строки) — PER-03
- [ ] `tests/test_persona_loader.py`, `test_persona_storage.py`, `test_persona_config.py`, `test_connector_params.py`, `test_nda_script_parity.py`, `test_hardcode_scanner.py` (assistant-core)
- [ ] `backend/tests/{test_persona_api,test_index_whitelabel,test_hardcode_scanner}.py`, расширение `conftest.py` (фикстуры копии БД и `persona_db`)
- [ ] установка Jinja2 (чекпоинт), запись версий в `docs/BASELINE.md`
- [ ] расширение `persona_drift_check` и `test_gate.py` (если добавляется общий файл; число 15 меняется только по решению владельца, Open Questions 1)

## Security Domain

`security_enforcement` в `.planning/config.json` не задан: считается включённым.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | нет (API без аутентификации, OPS-05/AUTH2) | не расширяется; `/persona/current` отдаёт только публично видимое |
| V3 Session Management | нет | — |
| V4 Access Control | да | белый список полей `/persona/current`; Telegram-авторизация не меняется; fail-closed Security Tile |
| V5 Input Validation | да | Pydantic (`extra="forbid"`, `Literal` допусков), `yaml.safe_load`, проверка путей шаблонов внутри каталога персоны |
| V6 Cryptography | нет | SHA-256 только для контроля целостности (уже в гейте) |
| V8 Data Protection | да | `${TELEGRAM_USER_ID}` не попадает ни в файл, ни в снимок БД; NDA-слова не попадают в ответы API |
| V14 Configuration | да | секреты только из окружения; новые переменные имеют безопасные дефолты |

### Known Threat Patterns for этого стека
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSTI в шаблонах (если шаблон станет пользовательским) | Elevation of Privilege | `SandboxedEnvironment`, `StrictUndefined`, шаблоны только из каталога персоны |
| Обход каталога через `prompts:` (`../../...`) | Information Disclosure | `resolve()` и проверка, что путь лежит внутри каталога персоны |
| Небезопасная загрузка YAML | Tampering | только `yaml.safe_load` |
| Бот открыт всем при пустом `TELEGRAM_USER_ID` | Spoofing/EoP | не подставлять `""`; strict-режим в `main.py`; `_is_authorized` не менять в этой фазе |
| Security Tile «чисто» при пустой персоне | Repudiation/Info | 503 / статус `alert` |
| Сужение NDA-блокировок при переносе в данные | Tampering/Info Disclosure | чек-лист N/S/P/D с негативными случаями; валидация «NDA без правил» |
| Утечка NDA-слов в ответ API/лог | Information Disclosure | белый список `/persona/current`; тесты и гейт не печатают слова (правило Фазы 1) |
| Запись тестов в боевую БД | Tampering | фикстура копии + SHA-256 гейта; seed-CLI отказывает на боевом пути |
| Перезапись данных при повторной загрузке персоны | Tampering | замена только строк персоны в одной транзакции, пользовательские таблицы не затрагиваются |

## Рекомендуемая разбивка на планы и волны

| Волна/план | Содержание | Репозиторий | Зависит |
|-----------|-----------|-------------|---------|
| 1 / 03-01 | Снимок промптов (3 обязательных + остальные), капчур по месту вызова, манифест, тест | assistant-core | — (нет правок `src/`) |
| 2 / 03-02 | Зависимости (чекпоинт), `src/persona/*`, `config/persona.yaml` + шаблоны-заготовки, DDL в `init_db`, seed-CLI, `ConnectorRole` +2, `.importlinter`, конвертер синтетической персоны, `test_persona_loader/storage` | assistant-core | 03-01 |
| 3 / 03-03 | Характеризация NDA-чек-листа и эталон `/security/overview` (ОТДЕЛЬНЫЙ коммит), затем фикстура копии БД, чтение из таблиц, удаление `PROJECTS_REGISTRY`, переписанные `test_security_api` | chat-app | 03-02 |
| 3 / 03-04 | Промпты → шаблоны (секретарь, маршрутизатор, методист+scope), потом остальные; потребители, `test_fast_intent_router` импорт | assistant-core | 03-02 (параллельно с 03-03) |
| 4 / 03-05 | `/persona/current`, `index.html` white-label, дефолт области, переписанный `test_dashboard_api`, `test_index_whitelabel` | chat-app | 03-03 |
| 4 / 03-06 | Параметры коннекторов: композиция, call-sites, предметы/слоты/адреса/каталог, `test_connector_params`, переписанные тесты | assistant-core | 03-02 |
| 5 / 03-07 | Сканеры + baseline в обоих репозиториях, `test_persona_config.py`, `test_nda_script_parity`, `BASELINE.md`, финальный гейт | оба | всё |

Волны 3-4 для разных репозиториев независимы (общие файлы только `.planning/` и `docs/BASELINE.md`). Схему персоны утвердить полностью в 03-02: 03-04..03-06 только потребляют поля. Делегирование Antigravity (D-20) уместно для механической замены строк в `index.html` и черновиков шаблонных тестов; NDA-логика, чек-лист и ревью — только Claude; в задание не вставлять содержимое `config/persona.yaml` с NDA-словами и адреса почты.

## Sources

### Primary (HIGH confidence)
- Прочитано в этой сессии: `03-CONTEXT.md`, `03-DISCUSSION-LOG.md`, `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md` (Фаза 3), `.planning/intel/user-resolutions.md`, `docs/BASELINE.md`, `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` §3-5, `.planning/codebase/CONCERNS.md`, SUMMARY Фазы 2.
- Код chat-app: `backend/app/api/v1/security.py`, `app/db.py`, `app/models/dashboard_schemas.py`, `app/main.py`, `app/core/config.py`, `static/index.html`, `scripts/security_shield.py`, `scripts/gate.py`, `backend/tests/{test_security_api,test_dashboard_api,test_gate,synthetic_persona,conftest}.py`.
- Код assistant-core: `src/brain/{secretary_dialog,intent_router,methodist,reply_generator,debrief_parser,summarizer}.py`, `src/composition.py`, `src/config.py`, `src/storage/db.py` (init_db, DDL, засев), `src/models/schedule.py`, `src/calendar/client.py`, `src/parser/schedule_parser.py`, `src/connectors/guap_lms/client.py`, `src/notifier/{bot_handler,live_ticker}.py`, `src/main.py`, `src/core/**`, `.importlinter`, `.gitignore`, `pytest.ini`, `requirements.txt`, `tests/{test_ports_conformance,test_composition_di,test_core_architecture,test_core_domain,test_synthetic_persona,test_secretary_dialog,test_methodist,test_fast_intent_router}.py`.
- Проверки выполнением: `sqlite3 mode=ro&immutable=1` по боевой БД (список таблиц, счётчики, DDL `tasks`); `git check-ignore`; `pytest --collect-only` (223 / 68); прогон Jinja2 на системном python; `pip index versions`, `pip download` в scratchpad; `gsd-tools query package-legitimacy check`.

### Secondary (MEDIUM confidence)
- Документация Jinja2 по `SandboxedEnvironment`/`StrictUndefined` из памяти и подтверждена поведением в прогоне (версия 3.1.2).

### Tertiary (LOW confidence)
- Содержимое боевого `.env` и юнитов systemd не читалось (запрет и OPS-02): A1, A2.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — версии и доступность проверены командами.
- Architecture: MEDIUM — решения D-01..D-20 соблюдены; схема персоны и API — проект Claude (A3, A9).
- Pitfalls: HIGH — каждый воспроизведён или прочитан в коде (git-ignore, shield, fail-open, порядок, характеризация).
- NDA-чек-лист: HIGH по фактам кода, MEDIUM по толкованию W4 (A5).

**Research date:** 2026-10-02
**Valid until:** 2026-11-01 (код обоих репозиториев заморожен; устареет при правках `src/brain`, `security.py` или `scripts/gate.py` вне фазы)
