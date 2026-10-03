---
phase: 03-persona-kak-dannye
plan: 08
subsystem: persona-prompts
tags: [jinja2, prompt-templates, snapshot, synthetic-persona, PER-09]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-01: эталоны 8 промптов и тесты захвата по месту вызова; 03-04: synthetic_to_config и owner_tokens; 03-07: render_prompt, схема prompts, 4 шаблона"
provides:
  - "4 шаблона персоны по умолчанию: reply_generator, debrief (без завершающего перевода строки), morning_brief, evening_digest; рендер = эталоны 03-01 побайтно"
  - "reply_generator.py, debrief_parser.py, summarizer.py берут системный текст из render_prompt; константы SYSTEM_PROMPT, DEBRIEF_SYSTEM_PROMPT и f-строки system_instruction дайджестов удалены"
  - "8 шаблонов синтетической персоны в tests/fixtures/synthetic_prompts и тест PER-09 по промптам (10 тестов)"
  - "Runtime-переменные дайджестов: date_str, weekday (утро); date_str, weekday, tomorrow_date_str, tomorrow_weekday (вечер)"
affects: [03-09, 03-10, phase-06]

actuals:
  tokens: 5500
  tasks: 2
  commits: 0
  # commits: 0 - chat-app (репозиторий SUMMARY): изменений кода в этом репозитории нет (docs-only). Код - в assistant-core: 3 коммита, см. ниже.

tech-stack:
  added: []
  patterns:
    - "Динамические промпты: даты и день недели - runtime-переменные рендера, идентичность - данные персоны (D-08, D-09)"
    - "Шаблон создаётся копией байтов эталона и точечными подстановками; рендер сверяется с эталоном побайтно"
    - "Рендер системного промпта один раз до цикла попыток моделей, вне блока try, где это позволяет структура метода"

key-files:
  created:
    - /opt/assistant-core/config/prompts/reply_generator_default.jinja2
    - /opt/assistant-core/config/prompts/debrief_default.jinja2
    - /opt/assistant-core/config/prompts/morning_brief_default.jinja2
    - /opt/assistant-core/config/prompts/evening_digest_default.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/secretary.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/intent_router.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/methodist.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/methodist_scope_check.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/reply_generator.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/debrief.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/morning_brief.jinja2
    - /opt/assistant-core/tests/fixtures/synthetic_prompts/evening_digest.jinja2
    - /opt/assistant-core/tests/test_persona_prompts.py
  modified:
    - /opt/assistant-core/config/persona.yaml
    - /opt/assistant-core/src/brain/reply_generator.py
    - /opt/assistant-core/src/brain/debrief_parser.py
    - /opt/assistant-core/src/brain/summarizer.py
    - /opt/assistant-core/tests/test_prompt_snapshot.py

key-decisions:
  - "Имена runtime-переменных дайджестов (решение исполнителя, PER-07): date_str, weekday, tomorrow_date_str, tomorrow_weekday; значения формирует код (strftime и список названий дней), пользователь на них не влияет"
  - "Дебриф рендерится до блока try и кладётся в локальную переменную system_prompt, чтобы ошибка конфигурации персоны не маскировалась запасным разбором; контракт contents (префикс + два перевода строки + пользовательская часть) не изменился"
  - "Формы имени взяты из уже существующих ключей name_forms (nominative, signature, genitive, genitive_first_patronymic, instrumental_first_patronymic, short); новых ключей не добавлялось"

requirements-completed: [PER-07, PER-09, BCK-01]

