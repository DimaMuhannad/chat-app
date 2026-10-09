---
phase: 03-persona-kak-dannye
plan: 05
subsystem: security
tags: [security-tile, nda, workspaces, characterization, fail-closed, equivalence-test]

requires:
  - phase: 03-persona-kak-dannye
    provides: "03-02/03-03/03-04: таблица workspaces (персоны по умолчанию и синтетической), seed-CLI, фикстура persona_session_db"
provides:
  - "DatabaseService.list_workspaces(persona_id): пространства в порядке position, JSON-списки декодированы"
  - "security.py без реестра-константы: NdaRemoteRule, nda_rule_for, DEFAULT_REMOTE_VIOLATION, _persona_workspaces (503 без данных), audit_path(target_path, nda_rule=None)"
  - "test_nda_equivalence.py: явный чек-лист N01-N09, S01-S09, P02-P03 на временных git-репозиториях плюс D01, D02 (2), 503"
  - "test_security_golden.py: эталон /security/overview и /security/audit (4 записи, порядок, ключи)"
  - "test_security_api.py на данных персоны без ослабления ассертов"
affects: [03-06, 03-07, 03-08, 03-09, 03-10, phase-04]

actuals:
  tokens: 14200
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Характеризация отдельным коммитом до правки кода; единственная точка адаптации - блок _audit в тесте"
    - "Признак NDA - допуск пространства (clearance), правила remote и сообщение - данные строки workspaces"
    - "Пустые данные персоны - 503, а не пустой «чистый» ответ"
    - "Тесты с NDA-словами сравнивают только числа и булевы флаги: слова не попадают в вывод pytest"

key-files:
  created:
    - backend/tests/test_nda_equivalence.py
    - backend/tests/test_security_golden.py
  modified:
    - backend/app/api/v1/security.py
    - backend/app/db.py
    - backend/tests/test_security_api.py

key-decisions:
  - "Web-аудит по-прежнему не проверяет слова NDA (расхождение 1:1, BCK-01); зафиксировано чек-листом, закрывает Фаза 4 (SEC-01/02)"
  - "Правило remote применяется только при clearance == restricted_nda; сообщение - remote_violation_message пространства, при отсутствии нейтральный текст без названий организаций"
  - "Фильтр project_id при пустых данных персоны тоже отдаёт 503 (одно место проверки в _persona_workspaces)"

requirements-completed: [PER-03, PER-04, BCK-01, BCK-02]

coverage:
  - id: G1
    description: "Сегодняшнее поведение NDA-проверок Web и shield закреплено явным чек-листом на настоящих git-репозиториях до правки security.py (отдельный коммит, только backend/tests)"
    requirement: "PER-04"
    verification:
      - kind: unit
        ref: "backend/tests/test_nda_equivalence.py (N01-N09, S01-S09, P02, P03), коммит 6abd327"
        status: pass
    human_judgment: false
  - id: G2
    description: "Вывод /security/overview и /security/audit для персоны по умолчанию совпадает с эталоном: 4 записи, порядок, эмодзи, подписи, цвета, пути, air-gap отсутствующих каталогов"
    requirement: "PER-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_security_golden.py::test_overview_golden_matches_today, ::test_audit_all_golden_order (файл не менялся после характеризации)"
        status: pass
    human_judgment: false
  - id: G3
    description: "Реестр удалён, NDA-правила берутся из данных пространства; чек-лист проходит на данных, синтетическая персона получает свои результаты, правила не пересекаются между персонами"
    requirement: "PER-04"
    verification:
      - kind: unit
        ref: "backend/tests/test_nda_equivalence.py::test_d01_owner_rules_come_from_data, ::test_d02_synthetic_overview_lists_its_workspaces, ::test_d02_synthetic_rule_applies_only_its_data"
        status: pass
    human_judgment: false
  - id: G4
    description: "Нет пространств персоны - 503 у overview и audit (fail-closed)"
    requirement: "PER-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_nda_equivalence.py::test_overview_and_audit_503_without_workspaces"
        status: pass
    human_judgment: false
  - id: G5
    description: "test_security_api.py переписан на данные персоны без ослабления: 4 записи, restricted_nda у NDA-пространства, аудит всех passed"
    requirement: "BCK-02"
    verification:
      - kind: unit
        ref: "backend/tests/test_security_api.py (3 passed)"
        status: pass
      - kind: other
        ref: "python3 scripts/gate.py: ИТОГ: ЗЕЛЁНЫЙ, chat-app 112, assistant-core 268"
        status: pass
    human_judgment: false

