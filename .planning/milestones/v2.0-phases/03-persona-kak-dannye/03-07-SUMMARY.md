---
phase: 03-persona-kak-dannye
plan: 07
subsystem: persona-prompts
tags: [jinja2, sandbox, render-prompt, prompt-templates, snapshot, package-legitimacy]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-01: эталоны промптов и тесты захвата по месту вызова; 03-03: PersonaConfig (prompts, name_forms, base_dir), загрузчик; 03-06: белый список /persona/current"
provides:
  - "src/persona/prompts.py: render_prompt(key, persona=None, **runtime_vars) - SandboxedEnvironment, StrictUndefined, keep_trailing_newline, без автоэкранирования"
  - "Проверка полей prompts: форма пути в models.py (относительный, без .., .jinja2), существование файла внутри каталога персоны в loader.py"
  - "4 шаблона config/prompts/*_default.jinja2 (secretary, intent_router, methodist, methodist_scope_check), блок prompts в config/persona.yaml"
  - "Секретарь, маршрутизатор и методист берут системный текст из render_prompt; константы четырёх промптов удалены"
  - "Jinja2 3.1.6 и MarkupSafe 3.0.3 в .venv assistant-core (одобрено владельцем), строки в requirements.txt и docs/BASELINE.md"
affects: [03-08, 03-09, 03-10, phase-04]

actuals:
  # chat-app (репозиторий SUMMARY): 1 коммит; assistant-core: 3 коммита, см. assistant_core_* ниже
  tokens: 14000
  tasks: 3
  commits: 1

tech-stack:
  added: ["jinja2==3.1.6 (requirements: >=3.1,<4)", "markupsafe==3.0.3"]
  patterns:
    - "Системный промпт - шаблон персоны, рендерится в момент вызова, один раз перед циклом попыток моделей"
    - "Пользовательский ввод (question) - переменная шаблона, а не часть его текста (T-03-22)"
    - "Рендер = эталон побайтно: тест сравнивает encode('utf-8') с эталоном 03-01"

key-files:
  created:
    - /opt/assistant-core/src/persona/prompts.py
    - /opt/assistant-core/config/prompts/secretary_default.jinja2
    - /opt/assistant-core/config/prompts/intent_router_default.jinja2
    - /opt/assistant-core/config/prompts/methodist_default.jinja2
    - /opt/assistant-core/config/prompts/methodist_scope_check_default.jinja2
  modified:
    - /opt/assistant-core/requirements.txt
    - /opt/assistant-core/src/persona/models.py
    - /opt/assistant-core/src/persona/loader.py
    - /opt/assistant-core/config/persona.yaml
    - /opt/assistant-core/src/brain/secretary_dialog.py
    - /opt/assistant-core/src/brain/intent_router.py
    - /opt/assistant-core/src/brain/methodist.py
    - /opt/assistant-core/tests/test_prompt_snapshot.py
    - /opt/assistant-core/tests/test_persona_loader.py
    - /opt/assistant-core/tests/test_fast_intent_router.py
    - docs/BASELINE.md

key-decisions:
  - "Пакеты Jinja2 и MarkupSafe ставятся с ДВУМЯ точными закреплениями (jinja2==3.1.6, markupsafe==3.0.3), в requirements.txt: jinja2>=3.1,<4 и markupsafe==3.0.3; одобрено владельцем"
  - "Рендер выполняется один раз перед циклом попыток моделей, вне блока try: ошибка конфигурации персоны (нет шаблона, неизвестная переменная) не маскируется переходом на запасную модель"
  - "Недельная норма 42.5 в шаблоне секретаря вычисляется как daily_norm_hours * 5 с round(1), чтобы смена нормы в персоне меняла и недельное значение"

requirements-completed: [PER-07, BCK-01, BCK-02]

