---
phase: 03-persona-kak-dannye
plan: 10
subsystem: acceptance
tags: [persona, hardcode-scanner, baseline, synthetic-persona, PER-08, PER-09, BCK-01, BCK-02]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-04: owner_tokens и synthetic_to_config; 03-07/03-08: шаблоны промптов; 03-09: привязки коннекторов и аксессоры src/persona/bindings.py"
provides:
  - "Фикстура default_persona_config в обоих репозиториях; test_synthetic_persona.py (обе копии, 7 тестов) без констант-копий профиля владельца"
  - "Сканер хардкода (tests/test_hardcode_scanner.py и backend/tests/test_hardcode_scanner.py) и baseline-словарь HARDCODE_BASELINE, который не может расти"
  - "tests/test_persona_config.py: PER-09 (промпты, пространства, дефолты, scope-решения второй персоны, нет ветвления по id)"
  - "docs/BASELINE.md: Включено в Фазе 3, Итог после Фазы 3, Известные отступления, Разморозка, правило 6"
affects: [phase-04, phase-06]

actuals:
  tokens: 20000
  tasks: 3
  commits: 3
  # commits: 3 - chat-app (репозиторий SUMMARY), измерено git rev-list --count 2dacdff..HEAD до коммита метаданных. assistant-core: 2 коммита (8f61982..1aa9d50).

tech-stack:
  added: []
  patterns:
    - "Токены профиля вычисляются из данных персоны по умолчанию (owner_tokens), копий профиля в тестах нет"
    - "Baseline с двойной проверкой «новое/устаревшее» (по образцу compare_shield_findings): растёт нельзя, сокращать обязательно"
    - "Счёт находок - число строк файла с токеном класса, сообщения без текста токена"

key-files:
  created:
    - /opt/assistant-core/tests/test_hardcode_scanner.py
    - /opt/assistant-core/tests/hardcode_baseline.py
    - /opt/assistant-core/tests/test_persona_config.py
    - /opt/chat-app/backend/tests/test_hardcode_scanner.py
    - /opt/chat-app/backend/tests/hardcode_baseline.py
  modified:
    - /opt/assistant-core/tests/conftest.py
    - /opt/assistant-core/tests/test_synthetic_persona.py
    - /opt/assistant-core/tests/synthetic_persona.py
    - /opt/chat-app/backend/tests/conftest.py
    - /opt/chat-app/backend/tests/test_synthetic_persona.py
    - /opt/chat-app/backend/tests/synthetic_persona.py
    - /opt/chat-app/docs/BASELINE.md

key-decisions:
  - "Сканер считает строки с токеном класса; allowlist - config/, tests/, backend/tests/, docs/, .planning/, *.md; baseline сгенерирован программой один раз и просмотрен вручную"
  - "Идентификатор источника расписания в backend/app/db.py оставлен в baseline (строка строится assistant-core из SCHEDULE_TARGET_ID), а не перенесён в данные: это тот же долг, что и SCHEDULE_TARGET_ID"
  - "Опорным SHA-256 боевой БД для следующих фаз считается 726c4e99... (старт Фазы 3); расхождение с записью Фазы 1 (baef14f7...) зафиксировано в BASELINE, причина не установлена"

requirements-completed: [PER-08, PER-09, BCK-01, BCK-02]