plan_head_before: 494e6dd8e3324fcf93adbf39db27ceda960137bf
plan_head_after: 6ae0e5309ed8f644606de2b781e4a3881d045195
duration: 14min
completed: 2026-10-03
status: complete
---

# Phase 3 Plan 05: Security Tile из рабочих пространств персоны и NDA-эквивалентность Summary

**Security Tile и Web-аудит строятся из таблицы `workspaces` персоны `settings.PERSONA_ID` (реестр-константа удалена, NDA-признак - `clearance`, подстроки remote и сообщение - данные пространства, без данных - 503), а явный NDA-чек-лист из 42 проверок на настоящих git-репозиториях закоммичен до правки и проходит после неё без изменения единой строки `assert`.**

## Performance

- **Duration:** около 14 мин
- **Tasks:** 2 из 2
- **Репозиторий:** только chat-app (`master`, 2 коммита, без push); `scripts/security_shield.py` не менялся (D-15)

## Accomplishments

- **Характеризация до правки (коммит `6abd327`, только `backend/tests`):** `test_nda_equivalence.py` (N01-N09 Web, S01-S09 shield, P02-P03; 33 теста с параметризацией) и `test_security_golden.py` (2 теста). Эталон: 4 записи в порядке chat-app, assistant-core, tydex-optics, guap-physics с дословными эмодзи, account, clearance_label, color, путями; air-gap для двух отсутствующих каталогов; множества ключей записи и верхнего уровня. Все 35 тестов зелёные на неизменённом `security.py`.
- **Перевод на данные (коммит `6ae0e53`):** `PROJECTS_REGISTRY` удалён; `_persona_workspaces()` читает `DatabaseService.list_workspaces(settings.PERSONA_ID)` и при пустом результате отдаёт 503. `nda_rule_for(ws)` возвращает `NdaRemoteRule` только для `restricted_nda`; `audit_path(target_path, nda_rule=None)` проверяет подстроки remote из правила и выдаёт сообщение пространства. Литерал аккаунта и `is_tydex` из кода убраны. Формат ответов не менялся.
- **Тест эквивалентности:** при переходе изменено только тело `_audit` в помеченном блоке адаптера; ни одна из 60 строк `assert` характеризации не изменена и не удалена (проверка `comm` на отсортированных множествах). Добавлены D01 (правило из данных равно строке владельца; правила нет у не-NDA пространств), D02 (синтетическая персона: 3 записи, все virtual_airgap, 3 уровня допуска; её правило ловит только её подстроку и даёт её сообщение, правило владельца на её remote не действует, названий организаций владельца в сообщении нет), 503 без данных (overview, audit, audit с `project_id`).
- **`test_security_api.py`:** те же три теста с теми же проверками; число пространств и NDA-запись берутся из БД (`len == 4` и `== len(list_workspaces)`), одиночный аудит - по id строки с `position` 0.

## Task Commits

1. **Задача 1:** `6abd327` (test) - характеризация NDA-чек-листа и вывода Security Tile
2. **Задача 2:** `6ae0e53` (feat) - Security Tile из workspaces, `list_workspaces`, D01/D02/503, переписанный `test_security_api.py`

Метаданные плана (SUMMARY, STATE, ROADMAP, REQUIREMENTS) коммитятся отдельно. Измеренное число коммитов: 2 (`494e6dd..HEAD`).

## TDD-заметка