coverage:
  - id: H1
    description: "4 шаблона персоны по умолчанию (reply_generator, debrief, morning_brief, evening_digest) рендерятся в эталоны 03-01 побайтно; debrief без завершающего перевода строки"
    requirement: "PER-07"
    verification:
      - kind: unit
        ref: "tests/test_prompt_snapshot.py::test_default_template_renders_to_snapshot[reply_generator|debrief|morning_brief|evening_digest]"
        status: pass
      - kind: other
        ref: "python3 -c: debrief_default.jinja2 не оканчивается b'\\n' - код 0"
        status: pass
    human_judgment: false
  - id: H2
    description: "Текст, уходящий в LLM, не изменился: тесты захвата по месту вызова 03-01 (включая test_debrief_call_matches_snapshot, test_reply_generator_/morning_brief_/evening_digest_prompt_matches_snapshot) зелёные без правок"
    requirement: "BCK-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_snapshot.py, test_brain.py, test_debrief_parser.py, test_email_reply_workflow.py: 35 passed"
        status: pass
    human_judgment: false
  - id: H3
    description: "В src/brain нет системных промптов из списка D-08: константы и f-строки удалены"
    requirement: "PER-07"
    verification:
      - kind: other
        ref: "grep -cE 'DEBRIEF_SYSTEM_PROMPT|^SYSTEM_PROMPT' debrief_parser.py reply_generator.py - 0 и 0; grep -c 'Ты — персональный академический ассистент' summarizer.py - 0"
        status: pass
    human_judgment: false
  - id: H4
    description: "Синтетическая персона на тех же render_prompt и потребителе даёт для каждого из 8 промптов текст, отличный от промпта по умолчанию, со своим display_name и без токенов владельца; шаблоны синтетической персоны без токенов владельца"
    requirement: "PER-09"
    verification:
      - kind: unit
        ref: "tests/test_persona_prompts.py::test_synthetic_persona_prompts_differ (8), ::test_synthetic_prompt_templates_have_no_owner_tokens, ::test_same_consumer_path_uses_active_persona: 10 passed"
        status: pass
      - kind: other
        ref: "мутационная проверка: добавление «ГУАП» в синтетический шаблон дебрифа роняет 2 теста; шаблон восстановлен"
        status: pass
    human_judgment: false
  - id: H5
    description: "Гейт качества зелёный; рост числа тестов без регрессии"
    requirement: "BCK-01"
    verification:
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ, chat-app 124 (порог 109), assistant-core 294 (порог 280); lint-imports 5 kept, 0 broken; shield обоих репозиториев, дрейф SHA-256, неизменность assistant.db - все ✓"
        status: pass
    human_judgment: false

plan_head_before: 71ff82220e05de811dedde7fee5fe5ef029bf5eb
plan_head_after: 71ff82220e05de811dedde7fee5fe5ef029bf5eb
assistant_core_head_before: c419e7da3a6a93bb1ae40f5fd082112654a32510
assistant_core_head_after: b004f66
assistant_core_commits: 3
duration: около 12 мин
completed: 2026-10-03
status: complete
---

# Phase 3 Plan 08: Шаблоны ответов, дебрифа и дайджестов, PER-09 по промптам Summary

**Промпты генератора ответов на почту, дебрифа, утреннего и вечернего дайджеста стали Jinja2-шаблонами персоны (даты и дни недели - переменные рендера, имя, титул и организации - данные персоны); для персоны по умолчанию текст совпадает с эталонами 03-01 побайтно, а синтетическая персона на тех же кодовых путях даёт 8 других промптов без токенов владельца.**

## Performance

- **Duration:** около 12 мин
- **Tasks:** 2 из 2
- **Репозитории:** assistant-core (`main`, 3 коммита, без push); chat-app (`master`) - только метаданные плана. Сервисы не запускались (OPS-06): `systemctl is-active` до и после - `failed`, `inactive`, `inactive`.

## Accomplishments