coverage:
  - id: I1
    description: "Каркас второй персоны проверяется против данных персоны по умолчанию: константы-копии профиля удалены, токены покрывают прежний denylist целиком, обе копии файлов байт-в-байт, 7 тестов в файле"
    requirement: "PER-08"
    verification:
      - kind: unit
        ref: "backend/tests/test_synthetic_persona.py и tests/test_synthetic_persona.py: 7 passed в каждом; cmp обеих пар - код 0; acceptance по покрытию denylist - код 0"
        status: pass
    human_judgment: false
  - id: I2
    description: "Сканер хардкода в обоих репозиториях; baseline не растёт: новая находка, новый файл и устаревшая запись делают тест красным"
    requirement: "PER-08"
    verification:
      - kind: unit
        ref: "tests/test_hardcode_scanner.py::test_scanner_counts_lines_and_respects_allowlist, ::test_no_new_hardcode_outside_baseline, ::test_baseline_has_no_stale_entries (3 passed); то же в backend/tests/test_hardcode_scanner.py"
        status: pass
      - kind: other
        ref: "ручная проверка красного: строка с токеном в существующий файл baseline (chat-app и assistant-core), в файл вне baseline (chat-app), завышенная запись baseline (chat-app) - все три случая дали красный тест, изменения откатаны"
        status: pass
    human_judgment: false
  - id: I3
    description: "PER-09: персона по умолчанию грузится без PERSONA_CONFIG_PATH; вторая персона даёт другие промпты, пространства, дефолты и scope-решения; в src нет литералов id персон"
    requirement: "PER-09"
    verification:
      - kind: unit
        ref: "tests/test_persona_config.py: 8 passed (6 функций, одна параметризована тремя ключами промптов)"
        status: pass
    human_judgment: false
  - id: I4
    description: "BASELINE фиксирует итог фазы, известные отступления, порядок разморозки и SHA-256 боевой БД; без NDA-слов, Telegram-ID и адресов почты"
    requirement: "BCK-01"
    verification:
      - kind: other
        ref: "grep по заголовкам и OQ2 - код 0; число NDA-слов из CORPORATE_NDA_KEYWORDS в документе - 0; адресов почты и длинных числовых идентификаторов - 0"
        status: pass
    human_judgment: false
  - id: I5
    description: "Тесты не удалены и не ослаблены, гейт зелёный: assistant-core 326 (порог 302), chat-app 127 (порог 112)"
    requirement: "BCK-02"
    verification:
      - kind: other
        ref: "git diff --name-status по каталогам тестов обоих репозиториев от баз фазы - строк D нет; число def test_ в изменённых файлах не уменьшилось; python3 scripts/gate.py - ИТОГ: ЗЕЛЁНЫЙ, код 0"
        status: pass
    human_judgment: false

plan_head_before: 2dacdffaab6ee70963171a99abf62154568ea57a
plan_head_after: 828845a4ba336d9600bd90d3eecb28d31db7c268
assistant_core_head_before: 8f619829336f0a87bb00f177324e1786797054c1
assistant_core_head_after: 1aa9d500f48cd3d47816d98c05917d751e5ab1eb
assistant_core_commits: 2
duration: около 30 мин
completed: 2026-10-03
status: complete
---

# Phase 3 Plan 10: приёмка фазы Summary

**Каркас второй персоны переключён с констант-копий профиля владельца на данные персоны по умолчанию, сканер хардкода с baseline, который может только сокращаться, стоит в обоих репозиториях, PER-09 доказан сводным `test_persona_config.py`, BASELINE фиксирует итог Фазы 3, отступления и порядок разморозки; гейт зелёный (assistant-core 326, chat-app 127).**

## Performance

- **Duration:** около 30 мин
- **Tasks:** 3 из 3
- **Репозитории:** assistant-core (`main`, 2 коммита, без push); chat-app (`master`, 3 коммита кода/доков + коммит метаданных). Сервисы не запускались (OPS-06): `systemctl is-active` до и после - `failed`, `inactive`, `inactive`.

## Accomplishments

- **Каркас на данных (Задача 1):** фикстура `default_persona_config` (assistant-core: `load_persona().model_dump(mode="json")` без `PERSONA_CONFIG_PATH`; chat-app: `config_json` строки `settings.PERSONA_ID` из копии БД `persona_session_db`). В `test_synthetic_persona.py` удалены `OWNER_TOKEN_DENYLIST` и `CURRENT_HARDCODED_DEFAULTS`; `test_no_owner_tokens` проверяет токены `owner_tokens(default_persona_config)`, `test_every_identifying_field_differs_from_default_persona` сравнивает по тем же полям, что раньше. Тестов в файле по-прежнему 7, копии байт-в-байт. Докстринг `synthetic_persona.py`: «Ожидают Фазы 3» стал «Включено в Фазе 3» со ссылками на тесты.
- **Сканер и baseline (Задача 2):** `scan_files`/`scan_repo`/`compare`/`render_baseline`, `REPO` через git, `SCANNED_SUFFIXES`, `ALLOWLIST_PREFIXES`; три теста в каждом репозитории. Baseline сгенерирован один раз и просмотрен: assistant-core 35 файлов и 515 строк (name 45, organization 368, domain 94, account 8), chat-app 4 файла и 22 строки (name 2, organization 16, domain 2, account 2). Из `src/persona/`, `index.html` и `security.py` находок нет.
- **PER-09 (Задача 2):** `tests/test_persona_config.py` - 6 тестов-функций (8 прогонов): персона по умолчанию без PERSONA_CONFIG_PATH; промпты secretary, intent_router, methodist; пространства (id и пути не пересекаются, 4 против 3, три уровня допуска, правила remote NDA не пересекаются); дефолты (область, табель, расписание, ЛК, каталог методиста); scope-решения `MethodistService.check_scope` (три вопроса: слово области владельца, название компании синтетической персоны, слово из стоп-списка владельца); нет литералов id персон в `src`.
- **BASELINE (Задача 3):** разделы «Включено в Фазе 3», «Итог после Фазы 3» (таблица гейта, числа тестов, lint-imports «5 kept», SHA-256 БД), «Известные отступления Фазы 3», «Разморозка (для владельца)», правило 6.