coverage:
  - id: H1
    description: "Jinja2 3.1.6 и MarkupSafe 3.0.3 установлены только после явного одобрения владельца; pip freeze до/после отличается ровно двумя строками; версии в requirements.txt и docs/BASELINE.md"
    requirement: "PER-07"
    verification:
      - kind: other
        ref: "importlib.metadata: jinja2 3.1.6, markupsafe 3.0.3; diff pip freeze: +Jinja2==3.1.6, +MarkupSafe==3.0.3"
        status: pass
    human_judgment: false
  - id: H2
    description: "4 шаблона персоны по умолчанию рендерятся в эталоны 03-01 побайтно (scope - с вопросом из манифеста)"
    requirement: "PER-07"
    verification:
      - kind: unit
        ref: "tests/test_prompt_snapshot.py::test_default_template_renders_to_snapshot[secretary|intent_router|methodist|methodist_scope_check]"
        status: pass
    human_judgment: false
  - id: H3
    description: "Пути prompts: абсолютный, с .., не .jinja2, пустой - отказ при загрузке; несуществующий файл - PersonaConfigError с ключом и путём; неизвестная переменная - UndefinedError; неизвестный ключ - PersonaConfigError с именем ключа"
    requirement: "PER-07"
    verification:
      - kind: unit
        ref: "tests/test_persona_loader.py::test_prompt_paths_must_stay_inside_persona_dir (5 вариантов), ::test_missing_template_rejected_on_load, ::test_render_unknown_variable_raises, ::test_render_unknown_prompt_key_raises"
        status: pass
    human_judgment: false
  - id: H4
    description: "Текст, уходящий в LLM, не изменился: тесты захвата по месту вызова из 03-01 не правились и зелёные; констант промптов в src и tests нет"
    requirement: "BCK-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_snapshot.py (тесты захвата), test_fast_intent_router.py, test_methodist.py, test_secretary_dialog.py: 33 passed"
        status: pass
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ, chat-app 124, assistant-core 280; lint-imports 5 kept, 0 broken"
        status: pass
    human_judgment: false
  - id: H5
    description: "test_fast_intent_router.py: из строки импорта убрана только удалённая неиспользуемая константа, ни один assert не менялся"
    requirement: "BCK-02"
    verification:
      - kind: unit
        ref: "tests/test_fast_intent_router.py (зелёный в гейте)"
        status: pass
    human_judgment: false

plan_head_before: b6319ccf1ad2e0f18cb9e37639403c95091a6ca2
plan_head_after: dc380760fdb43bfa6edb3323a4d3af2a83cccf01
assistant_core_head_before: cfb829a
assistant_core_head_after: c419e7da3a6a93bb1ae40f5fd082112654a32510
assistant_core_commits: 3
duration: около 35 мин (после чекпойнта)
completed: 2026-10-03
status: complete
---

# Phase 3 Plan 07: Jinja2-шаблоны промптов персоны Summary

**Системные промпты секретаря, маршрутизатора и методиста (и проверка области методиста) стали Jinja2-шаблонами персоны, которые `render_prompt` рендерит в песочнице со `StrictUndefined`; для персоны по умолчанию текст совпадает с эталонами 03-01 байт в байт, Jinja2 3.1.6 и MarkupSafe 3.0.3 установлены с одобрения владельца.**

## Performance

- **Duration:** около 35 мин (Задачи 2-3 после чекпойнта)
- **Tasks:** 3 из 3 (Задача 1 - чекпойнт, закрыт ответом владельца)
- **Репозитории:** assistant-core (`main`, 3 коммита) и chat-app (`master`, 1 коммит `docs/BASELINE.md`); без push. Сервисы не запускались (OPS-06): `systemctl is-active` до и после - `failed`, `inactive`, `inactive`.

## Одобрение владельца (Задача 1, чекпойнт `blocking-human`)

- **Дата и чекпойнт:** 2026-10-03, чекпойнт 03-07 Задача 1 (T-03-SC).
- **Предусловие OPS-06:** `systemctl is-active assistant-worker chat-app dev-bridge` - `failed`, `inactive`, `inactive` (ни одного `active`).
- **Сведения о пакетах (без установки; `pip index`, `pip download --no-deps` в scratchpad, каталог затем удалён):** Jinja2 3.1.6 (сопровождающий Pallets, github.com/pallets/jinja), MarkupSafe 3.0.3 (Pallets, BSD-3-Clause, github.com/pallets/markupsafe). Имена и версии совпали с планом.
- **Примечание про 3.0.4:** простая установка `pip install jinja2==3.1.6` (сухой прогон) потянула бы MarkupSafe 3.0.4, а не 3.0.3.
- **Ответ владельца (реальный пользователь сессии, через AskUserQuestion):** «Одобрено (рекомендуется)» - установить Jinja2 3.1.6 и MarkupSafe 3.0.3 с точным закреплением обеих версий.

## Accomplishments