- **Шаблоны персоны по умолчанию:** созданы копией байтов эталонов 03-01 и точечными заменами скриптом (UTF-8, завершающие байты не затрагивались): `reply_generator_default.jinja2` (подпись и представление - формы `nominative`, `signature`, название университета), `debrief_default.jinja2` (формы `genitive`, `genitive_first_patronymic`, `instrumental_first_patronymic`, названия университета и компании; файл не оканчивается переводом строки), `morning_brief_default.jinja2` и `evening_digest_default.jinja2` (`{{ date_str }}`, `{{ weekday }}`, для вечера ещё `{{ tomorrow_date_str }}`, `{{ tomorrow_weekday }}`, форма `short`, названия организаций). Описания дисциплин, групп и подписи кафедры остались литералом (как в 03-07).
- **`config/persona.yaml`:** в `prompts` добавлены 4 ключа; всего 8.
- **Потребители:** `reply_generator.py` - `render_prompt("reply_generator")` один раз перед циклом моделей в `generate_reply` и `refine_reply`; `debrief_parser.py` - `system_prompt = render_prompt("debrief")` до `try`, contents `f"{system_prompt}\n\n{user_prompt}"`; `summarizer.py` - `render_prompt("morning_brief", date_str=..., weekday=...)` и `render_prompt("evening_digest", date_str=..., weekday=..., tomorrow_date_str=..., tomorrow_weekday=...)`; вычисление дат и названий дней осталось в коде (D-09). Константы и f-строки системных промптов удалены.
- **`tests/test_prompt_snapshot.py`:** `TEMPLATE_KEYS` расширен до 8 ключей, `RENDER_VARS` получил литералы для дайджестов («30.09.2026», «среда», «01.10.2026», «четверг»); существующие тесты захвата не менялись.
- **Синтетическая персона (PER-09, промпты):** 8 коротких шаблонов в `tests/fixtures/synthetic_prompts/` (каждый использует `persona.display_name` и поле организаций; дайджесты и `methodist_scope_check` - те же runtime-переменные, что шаблоны владельца); `tests/test_persona_prompts.py` - фикстура `synthetic_persona_loaded` (копирует шаблоны в `tmp_path`, пишет `persona.json` через `synthetic_to_config(..., prompts=...)`, грузит `load_persona`), `test_synthetic_persona_prompts_differ` x8, `test_synthetic_prompt_templates_have_no_owner_tokens`, `test_same_consumer_path_uses_active_persona` (ReplyGenerator с фейком под `use_persona`).

## Task Commits

Репозиторий assistant-core (`c419e7d..b004f66`, измерено `git rev-list --count`: 3 коммита):

1. **Задача 1 (TDD), красная фаза:** `d8ce066` - 4 упавших теста (`4 failed, 15 passed`: нет ключей `prompts` для новых шаблонов).
2. **Задача 1, зелёная фаза:** `96f92b8` - шаблоны, `persona.yaml`, потребители; `35 passed` по четырём тестовым файлам.
3. **Задача 2 (TDD):** `b004f66` - 8 синтетических шаблонов и `test_persona_prompts.py`; `10 passed`.

chat-app: код не менялся (`plan_head_before` = `plan_head_after`, `commits: 0` - docs-only для этого репозитория); метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS) коммитятся отдельно.

## TDD Gate Compliance

- **Задача 1, RED (`d8ce066`):** 4 failed (`PersonaConfigError`: в персоне нет шаблона для `reply_generator`, `debrief`, `morning_brief`, `evening_digest`), 15 passed.
- **Задача 1, GREEN (`96f92b8`):** 35 passed (`test_prompt_snapshot`, `test_brain`, `test_debrief_parser`, `test_email_reply_workflow`).
- **Задача 2:** отдельной красной фазы нет - код (`render_prompt`, потребители) уже готов после Задачи 1, тесты новые и сразу зелёные; их способность падать проверена мутацией (добавление «ГУАП» в синтетический шаблон роняет `test_synthetic_persona_prompts_differ[debrief]` и `test_synthetic_prompt_templates_have_no_owner_tokens`; шаблон восстановлен, повторный прогон - 10 passed). Файл `check tdd-red-evidence` не оформлялся (как в 03-07).
- **REFACTOR:** не требовался.

## Deviations from Plan

### Уточнения без отклонения от смысла плана