## Task Commits

1. **Задача 1:** assistant-core `02c29c5`, chat-app `8678c69` - фикстуры, каркас, докстринг.
2. **Задача 2:** assistant-core `1aa9d50` (сканер, baseline, `test_persona_config.py`), chat-app `7937a77` (сканер, baseline).
3. **Задача 3:** chat-app `828845a` - `docs/BASELINE.md`.

Число коммитов измерено `git rev-list --count`: chat-app 3 (`2dacdff..828845a`), assistant-core 2 (`8f61982..1aa9d50`). Метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS) коммитятся отдельно.

## TDD Gate Compliance

Задача 2 помечена `tdd="true"`, но продакшен-код не менялся (сканер и тесты - сами тесты). Классический RED-коммит с падающим тестом до реализации не оформлялся: красное состояние подтверждено вручную на внесённых изменениях (см. проверку «не растёт» ниже), а сами тесты сразу зелёные. `check tdd-red-evidence` не оформлялся (как в 03-07..03-09). REFACTOR не требовался.

## Deviations from Plan

### Auto-fixed Issues

None - по существу план выполнен как написан. Уточнения:

- **Состав baseline assistant-core шире ожидаемого:** кроме перечисленных в плане, в baseline попали `reconcile_report.json` (отслеживаемый отчёт сверки в корне репозитория, 23 строки), `src/brain/{debrief_parser,intent_router,reply_generator,summarizer}.py`, `src/composition.py`, `src/detector/tg_filter.py`, `src/connectors/aadhk/parser.py`, `src/connectors/guap_lms/{__init__,provider}.py`, `src/models/second_brain.py`, `src/models/schedule.py` и несколько скриптов (`scripts/` - 12 файлов). Причина: сканер считает любую подстроку токена (в том числе в идентификаторах и docstring); записано по факту сканирования с просмотром, в BASELINE описано группами. Файлов из `src/persona/` нет, как требовал план.
- **chat-app `backend/app/db.py`:** одна строка с шаблоном идентификатора источника расписания. План ожидал в `backend/app/` нулевых находок или причину в SUMMARY: строку строит assistant-core из `SCHEDULE_TARGET_ID`, перенос в данные - вместе с этим долгом (Фаза 6).
- **Количество функций test_persona_config.py:** 6 функций по плану; одна параметризована тремя ключами промптов, поэтому pytest показывает 8 passed (порог плана 9 для двух файлов assistant-core: 3 + 8 = 11).
- **Гейт:** запущен дважды - после Задачи 2 (ЗЕЛЁНЫЙ, 326/127) и после Задачи 3 (ЗЕЛЁНЫЙ, 326/127); отдельного прогона после Задачи 1 не было, её покрывают прогон тестов обеих копий и итоговый гейт.
- **Делегирование agy не использовалось** (значения владельца, NDA-правила плана).

**Total deviations:** 0 auto-fixed. **Impact:** критерии плана выполнены; расширенный состав baseline и одна строка в `backend/app/db.py` описаны выше.

## Authentication Gates

None.

## Verification Results

