---
phase: 03-persona-kak-dannye
reviewed: 2026-10-03T00:00:00Z
depth: standard
files_reviewed: 67
files_reviewed_list:
  - /opt/assistant-core/.importlinter
  - /opt/assistant-core/requirements.txt
  - /opt/assistant-core/src/brain/debrief_parser.py
  - /opt/assistant-core/src/brain/intent_router.py
  - /opt/assistant-core/src/brain/methodist.py
  - /opt/assistant-core/src/brain/reply_generator.py
  - /opt/assistant-core/src/brain/secretary_dialog.py
  - /opt/assistant-core/src/brain/summarizer.py
  - /opt/assistant-core/src/calendar/client.py
  - /opt/assistant-core/src/composition.py
  - /opt/assistant-core/src/config.py
  - /opt/assistant-core/src/connectors/aadhk/parser.py
  - /opt/assistant-core/src/connectors/guap_lms/client.py
  - /opt/assistant-core/src/core/domain/entities.py
  - /opt/assistant-core/src/main.py
  - /opt/assistant-core/src/models/schedule.py
  - /opt/assistant-core/src/notifier/bot_handler.py
  - /opt/assistant-core/src/notifier/live_ticker.py
  - /opt/assistant-core/src/parser/schedule_parser.py
  - /opt/assistant-core/src/persona/bindings.py
  - /opt/assistant-core/src/persona/current.py
  - /opt/assistant-core/src/persona/__init__.py
  - /opt/assistant-core/src/persona/loader.py
  - /opt/assistant-core/src/persona/models.py
  - /opt/assistant-core/src/persona/prompts.py
  - /opt/assistant-core/src/persona/seed.py
  - /opt/assistant-core/src/storage/db.py
  - /opt/assistant-core/tests/conftest.py
  - /opt/assistant-core/tests/hardcode_baseline.py
  - /opt/assistant-core/tests/persona_tokens.py
  - /opt/assistant-core/tests/synthetic_persona.py
  - /opt/assistant-core/tests/test_connector_params.py
  - /opt/assistant-core/tests/test_fast_intent_router.py
  - /opt/assistant-core/tests/test_hardcode_scanner.py
  - /opt/assistant-core/tests/test_nda_script_parity.py
  - /opt/assistant-core/tests/test_persona_config.py
  - /opt/assistant-core/tests/test_persona_loader.py
  - /opt/assistant-core/tests/test_persona_prompts.py
  - /opt/assistant-core/tests/test_persona_storage.py
  - /opt/assistant-core/tests/test_prompt_snapshot.py
  - /opt/assistant-core/tests/test_secretary_dialog.py
  - /opt/assistant-core/tests/test_synthetic_persona.py
  - /opt/chat-app/backend/app/api/v1/persona.py
  - /opt/chat-app/backend/app/api/v1/router.py
  - /opt/chat-app/backend/app/api/v1/security.py
  - /opt/chat-app/backend/app/core/config.py
  - /opt/chat-app/backend/app/db.py
  - /opt/chat-app/backend/app/main.py
  - /opt/chat-app/backend/app/models/dashboard_schemas.py
  - /opt/chat-app/backend/app/static/index.html
  - /opt/chat-app/backend/tests/conftest.py
  - /opt/chat-app/backend/tests/hardcode_baseline.py
  - /opt/chat-app/backend/tests/persona_tokens.py
  - /opt/chat-app/backend/tests/synthetic_persona.py
  - /opt/chat-app/backend/tests/test_dashboard_api.py
  - /opt/chat-app/backend/tests/test_gate.py
  - /opt/chat-app/backend/tests/test_hardcode_scanner.py
  - /opt/chat-app/backend/tests/test_index_whitelabel.py
  - /opt/chat-app/backend/tests/test_nda_equivalence.py
  - /opt/chat-app/backend/tests/test_persona_api.py
  - /opt/chat-app/backend/tests/test_security_api.py
  - /opt/chat-app/backend/tests/test_security_golden.py
  - /opt/chat-app/backend/tests/test_synthetic_persona.py
  - /opt/chat-app/scripts/gate.py