Характеризационные тесты написаны и закоммичены до кода (полноценный порядок «сначала тест»). Для новых тестов Задачи 2 (D01, D02, 503, адаптер) красная фаза проверена прогоном до правки `security.py`: 25 failed, 17 passed (адаптер уже обращался к несуществующим `nda_rule_for` и `nda_rule=`); зелёная фаза после правки: 42 passed. По требованию плана (один коммит перевода, адаптер и код обязаны меняться вместе, иначе характеризация красная между коммитами) красная фаза Задачи 2 отдельным коммитом не оформлялась.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Собственный тест D02 подменял и данные владельца**
- **Found during:** Задача 2, первый зелёный прогон
- **Issue:** `test_d02_synthetic_rule_applies_only_its_data` делал `monkeypatch.setattr(settings, "PERSONA_ID", <синтетическая>)`, из-за чего `_owner_nda_workspace()` и `_owner_remote()` тоже читали синтетическую персону, и «подстрока владельца» оказалась подстрокой синтетической персоны.
- **Fix:** подмена `PERSONA_ID` из теста убрана: правила владельца берутся из его данных, синтетические - по явному id через `list_workspaces`.
- **Files modified:** backend/tests/test_nda_equivalence.py
- **Commit:** 6ae0e53

### Уточнения без отклонения от смысла плана

- В плане опечатка `{"Generic Bearer Secret»}`; в тесте P02 использовано `{"Generic Bearer Secret"}`.
- Тестов больше порога плана (параметризация N01, N06, N07): 35 после Задачи 1 (порог 22), 42 в трёх файлах после Задачи 2 (порог 29).
- 503 проверено и для `POST /security/audit` с `project_id` (одно общее место проверки).
- Делегирование agy не использовалось (NDA-логика, D-20).

**Total deviations:** 1 auto-fixed (Rule 1, в собственном тесте). **Impact:** на артефакты плана не влияет.

## Authentication Gates

None.

## Verification Results

- `test_nda_equivalence.py` + `test_security_golden.py` на неизменённом `security.py`: 35 passed (порог 22); три файла после перевода: 42 passed (порог 29).
- Порядок коммитов: характеризация (`6abd327`) - предок первого коммита фазы, меняющего `security.py` (`6ae0e53`); последний коммит характеризации не затрагивает `backend/app`.
- Строки `assert` характеризации сохранены (в коммите 60, `comm -23` пусто); `test_security_golden.py` после `6abd327` не менялся; в `backend/tests/` с базовой точки фазы нет удалённых файлов.
- Acceptance: `PROJECTS_REGISTRY`, литерал аккаунта и `is_tydex` в `security.py` - 0 вхождений; `list_workspaces(settings.PERSONA_ID)` и `status_code=503` найдены; `check_file_content` для новых и изменённых файлов - нарушений 0.
- Гейт `python3 scripts/gate.py`: **ИТОГ: ЗЕЛЁНЫЙ**; chat-app 112 тестов (порог 97), assistant-core 268 (порог 259); `lint-imports` оба, shield `--all` оба, обе строки дрейфа, боевая `assistant.db` не изменена. Промежуточный прогон после Задачи 1: 108 тестов, зелёный.
- NDA-слова не печатались; сервисы не запускались (assistant-worker `failed`, chat-app и dev-bridge `inactive`, как и до плана).

## Threat Model Status

- T-03-14 (сужение NDA-блокировок): митигирована - чек-лист до правки, assert-строки сохранены, D01/D02.
- T-03-15 (пустые данные - «чисто»): митигирована - 503, тест `test_overview_and_audit_503_without_workspaces`.
- T-03-16 (состав ответа): принята - ключи и формат ответа не менялись.
- T-03-17 (литералы секретов и NDA-слова в тестах): митигирована - секреты собираются из частей, слова читаются из shield, проверка `check_file_content` новых файлов - 0.
- T-03-SC: установок пакетов не было.

## Known Stubs

None.

## Threat Flags

None.

## Next Phase Readiness

Тест эквивалентности (чек-лист N/S/P) перезапускается в Фазе 4 против общей библиотеки (D-15); блок адаптера `_audit` - единственное место смены вызова. Расхождение «Web не проверяет слова NDA» и правило shield «NDA по подстроке пути» записаны чек-листом (S01) для Фазы 4. Блокеров нет.

## Self-Check: PASSED

- Файлы `backend/tests/test_nda_equivalence.py`, `backend/tests/test_security_golden.py`, `backend/app/api/v1/security.py`, `backend/app/db.py`, `backend/tests/test_security_api.py` найдены на диске.
- Коммиты `6abd327` и `6ae0e53` найдены в `git log`; измеренное число коммитов плана: 2.