- **Шаблоны созданы скриптом Python, а не Edit:** копия байтов эталона и замена строк в UTF-8 (одна и та же техника, что в 03-07); побайтное равенство подтверждено тестом, а у `debrief_default.jinja2` проверен отсутствующий завершающий `\n`.
- **Рендер дебрифа вынесен из f-строки в `system_prompt` до `try`:** ключевая связь плана (`render_prompt('debrief')`) сохранена по смыслу; текст contents не изменился (тест `test_debrief_call_matches_snapshot` зелёный без правок).
- **Рендер дайджестов остался внутри существующего внешнего `try`:** тело методов `generate_morning_brief` и `generate_evening_digest` целиком обёрнуто в `try/except Exception` с запасным детерминированным дайджестом. Ошибка конфигурации персоны (нет шаблона, неизвестная переменная) там не маскируется молча: `logger.exception` пишет трассировку, но пользователь получит запасной дайджест. Менять структуру методов вне объёма плана; при необходимости пробросить `PersonaConfigError` - отдельная правка (кандидат в 03-10).
- **Гигиена секретов** проверена `check_file_content` для `tests/test_persona_prompts.py` и 8 шаблонов: «нарушений: 0».
- **Делегирование agy не использовалось** (шаблоны владельца содержат адреса и имена; синтетические шаблоны короткие, написаны напрямую).
- **Порог гейта задачи 1 (272) и задачи 2 (280):** гейт запущен один раз после Задачи 2 (результат покрывает оба порога: 294 и 124); отдельный прогон гейта между задачами не выполнялся, прогон целевых тестов Задачи 1 - 35 passed (порог 35).

**Total deviations:** 0 auto-fixed; 4 уточнения. **Impact:** критерии плана выполнены.

## Authentication Gates

None.

## Verification Results

- Acceptance Задачи 1: `debrief_default.jinja2` без завершающего `\n` (код 0); `grep -cE "DEBRIEF_SYSTEM_PROMPT|^SYSTEM_PROMPT"` - 0 для `debrief_parser.py` и `reply_generator.py`; `grep -c "Ты — персональный академический ассистент" summarizer.py` - 0; в `persona.yaml` ровно 8 ключей `prompts` (код 0); `lint-imports`: «5 kept, 0 broken».
- Acceptance Задачи 2: `git ls-files tests/fixtures/synthetic_prompts` - 8 файлов; `persona.display_name` в `secretary.jinja2` - не менее 1; `check_file_content` - «нарушений: 0».
- `pytest tests/test_persona_prompts.py`: 10 passed (порог 10).
- Гейт `python3 scripts/gate.py`: **ИТОГ: ЗЕЛЁНЫЙ**, chat-app 124 (порог 109), assistant-core 294 (порог 280).
- Сервисы: `systemctl is-active assistant-worker chat-app dev-bridge` - `failed`, `inactive`, `inactive` (ни одного `active`).

## Threat Model Status

- T-03-26 (подмена текста промптов по умолчанию): митигирована - рендер = эталон побайтно (8 из 8 ключей), тесты захвата 03-01 без правок, у дебрифа нет `\n` в конце.
- T-03-27 (утечка данных владельца в промпт другой персоны): митигирована - `test_synthetic_persona_prompts_differ` и `test_synthetic_prompt_templates_have_no_owner_tokens`, проверена мутацией.
- T-03-28 (SSTI через runtime-переменные): принята - значения (даты, день недели) формирует код; песочница из 03-07.
- T-03-SC (установка пакетов): митигирована - установок нет.

## Known Stubs

None.

## Threat Flags

None.

## Deferred Items

- Остаточный хардкод в `src/brain`: user-промпты и тексты интерфейса (например, «Категория отправителя: Студент ГУАП», «Указания преподавателя (Дмитрия Александровича)» в `reply_generator.py`, названия «ТИДЕКС» в разделах user-промпта дайджестов, детерминированные запасные тексты) остаются остаточным долгом сканера хардкода (03-10, PER-08).
- Решение, нужно ли пробрасывать `PersonaConfigError` из внешнего `try` дайджестов (см. уточнения), - к 03-10 или Фазе 6.
- Адреса почты владельца в шаблонах персоны - литералом (OQ2); запись отступления в BASELINE - 03-10.

## Next Phase Readiness

Все 8 промптов D-08 - шаблоны персоны, рендерятся в эталоны побайтно, вторая персона даёт 8 других промптов на тех же кодовых путях. Готово для 03-09 и 03-10 (сканер хардкода, PER-08); Фазе 6 не придётся повторять перенос системных промптов.

## Self-Check: PASSED

- Файлы: 4 шаблона по умолчанию, 8 синтетических шаблонов, `test_persona_prompts.py` найдены.
- Коммиты assistant-core: `d8ce066`, `96f92b8`, `b004f66` найдены.