- **Установка (по одобренному варианту):** `.venv/bin/pip install "jinja2==3.1.6" "markupsafe==3.0.3"`. `pip freeze` до (96 строк) и после: разница ровно две строки (`+Jinja2==3.1.6`, `+MarkupSafe==3.0.3`), PyYAML 6.0.3 не менялся. `requirements.txt` (раздел Core): `jinja2>=3.1,<4` и `markupsafe==3.0.3`. `docs/BASELINE.md` (chat-app, `dc38076`): строки Jinja2, MarkupSafe, PyYAML 6.0.3 (для chat-app «—») и абзац про одобрение и D-10.
- **`render_prompt`:** персона по умолчанию `current_persona()` в момент вызова; `SandboxedEnvironment(FileSystemLoader(base_dir), StrictUndefined, autoescape=False, keep_trailing_newline=True, trim_blocks=False, lstrip_blocks=False)`, окружение кэшируется по `base_dir`; контекст - runtime-переменные и `persona=model_dump(mode="json")` (персона задаётся последней и не подменяется переменными). Нет ключа - `PersonaConfigError` с именем ключа.
- **Пути шаблонов (T-03-23):** валидатор `prompts` в `models.py` (непустой, не абсолютный, без `..`, без обратной косой черты, суффикс `.jinja2`); загрузчик после `_source_path` проверяет, что `resolve()` лежит внутри каталога персоны (symlink раскрывается) и это файл.
- **Шаблоны:** каждый создан копией байтов эталона и точечными заменами: формы имени (genitive, nominative, dative_first_patronymic, short_genitive, initials_genitive), `persona.title`, названия университета и компании, норма часов. Описания дисциплин, ящиков, групп, приказов и адреса почты остались литералом (OQ2). Новых ключей `name_forms` не потребовалось. Завершающие переводы строк совпадают с эталонами.
- **Потребители:** `render_prompt("secretary")`, `render_prompt("intent_router")`, `render_prompt("methodist")`, `render_prompt("methodist_scope_check", question=question)`; константы SECRETARY_SYSTEM_PROMPT, ROUTER_SYSTEM_PROMPT, METHODIST_SYSTEM_PROMPT, SCOPE_CHECK_PROMPT удалены (в `src` и `tests` 0 упоминаний); `test_fast_intent_router.py`: убран только неиспользуемый импорт.

## Task Commits

1. **Задача 1:** чекпойнт (ответ владельца), коммита нет.
2. **Задача 2 (TDD):** assistant-core `8142e0c` (test, красная фаза), `d08d6d1` (feat); chat-app `dc38076` (docs, BASELINE).
3. **Задача 3:** assistant-core `c419e7d` (feat).

Метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS) коммитятся отдельно. Измерено: chat-app `b6319cc..dc38076` - 1 коммит; assistant-core `cfb829a..c419e7d` - 3 коммита.

## TDD Gate Compliance

- **RED (`8142e0c`):** 12 failed, 33 passed. Целевые тесты упали: `test_default_template_renders_to_snapshot` (4) и новые тесты загрузчика (8) - `ModuleNotFoundError: src.persona.prompts` для рендера и «DID NOT RAISE» там, где проверка путей ещё не существовала; импорт нового модуля сделан внутри тела теста, чтобы коллекция не ломалась. Файл с записью `check tdd-red-evidence` не оформлялся (отклонение от формата: свидетельство - вывод pytest выше).
- **GREEN (`d08d6d1`):** 45 passed (33 + 12).
- **REFACTOR:** не требовался.

## Deviations from Plan

### Одобренные владельцем

**1. Установка с двумя закреплениями вместо одного**
- **Что:** шаг 1 плана - `pip install "jinja2==3.1.6"`; выполнено `pip install "jinja2==3.1.6" "markupsafe==3.0.3"`, потому что одиночная установка поставила бы MarkupSafe 3.0.4, а владелец одобрил именно 3.0.3. В `requirements.txt` добавлена строка `markupsafe==3.0.3` (план называл только `jinja2>=3.1,<4`). Разница `pip freeze` - ровно две строки.

### Auto-fixed Issues

**2. [Rule 2 - Missing critical functionality] Обратная косая черта в путях шаблонов**
- **Found during:** Задача 2 (T-03-23)
- **Issue:** `PurePosixPath` не считает `..\x.jinja2` или `C:\x.jinja2` опасным путём; на другой платформе такой путь вышел бы за каталог.
- **Fix:** валидатор отклоняет любую обратную косую черту (поведение для POSIX-путей не меняется; проверка `resolve()` в загрузчике остаётся второй линией).
- **Files modified:** /opt/assistant-core/src/persona/models.py
- **Commit:** d08d6d1

### Уточнения без отклонения от смысла плана

