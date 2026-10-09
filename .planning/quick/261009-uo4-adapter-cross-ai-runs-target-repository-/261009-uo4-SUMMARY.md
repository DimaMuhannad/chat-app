---
phase: quick-261009-uo4
plan: 01
subsystem: cross-ai-adapter
tags: [cross-ai, agy, quality-gate, GATE-05, D-15]
requires: []
provides:
  - "scripts/agy_cross_ai.sh запускает гейт целевого репозитория (--repo)"
affects: [assistant-core 01-09 (переключение cross_ai_command и пробный прогон)]
key-files:
  modified:
    - scripts/agy_cross_ai.sh
    - backend/tests/test_agy_cross_ai.py
    - .claude/skills/agy-delegate/SKILL.md
decisions:
  - "Приоритет гейта: AGY_GATE_CMD -> $TOP/scripts/gate.py (cwd $TOP) -> гейт chat-app рядом с адаптером (cwd $SCRIPT_DIR/..)"
  - "Новые тесты работают на побайтной копии адаптера с заглушкой gate.py рядом: настоящий гейт chat-app из тестов не запускается"
status: complete
metrics:
  completed: 2026-10-09
  tasks: 3
  commits: 1
  plan_head_before: 279dc5a
  plan_head_after: 6b3b2ac48a1e5d6c7072c68460f845f4d042b01d
actuals:
  tasks: 3
  commits: 1
---

# Quick 261009-uo4: адаптер cross-AI запускает гейт целевого репозитория

Адаптер `scripts/agy_cross_ai.sh` теперь выбирает гейт качества по приоритету: `AGY_GATE_CMD` (только тесты), затем `scripts/gate.py` целевого репозитория из `--repo` (запуск из его корня), иначе гейт chat-app рядом с адаптером. Это закрывает Pitfall 7: для `--repo /opt/assistant-core` зелёный итог теперь означает зелёный собственный гейт assistant-core.

## Коммит

- `6b3b2ac` — `fix(cross-ai): adapter runs the target repository gate (GATE-05)`: ровно три файла (`scripts/agy_cross_ai.sh`, `backend/tests/test_agy_cross_ai.py`, `.claude/skills/agy-delegate/SKILL.md`), +93/-9 строк. Коммит один, хук pre-commit (security_shield) прошёл, `--no-verify` не использовался.

## Что сделано

- **Адаптер.** Блок `# ---------- gate ----------` стал трёхветочным if/elif/else с переменной `GATE_DIR`; фоновая подоболочка делает `cd "$GATE_DIR"`. В stderr пишется строка «гейт качества: <команда> (каталог <dir>)», так в журнале GSD видно, какой гейт проверял патч. Шапка описывает порядок выбора и почему гейту целевого репозитория можно доверять (`scripts/gate.py` входит в PROTECTED, патч на него отклоняется кодом 12). Текст SUMMARY адаптера: «Гейт качества целевого репозитория завершился с кодом 0. Журнал: ...».
- **Тесты (RED -> GREEN).** Добавлены `PY_GATE_STUB`, хелпер `adapter_copy`, параметр `adapter` у `run_adapter` и два теста: `test_target_repo_gate_runs_from_repo_root` и `test_fallback_to_adapter_gate_when_repo_has_none`. До правки адаптера первый тест падал (в журнале был гейт копии, не гейт репозитория), второй проходил (прежнее поведение); после правки оба зелёные. Тела 16 прежних тестов не менялись.
- **SKILL agy-delegate.** Три места про гейт описывают гейт целевого репозитория с откатом на гейт chat-app (3 строки изменены). Список защищённых путей, ограничение «chat-app или assistant-core» и строка про откат (15 / 143) сохранены.

## Не тронуто

`scripts/gate.py` chat-app (D-15; `git diff` пуст), heredoc `helper.py` с PROTECTED (побайтно равен HEAD 279dc5a), коды 10/12/15/16, отсутствие автокоммита, новых зависимостей нет.

## Проверка

| Проверка | Результат |
|---|---|
| `pytest backend/tests/test_agy_cross_ai.py -q` | `18 passed in 40.28s` |
| `pytest backend/tests -q` | `251 passed, 3 warnings in 35.45s` (без skip/xfail/deselected) |
| `python3 scripts/gate.py` | `ИТОГ: ЗЕЛЁНЫЙ` (код 0, повторный прогон; см. ниже) |
| verify задачи 3 | пройден: один коммит, три файла, gate.py и helper.py не изменены, дерево вне `.planning/` чистое |

## Отклонения от плана

**Нестабильный тест вне объёма плана.** Первый прогон общего гейта дал «ИТОГ: КРАСНЫЙ» из-за одного теста: `backend.tests.test_concurrent_write::test_concurrent_write_two_processes` (1 failed, 250 passed в chat-app). К трём файлам плана тест не относится. По отдельности он прошёл 3 раза из 3, а полный `backend/tests` до гейта был зелёным (251 passed). Повторный полный прогон гейта без правок дал «ИТОГ: ЗЕЛЁНЫЙ», код 0, поэтому коммит сделан. Вероятная причина: стресс-тест конкурентной записи двух процессов (SQLite WAL) чувствителен к нагрузке на VPS с 2 ГБ RAM, когда гейт гоняет тяжёлые наборы подряд. Причину по логу первого прогона точно установить нельзя: гейт выводит только имя упавшего теста. Журнал первого прогона: `/tmp/claude-0/-opt-assistant-core/00d1d81b-fbeb-4b94-b8ea-398f8ebb93ec/scratchpad/gate_run1.log`. Ни гейт, ни тесты ради зелёного итога не менялись. Рекомендация: отдельная мини-задача на стабилизацию этого теста (запас по `busy_timeout`/повтору), если сбой повторится.

Других отклонений нет: план выполнен как написан.

## Заметка для плана 01-09 assistant-core

Переключение `cross_ai_command` и пробный прогон с `--repo /opt/assistant-core` выполняются в плане 01-09 assistant-core. Этот план их не делал. Адаптер уже готов: при наличии `/opt/assistant-core/scripts/gate.py` он запустит именно его из корня assistant-core.

## Known Stubs

Нет.

## Threat Flags

Нет новой поверхности атаки. Угроза T-uo4-01 закрыта прежним PROTECTED (`scripts/gate.py` отклоняется кодом 12 до применения патча), T-uo4-04 закрыта запуском копии адаптера с заглушкой.

## Self-Check: PASSED

- Файлы на месте: `scripts/agy_cross_ai.sh`, `backend/tests/test_agy_cross_ai.py`, `.claude/skills/agy-delegate/SKILL.md`.
- Коммит `6b3b2ac` является предком HEAD и единственным после базы `279dc5a`.