findings:
  critical: 2
  warning: 9
  info: 7
  total: 18
status: issues_found
---

# Фаза 3: отчёт о код-ревью

**Проверено:** 2026-10-03
**Глубина:** standard
**Файлов:** 67
**Статус:** issues_found

## Краткое резюме

Рассмотрены перенос данных владельца из кода в данные персоны (config/persona.yaml, шаблоны Jinja2, таблицы SQLite), новый слой src/persona/*, веб-часть chat-app (security.py, persona.py, db.py, index.html), гейт качества и тесты. Структурных находок (fallow) к этому прогону не передано. Часть файлов из списка (тесты test_dashboard_api, test_gate, test_security_api, test_security_golden, test_fast_intent_router, test_secretary_dialog, test_persona_config, test_persona_storage, test_prompt_snapshot) просмотрена выборочно, в основном через зависимости и общие фикстуры.

Общая оценка: архитектура аккуратная (yaml.safe_load, extra=forbid, SandboxedEnvironment + StrictUndefined, проверка путей шаблонов, белый список в /persona/current, textContent вместо innerHTML в applyPersona, значения NDA не попадают в сообщения об ошибках). Но правило NDA в веб-аудите на рантайме не fail-closed (CR-01), UI-форма задачи может молча затирать область (CR-02), а ошибки конфигурации персоны в нескольких местах проглатываются или возникают только во время вызова, а не при старте.

Проверки по пунктам из задания:
1. Регрессии поведения для персоны по умолчанию: основные значения (слоты, предметы, URL, норма часов, тексты UI) совпадают; мелкие отличия описаны в IN-03.
2. Сужение правил NDA: прямого сужения для данных по умолчанию нет, но проверка ослабляется при пустых правилах в БД (CR-01) и слабое сопоставление подстрок (WR-07).
3. Песочница Jinja2 и обход пути: путь шаблона проверяется (относительный, без .., расширение .jinja2, symlink, внутри каталога), FileSystemLoader дополнительно отбрасывает `..`. Прямого обхода не найдено. Остаются WR-03 (необёрнутые исключения Jinja2) и WR-05 (в контекст шаблона попадает вся персона). Пути file_catalog не проверяются (WR-06).
4. XSS в index.html: applyPersona безопасна (textContent, Option, replaceChildren). Однако соседние поля по-прежнему вставляются без экранирования (WR-01).
5. Проглатывание PersonaConfigError: см. WR-02.

## Критические проблемы

### CR-01: Правило NDA в веб-аудите отключается молча при пустых данных пространства (fail-open)

**Файл:** `/opt/chat-app/backend/app/api/v1/security.py:47-54, 89`
**Проблема:** `nda_rule_for` для пространства с допуском restricted_nda строит правило из `ws.get("forbidden_remote_substrings") or ()`. Если в таблице workspaces список пуст, NULL, `[]` или строка записана не через загрузчик (колонка имеет DEFAULT '[]', CHECK на непустоту нет), правило создаётся с пустым кортежем, `any(...)` над пустым кортежем даёт False, нарушений нет, статус `passed`/`clean`. Запрет "NDA без правил" (`WorkspaceConfig._nda_requires_rules`) действует только при чтении YAML, а chat-app читает строки БД напрямую (в БД пишет демон, плюс любой сторонний засев/ручная правка). Раньше проверка remote для NDA-проекта была безусловной, то есть это ослабление air-gap защиты относительно прежнего поведения. Аналогично, `/security/audit` с неизвестным `project_id` возвращает `status: passed` при `audited_count: 0`.
**Исправление:**
```python
def nda_rule_for(ws):
    if ws.get("clearance") != "restricted_nda":
        return None
    subs = tuple(s for s in (ws.get("forbidden_remote_substrings") or ()) if s)
    return NdaRemoteRule(subs, ws.get("remote_violation_message") or DEFAULT_REMOTE_VIOLATION)

# в audit_path, для nda_rule is not None:
if nda_rule is not None and not nda_rule.forbidden_remote_substrings:
    violations.append("CRITICAL: у NDA-пространства не заданы правила remote (fail-closed)")
```
Для `/audit` с `project_id`, которого нет среди пространств, отвечать 404, а не `passed`.

### CR-02: Форма задачи затирает область (area) пустой строкой, если значения нет в списке персоны или персона не загрузилась

**Файл:** `/opt/chat-app/backend/app/static/index.html:718-722, 989, 1009` (+ `/opt/chat-app/backend/app/api/v1/tasks.py:30-35`, `/opt/chat-app/backend/app/db.py:315-327`)
**Проблема:** `<select id="modal-task-area">` теперь пустой в статике и заполняется только после успешного `/persona/current`. Если запрос не удался (503 для не засеянной персоны, сеть) или у существующей задачи область не входит в `task_areas` текущей персоны (старые данные, смена персоны), то `select.value = t.area` не выбирает ничего, `value` равен `''`, и `saveTaskModal` отправляет `PUT` с `area: ""`. `update_task` пишет `exclude_unset`-словарь как есть, в БД попадает пустая область, то есть происходит молчаливая порча данных. До фазы это работало автономно (шесть фиксированных option). `create_task` пустую область заменяет на дефолт (`or`), `update_task` нет, поведение несимметрично.
**Исправление:** (а) в `openTaskModalEdit` перед установкой значения добавлять недостающую область как option (`if (![...select.options].some(o => o.value === t.area)) select.add(new Option(t.area, t.area))`); (б) в `saveTaskModal` не включать `area` в payload, если значение пустое; (в) на сервере в `update_task` игнорировать пустую/None область (`if data.get("area") == "": data.pop("area")`).

## Предупреждения

### WR-01: Хранимый XSS через неэкранируемые поля задач и напоминаний (pre-existing, но фаза экранировала только area)

**Файл:** `/opt/chat-app/backend/app/static/index.html:796, 820, 928, 938, 1060, 1293`
**Проблема:** API без аутентификации принимает произвольные строки для `due_date`, `priority`, `check_date` (`Optional[str]`/`str` без валидации в `dashboard_schemas.py`), а страница вставляет их в `innerHTML` без `escapeHtml` (`${t.due_date}`, `${t.priority}`, `${r.check_date}`). Любой, кто может вызвать API, исполняет скрипт в браузере владельца. Фаза закрыла только `t.area` и `p.area`, оставив соседние поля. Кроме того, `runSecurityAudit('${p.id}')` вставляет id пространства в атрибут onclick: теперь это данные из БД, а паттерн `^[a-z0-9-]+$` проверяется только в YAML-загрузчике.
**Исправление:** обернуть все эти значения в `escapeHtml(...)`; для onclick использовать `addEventListener` или `data-`-атрибут с `escapeHtml`; на сервере валидировать `due_date`/`check_date` как дату, `priority` как `Literal["P1","P2","P3"]`.

### WR-02: PersonaConfigError проглатывается общими `except Exception` (ошибка конфигурации превращается в тихую деградацию)

**Файлы:**
- `/opt/assistant-core/src/brain/summarizer.py:155, 356` (рендер внутри внешнего `try ... except Exception`, оба дайджеста уходят на запасной шаблон с `logger.exception`)
- `/opt/assistant-core/src/brain/methodist.py:426-431` (`render_prompt("methodist_scope_check")` внутри `try`, итог `out_of_scope` с `logger.debug`: все вопросы молча отклоняются как "вне области")
- `/opt/assistant-core/src/main.py:299-303` (`timesheet_settings()` внутри `except Exception` с `logger.debug`: утренний дайджест молча теряет табель)
- `/opt/assistant-core/src/brain/secretary_dialog.py:117-130`, `/opt/assistant-core/src/notifier/live_ticker.py:120-129` (то же для табеля)

**Проблема:** в `debrief_parser.py` авторы сами вынесли рендер за `try` ("ошибка конфигурации персоны не должна маскироваться"), но в остальных местах этот принцип не соблюдён. Сломанная персона выглядит как "модель недоступна", а `debug`-логи в проде не видны.
**Исправление:** добавить перед общим обработчиком `except PersonaConfigError: raise` (или вынести рендер/чтение настроек до `try`), а для сценариев со степенью деградации логировать на уровне `error`. Лучше дополнительно проверять полноту персоны при старте (см. WR-03, WR-04).

### WR-03: Ошибки рендера Jinja2 не приводятся к PersonaConfigError, полнота персоны не проверяется при загрузке

**Файл:** `/opt/assistant-core/src/persona/prompts.py:41-52`, `/opt/assistant-core/src/persona/models.py:150-166`
**Проблема:** `render_prompt` пропускает наружу `jinja2.UndefinedError`, `TemplateNotFound`, `TemplateSyntaxError` (тест `test_render_unknown_variable_raises` фиксирует это как норму). Схема допускает персону без `prompts`, без организации `company`/`university` или без нужных `name_forms`, при этом все шаблоны по умолчанию обращаются к `persona.organizations.university.name`, `persona.organizations.company.name`, `persona.name_forms.*`. Такая персона проходит `load_persona` и падает уже во время LLM-вызова, а в местах из WR-02 ещё и тихо. Вторая персона (цель фазы) наткнётся на это первой.
**Исправление:** оборачивать `jinja2.TemplateError` в `PersonaConfigError` без значений контекста; при загрузке требовать наличие набора обязательных ключей `prompts` (8 ключей) и пробный рендер всех шаблонов с синтетическими runtime-переменными на старте (fail-fast в `main()` и в seed).

### WR-04: Параметры привязок коннекторов не валидируются; тихие искажения и сырые исключения

**Файл:** `/opt/assistant-core/src/persona/bindings.py:60-97`, `/opt/assistant-core/config/persona.yaml:96-110`
**Проблема:** `ConnectorBindingConfig.config` это `dict[str, Any]`, значения приводятся в момент вызова. Проверено: в PyYAML 1.1 непроизведённое значение `start: 11:10` читается как число 670 (в файле для 11:10, 13:00 и т.д. стоят кавычки только по этой причине, а `09:30` и `08:15` случайно остаются строками). `str(670)` даёт слот "670", который никогда не совпадёт, и нумерация пар молча ломается. Далее: `slot["number"]` бросает `KeyError`, `subjects` не словарь даёт `AttributeError`, нечисловая норма даёт `ValueError`, а `daily_norm_hours <= 0` не отвергается. Всё это сырые исключения, а не `PersonaConfigError`, и обнаруживаются на рантайме.
**Исправление:** описать pydantic-модели для config каждой роли (`start: str` с паттерном `^\d{2}:\d{2}$`, `number: int`, `daily_norm_hours: float = Field(gt=0)`, `base_url: HttpUrl`) и валидировать их в загрузчике; `bindings.*_settings` оставить тонкими.

### WR-05: В контекст каждого шаблона попадает вся персона, включая правила NDA

**Файл:** `/opt/assistant-core/src/persona/prompts.py:51`
**Проблема:** `persona.model_dump(mode="json")` передаётся в шаблон целиком: `workspaces[*].forbidden_keywords`, `forbidden_remote_substrings`, пути, `telegram`, привязки. Текст шаблона уходит во внешнюю LLM, поэтому одна неосторожная правка шаблона (`{{ persona.workspaces }}`) отправит NDA-данные наружу. Песочница это не предотвращает.
**Исправление:** давать шаблонам явный белый список: `id, display_name, short_name, title, organizations, name_forms, default_area, task_areas, ui`; без `workspaces`, `connectors`, `telegram`, `methodist`.

### WR-06: Пути file_catalog, raw_dir, kb_dir не проверяются; ключевые слова не нормализуются

**Файл:** `/opt/assistant-core/src/persona/models.py:125-147`, `/opt/assistant-core/src/brain/secretary_dialog.py:243-262`, `/opt/assistant-core/src/brain/methodist.py:413-420`
**Проблема:** для `prompts` проверяются `..`, абсолютные пути и symlink, но `FileCatalogEntry.relpath` проверок не имеет. `base_dir / entry.relpath` с `..` или абсолютным путём (`Path.__truediv__` отбрасывает базу) даёт произвольный файл, который секретарь затем предлагает/отправляет в Telegram (`matched_files`). Ключевые слова не приводятся к нижнему регистру: `k in q_lower` никогда не совпадёт с "Тидекс"; пустая строка `""` совпадает с любым запросом (все вопросы "вне области" или "академические").
**Исправление:** в модели: валидатор `relpath` (как для prompts, без суффикса `.jinja2`) и проверка `resolve().is_relative_to(raw_dir.resolve())` при использовании; валидатор keywords: `strip().casefold()`, `min_length=1`.

### WR-07: Сопоставление remote в веб-аудите NDA слабое (регистр, scp-форма) и не fail-closed при отсутствии origin

**Файл:** `/opt/chat-app/backend/app/api/v1/security.py:85-90`
**Проблема:** `s in origin_url` чувствителен к регистру (адреса GitHub регистронезависимы), а запрещённая подстрока формы `host/owner` не совпадёт с scp-формой `git@host:owner/repo` и с SSH-алиасами `git@alias:owner/repo` (проект сам использует SSH-алиасы). Если у NDA-репозитория нет origin (`code != 0`), нарушения нет (зафиксировано тестом N05 как норма). Это поведение унаследовано, но теперь правило стало данными, и ослабление проверки получает дополнительную видимость в этой фазе.
**Исправление:** нормализовать `origin_url` (casefold, замена `:` после хоста на `/`, обрезка `.git`, `ssh://`) и подстроки так же; для NDA без origin выдавать предупреждение/нарушение "remote не задан".

### WR-08: Косметические обращения к привязке schedule_source падают для персон без неё

**Файл:** `/opt/assistant-core/src/models/schedule.py:86-96, 127`, `/opt/assistant-core/src/calendar/client.py:86, 95, 103, 133`, `/opt/assistant-core/src/notifier/live_ticker.py:165, 170`
**Проблема:** `subject_short_names()` и `lesson_slot_numbers()` вызывают `schedule_source_settings()`, которая бросает `PersonaConfigError`, если привязки нет (схема это допускает, `connectors.schedule_source` по умолчанию `[]`). Форматирование строки пары, описания события и тикера (и запасной дайджест в summarizer, вызываемый из обработчика ошибок) падает целиком из-за необязательного словаря сокращений. Вызов происходит по несколько раз на пару с повторным разбором настроек.
**Исправление:** отдельные "мягкие" аксессоры: нет привязки возвращают `{}`/пустые слоты; ошибку конфигурации оставлять только для `base_url` реального источника расписания.

### WR-09: Загрузчик не оборачивает UnicodeDecodeError

**Файл:** `/opt/assistant-core/src/persona/loader.py:44-47`
**Проблема:** `read_text(encoding="utf-8")` при невалидном UTF-8 бросает `UnicodeDecodeError` (подкласс ValueError, но не `OSError`), поэтому он выходит из `load_persona` как есть (проверено на файле с байтом 0xFF), в обход `PersonaConfigError`. Контракт модуля "текст ошибки не содержит входных значений" нарушается, а CLI seed не перехватит его (`except PersonaConfigError`) и упадёт с трассировкой.
**Исправление:** `except (OSError, UnicodeDecodeError) as exc:` с сообщением без содержимого (`getattr(exc, "strerror", None) or "не UTF-8"`).

## Информационные замечания

### IN-01: Идентификаторы Telegram персоны нигде не используются

**Файл:** `/opt/assistant-core/src/persona/models.py:60-75, 213-233`, `/opt/assistant-core/src/main.py:571`
**Проблема:** `resolve_authorized_user_ids` в `src` не вызывается: авторизация по-прежнему идёт по `config.TELEGRAM_USER_ID`. Персона только предупреждает о незаданной переменной. Это создаёт ложное впечатление, что список пользователей управляется данными персоны.
**Исправление:** либо подключить к проверке авторизации, либо явно пометить поле как зарезервированное.

### IN-02: Дрейф копий тестовых файлов отслеживается не для всех общих файлов

**Файл:** `/opt/chat-app/scripts/gate.py:47-50, 538-541`
**Проблема:** шаг дрейфа сверяет только `synthetic_persona.py` и `persona_tokens.py`, хотя `test_hardcode_scanner.py` и `test_synthetic_persona.py` по документации тоже "две одинаковые копии" (сейчас совпадают, но будущее расхождение гейт не поймает). `scripts/security_shield.py` сверяется только тестом P03 в chat-app.
**Исправление:** добавить эти пары в `persona_drift_check`.

### IN-03: Мелкие отличия поведения для персоны по умолчанию

**Файл:** `/opt/assistant-core/src/parser/schedule_parser.py:28-34`, `/opt/assistant-core/src/calendar/client.py:95`
**Проблема:** `ScheduleParser()` без аргумента раньше использовал `https://rasp.guap.ru/`, теперь берёт `base_url` привязки (`https://guap.ru/rasp`); боевые вызовы передают адрес явно, но тесты и скрипты без аргумента изменили адрес. Описание события календаря раньше знало 6 слотов, теперь и 7-й (20:20) даёт строку со слотом. Скорее всего изменение допустимо, но стоит зафиксировать в BASELINE как отступление.

### IN-04: Слова и правила NDA лежат открытым текстом в отслеживаемом git-файле и в общей БД

**Файл:** `/opt/chat-app/scripts/gate.py:69`, `/opt/assistant-core/config/persona.yaml:29-38`
**Проблема:** по решению владельца (OQ1) файл данных персоны исключён из срабатываний shield; значения NDA теперь дублируются в `personas.config_json` и `workspaces` общей БД, откуда chat-app читает без аутентификации. Белый список `/persona/current` и тесты утечки это сейчас закрывают, но защита держится на одном белом списке. Исключение "снимается Фазой 4 (SEC-01)": убедиться, что задача не потеряется, и не добавлять новых эндпоинтов, читающих `config_json` целиком.

### IN-05: Частичная миграция даёт несогласованные тексты для второй персоны

**Файл:** `/opt/assistant-core/src/brain/secretary_dialog.py:126`, `/opt/assistant-core/src/notifier/bot_handler.py:1122`, `/opt/assistant-core/src/brain/summarizer.py` (запасные дайджесты)
**Проблема:** название проекта табеля берётся из персоны, а подпись "ООО «...»" и другие названия организаций остаются литералами рядом (учтено baseline и BASELINE.md). Для персоны с другим `default_project` пользователь увидит смесь данных. Это ожидаемый остаток для Фазы 6, но стоит держать в списке.

### IN-06: Мелкие несогласованности слоя БД chat-app

**Файл:** `/opt/chat-app/backend/app/db.py:24-48, 54-63`
**Проблема:** `get_persona`/`list_workspaces` превращают любой `OperationalError` (в том числе `database is locked`) в "персона не загружена"/503; `resolve_default_area` читает `config["default_area"]` только для плоской формы, а `persona_public_view` принимает и обёрнутую (`"persona"`); `json.loads` повреждённых колонок даёт 500 без пояснения.
**Исправление:** различать "нет таблицы" (`no such table`) и прочие ошибки; использовать единую функцию извлечения персоны.

### IN-07: MethodistService всегда читает настройки персоны, даже если каталоги переданы явно

**Файл:** `/opt/assistant-core/src/brain/methodist.py:44-46`
**Проблема:** `methodist_settings()` вызывается безусловно, поэтому конструктор зависит от наличия персоны, даже когда `raw_dir` и `kb_dir` заданы аргументами (лишняя связность, усложняет юнит-тесты).
**Исправление:** вызывать только если хотя бы один из аргументов равен `None`.

---

_Проверено: 2026-10-03_
_Проверяющий: Claude (gsd-code-reviewer)_
_Глубина: standard_