- Acceptance Задачи 1: `grep -c` констант - 0; токены персоны покрывают все 8 строк прежнего denylist (код 0); «Включено в Фазе 3» найдено; число `def test_` не уменьшилось (код 0); `cmp` обеих пар - код 0; 7 passed в каждом репозитории.
- Acceptance Задачи 2: `src/persona/`, `index.html`, `security.py` в baseline обоих репозиториев - 0; `def test_no_persona_id_branching_in_src` найден; гигиена секретов (`check_file_content`) пяти файлов - «нарушений: 0»; сканеры 3 + 3 passed, `test_persona_config.py` 8 passed. Проверка «не растёт» на временных правках с откатом: строка с токеном в файл из baseline (chat-app `backend/app/db.py`: «строк: 2 (в baseline 1)»; assistant-core `src/brain/intent_router.py`), в файл вне baseline (chat-app `backend/app/main.py`: «строк: 1 (в baseline 0)») и завышенная запись baseline (устаревшая запись: «в baseline 2, найдено 1») - красный тест во всех случаях; после отката `git status` без изменений в отслеживаемых файлах.
- Acceptance Задачи 3: BASELINE содержит «Итог после Фазы 3», «Включено в Фазе 3», OQ2, не содержит «Ожидают Фазы 3»; NDA-слов из `CORPORATE_NDA_KEYWORDS` - 0; адресов почты - 0; BCK-02 по обоим репозиториям - строк `D` нет.
- `lint-imports`: assistant-core «5 kept, 0 broken», chat-app «1 kept, 0 broken».
- Гейт `python3 scripts/gate.py`: **ИТОГ: ЗЕЛЁНЫЙ**, код 0; chat-app 127 (порог 112), assistant-core 326 (порог 302); shield, оба дрейфа SHA-256 и неизменность `assistant.db` - все ✓. Боевая БД: SHA-256 `726c4e99...` равен значению старта Фазы 3.
- Сервисы: `systemctl is-active assistant-worker chat-app dev-bridge` - `failed`, `inactive`, `inactive` (ни одного `active`).

## Threat Model Status

- T-03-32 (тихий рост baseline): митигирована - тесты «новая находка» и «устаревшая запись», baseline сгенерирован один раз с ручным просмотром, красный на внесённой строке проверен вручную.
- T-03-33 (NDA-слова, ID, адреса в BASELINE): митигирована - проверки acceptance пройдены.
- T-03-34 (ослабление каркаса): митигирована - 7 тестов сохранены, токены покрывают прежний denylist, копии байт-в-байт, функций `test_*` не стало меньше.
- T-03-SC (установка пакетов): митигирована - установок нет.

## Known Stubs

None.

## Threat Flags

None.

## Остаточный долг и вопросы к владельцу

- **Изменение поведения персоны по умолчанию, ждёт решения владельца (из 03-09):** строка «Пара: 7» в описании события календаря для пары 20:20 (раньше седьмого слота в календаре не было). Записано в BASELINE, «Известные отступления», п. 6.
- **Остаточный хардкод (baseline сканера до Фазы 6):** `SCHEDULE_TARGET_ID`; имена функций с названием организации; хост проверки входа и SSO-хост ЛК; тексты интерфейса Telegram и подписи ссылок; текст отказа методиста в `ask`; DDL-дефолты и стартовые данные `src/storage/db.py`; `PersonaConfigError` проглатывается внешними `try` (дайджесты, `_get_tydex_context`).
- **Расхождение SHA-256 боевой БД:** на старте Фазы 1 `baef14f7...`, на старте Фазы 3 и сейчас `726c4e99...`; файл последний раз записан 2026-10-02 15:11 UTC (после Фаз 1 и 2, до 03-01). Причина не установлена; в BASELINE опорным назначено `726c4e99...`.
- **`reconcile_report.json`:** отслеживаемый в корне assistant-core отчёт с данными владельца (23 строки в baseline); решение - убрать из репозитория или оставить - за владельцем (вне плана).

## Next Phase Readiness

Фаза 3 завершена: профиль владельца в данных, вторая персона проходит через те же кодовые пути, остаточный долг зафиксирован baseline, который может только сокращаться. Разморозка сервисов - решение владельца (порядок в BASELINE). Готово к проверке фазы и к Фазе 4.

## Self-Check: PASSED

- Файлы `test_hardcode_scanner.py`, `hardcode_baseline.py` в обоих репозиториях, `tests/test_persona_config.py`, `docs/BASELINE.md` найдены на диске.
- Коммиты assistant-core `02c29c5`, `1aa9d50` и chat-app `8678c69`, `7937a77`, `828845a` найдены в `git log`.
- Измеренное число коммитов плана: chat-app 3 (до коммита метаданных), assistant-core 2.