- **Проверка «эталоны не изменены» из плана ложно красная.** Команда берёт первый коммит `MANIFEST.json` (`4ea108b`), но три из четырёх эталонов (`intent_router`, `methodist`, `methodist_scope_check`) добавлены позже, в `caf4789`, который лежит после `4ea108b`; команда возвращает 1 независимо от содержимого. Эквивалентная проверка: `git log -- tests/fixtures/prompts_snapshot/<ключ>.txt` для каждого из четырёх файлов даёт ровно один коммит (создание: `4ea108b` для secretary, `caf4789` для остальных), а `git log 8142e0c~1..HEAD -- tests/fixtures` пуст. Эталоны не правились.
- **Красная фаза вынесена отдельным коммитом** (в 03-02..03-06 тесты и код шли одним коммитом) - по требованию `tdd="true"` и справочника TDD.
- **Замены в шаблонах выполнены скриптом на Python (замена строк в UTF-8, байты завершающего перевода строки не затронуты), а не инструментом Edit:** заменялись все вхождения «ГУАП» и «Тидекс» (включая подпись ящика ГУАП и «ООО «Тидекс»»), строчные «тидекс» в примерах фраз пользователя оставлены. Побайтовое равенство подтверждено тестом.
- Корректность рендера не зависит от `PERSONA_CONFIG_PATH`: тест снимка удаляет переменную через `monkeypatch.delenv`.
- Ошибка вызова `root_pin.sh` из каталога assistant-core (один раз, до коммита chat-app): охранник сообщил о несовпадении корня, ничего не записано; коммиты assistant-core выполняются его собственным git по условиям плана, коммит chat-app - после успешного прогона охранника из `/opt/chat-app`.
- Делегирование agy не использовалось (адреса почты владельца в текстах).

**Total deviations:** 1 одобренное владельцем, 1 auto-fixed (Rule 2), остальное - уточнения. **Impact:** критерии плана выполнены; ложная красная проверка эталонов заменена эквивалентной.

## Authentication Gates

None.

## Verification Results

- `pytest tests/test_prompt_snapshot.py tests/test_persona_loader.py`: 45 passed (порог 34).
- `pytest tests/test_prompt_snapshot.py tests/test_fast_intent_router.py tests/test_methodist.py tests/test_secretary_dialog.py`: 33 passed (порог 33).
- Полный набор assistant-core: 280 passed. `lint-imports`: «5 kept, 0 broken» (persona-is-leaf соблюдён: `src.persona.prompts` импортирует stdlib, jinja2 и `src.persona.*`).
- Гейт `python3 scripts/gate.py`: **ИТОГ: ЗЕЛЁНЫЙ**, chat-app 124 (порог 109), assistant-core 280 (порог 266); shield обоих репозиториев, дрейф SHA-256 синтетической персоны и токенов персоны, неизменность боевой `assistant.db` - все ✓.
- W10: коммит снимка (`4ea108b`) предшествует первому коммиту фазы, менявшему `src/brain` (`c419e7d`) - проверка плана зелёная.
- `git log -1 -- tests/test_prompt_snapshot.py`: `8142e0c` (коммит Задачи 2; после него файл не менялся). `grep` по константам: 0 во всех файлах `src` и `tests`.
- Acceptance Задачи 2: `jinja2>=3.1,<4` в `requirements.txt`, Jinja2 3.1.6 в BASELINE, `SandboxedEnvironment` и `keep_trailing_newline=True` в `prompts.py`, совпадение завершающих переводов строки, `{{ persona.` в шаблонах: secretary 11, intent_router 4, methodist 12 строк.

## Threat Model Status

- T-03-SC (установка пакетов, SUS): митигирована - блокирующий чекпойнт, ответ владельца записан, точные версии, `pip freeze` до/после - две строки.
- T-03-22 (SSTI): митигирована - `SandboxedEnvironment`, `StrictUndefined`, шаблоны только из каталога персоны, вопрос - переменная. Полный разбор SSTI - `/gsd-secure-phase`.
- T-03-23 (обход каталога): митигирована - валидатор формы пути, проверка `resolve()` и существования в загрузчике, тест `test_prompt_paths_must_stay_inside_persona_dir` (5 вариантов).
- T-03-24 (подмена текста промпта): митигирована - рендер = эталон побайтно и тесты захвата 03-01 без правок.
- T-03-25 (адреса почты в шаблонах): принята по плану (решение владельца OQ2), запись в BASELINE - 03-10.

## Known Stubs

None.

## Threat Flags

None.

## Deferred Items

- Остальные четыре промпта (`reply_generator`, `debrief`, `morning_brief`, `evening_digest`) - 03-08 (D-08).
- Адреса почты владельца остаются литералом в шаблонах (OQ2); запись отступления в BASELINE - 03-10.

## Next Phase Readiness

`render_prompt` и схема `prompts` готовы для 03-08: добавить ключи в `persona.yaml`, шаблоны `*_default.jinja2` и перевести оставшиеся модули. Ограничение: шаблоны не должны содержать `{{`, `{%`, `{#` кроме намеренных подстановок.

## Self-Check: PASSED

- Файлы: `prompts.py` и четыре шаблона найдены.
- Коммиты: `8142e0c`, `d08d6d1`, `c419e7d` (assistant-core) и `dc38076` (chat-app) найдены.
