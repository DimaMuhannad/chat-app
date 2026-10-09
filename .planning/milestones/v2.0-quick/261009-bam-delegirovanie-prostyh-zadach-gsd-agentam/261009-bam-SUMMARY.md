---
phase: 261009-bam
plan: 01
subsystem: agy-delegation
tags: [gsd, cross-ai, antigravity, jail, quality-gate]
requires: []
provides:
  - scripts/agy_cross_ai.sh (адаптер workflow.cross_ai_command)
  - AGY_RESULT-контракт и коды возврата в scripts/agy_task.sh
  - правило маршрутизации GSD -> agy в навыке agy-delegate и CLAUDE.md
affects: [scripts/agy_task.sh, .planning/config.json, .claude/skills/agy-delegate/SKILL.md, CLAUDE.md]
tech-stack:
  added: []
  patterns: [sentinel-проверки результата недоверенного агента, откат патча через git apply -R]
key-files:
  created:
    - scripts/agy_cross_ai.sh
    - backend/tests/test_agy_cross_ai.py
  modified:
    - scripts/agy_task.sh
    - .planning/config.json
    - .claude/skills/agy-delegate/SKILL.md
    - CLAUDE.md
    - .planning/subagents/GSD_PHASE_AGENT_TRAINING_AND_PROMPT.md
  deleted:
    - .agents/agents/gsd-phase-agent/agent.md
    - .agents/agents/gsd-plan-executor/agent.md
decisions:
  - "Патч агента применяется только в рабочее дерево (git apply + git add -N), коммит делает Claude"
  - "Результат agy не доверяется: сентинелы 10-14, гейт, автооткат"
  - "Планирование и исследование остаются за Claude; удалены два профиля, несовместимых с jail"
metrics:
  duration: ~35 мин (включая 4м46с на полный гейт)
  completed: 2026-10-09
status: complete
commits: 3
plan_head_before: 74251f9e064603f32c3edde8634f99da566716c7
plan_head_after: c6ac2a41bf159d876b12a73753d77019214f7263
actuals:
  tokens: 60000
  tasks: 3
  commits: 3
---

# Quick 261009-bam: делегирование простых задач GSD агентам Antigravity

**Механические планы GSD с `cross_ai: true` теперь исполняет агент agy через `scripts/agy_cross_ai.sh` (jail, сентинелы, гейт, автооткат), правки остаются незакоммиченными для ревью Claude.**

## Что сделано

**Task 1 (tracer), коммит 2c5fc79.**
- `scripts/agy_task.sh`: последняя строка stdout `AGY_RESULT job=… status=… changed=… patch=… rc=… model=… input_tokens=… output_tokens=…`; коды 0/1/3/4/5/6; отказ по секретам в тексте задачи (код 4); NDA-отказы теперь код 3; блок «Коды возврата» в usage. Весь прежний русский вывод сохранён.
- `scripts/agy_cross_ai.sh` (режим 100755): stdin-промпт -> `agy_task.sh run --mode edit --agent gsd-executor` -> разбор только последней строки `AGY_RESULT` -> применение патча в рабочее дерево -> гейт -> SUMMARY (frontmatter `status: complete`, предупреждение «UNCOMMITTED», команды для Claude) на stdout.
- `.planning/config.json`: `workflow.cross_ai_execution=true` (bool), `cross_ai_command="scripts/agy_cross_ai.sh"`, `cross_ai_timeout=900` (число); прежние ключи сохранены.
- `backend/tests/test_agy_cross_ai.py`: сквозной тест с заглушками systemd-run (PATH-shim), agy (AGY_BIN) и гейта (AGY_GATE_CMD).

**Task 2 (sentinels), коммит c2116cd.** Отказ на грязном дереве вне `.planning/` (10); защищённые пути (12); покрытие путей из элементов `files` (13); `git apply --check` (14); красный гейт -> откат (15); сбой отката (16); SIGTERM/INT/HUP -> откат и код 143. Тестов всего 16 (13 сценариев отказов, прямой тест `AGY_RESULT`, трейсер и др.), пропусков нет.

**Task 3 (routing), коммит c6ac2a4.** `git rm` профилей `gsd-phase-agent` и `gsd-plan-executor`; обучающий документ помечен «Устарело (2026-10-09)»; навык `agy-delegate` переписан (маршрутизация, cross-AI, таблицы кодов, запреты, надёжность, предложение по settings.json); строка про `cross_ai: true` в CLAUDE.md §3.

## Проверка

- `bash -n` обоих скриптов — ок; `pytest backend/tests/test_agy_cross_ai.py` — 16 passed.
- JSON-типы config.json проверены; `git ls-files -s scripts/agy_cross_ai.sh` -> 100755.
- Финальный гейт `python3 scripts/gate.py`, exit 0 (последние строки):

```
оба             боевая assistant.db не изменена        ✓

ИТОГ: ЗЕЛЁНЫЙ
```
(chat-app: 187 тестов, assistant-core: 421 тест, import-linter и security_shield по обоим репозиториям — все ✓).

## Отклонения от плана

**1. [Rule 1 - Bug] `git apply --intent-to-add` ломает индекс (git 2.43).**
- **Найдено в:** Task 2 (тест красного гейта и SIGTERM показал `D .planning/STATE.md`, `DA app.txt` и т.п. после отката).
- **Проблема:** допущение плана «проверено» неверно: `git apply --intent-to-add` перезаписывает индекс только записями затронутых файлов, остальные записи пропадают.
- **Исправление:** применять обычным `git apply --whitespace=nowarn`, а новые файлы помечать отдельно `git add -N -- <созданные>`; откат — `git apply -R` + `git reset -q -- <созданные>`; `--check` без `--intent-to-add`. Трейсер-тест усилен: проверяет, что `git ls-files` сохраняет все записи и `git status --porcelain` равен ` M app.txt` / ` A new.txt`.
- **Файлы:** scripts/agy_cross_ai.sh, backend/tests/test_agy_cross_ai.py. **Коммит:** c2116cd.

**2. Трейсер-коммит без бага не выпускался отдельно.** Код 2c5fc79 содержит первую версию с `--intent-to-add` (трейсер-тест на ней проходил, так как проверял не полный статус); исправлено следующим коммитом.

Прочее: план выполнен как написан. Аутентификационных гейтов нет. Реальный agy и `agy_task.sh` на настоящих репозиториях не запускались (только заглушки в tmp_path); `~/.gemini`, systemd и сервисы не менялись.

## Коды возврата

**agy_task.sh run:** 0 успех; 1 общая ошибка; 3 NDA/air-gap; 4 секреты (копия или текст задачи); 5 пустой ответ после повтора; 6 статус не SUCCESS при непустом ответе.

**agy_cross_ai.sh:** 0 успех; 2 usage/пустой промпт/не git; 1, 3, 4, 5, 6 из agy_task.sh; 10 грязное дерево вне `.planning/`; 11 нет валидного AGY_RESULT / не SUCCESS / нет правок / нет патча; 12 защищённый путь; 13 объявленный файл не тронут; 14 патч не применяется; 15 гейт красный (патч откачен); 16 откат не удался; 143 SIGTERM/SIGINT/SIGHUP.

## Предложение: узкие права agy (НЕ применено)

Текущий `~/.gemini/antigravity-cli/settings.json` разрешает `command(*)`, `write_file(*)`, `read_file(*)` и доверяет `/opt/chat-app`, `/opt/assistant-core`, `/root/.gemini/antigravity-cli`, `/root`, `/opt`. Предлагаемый фрагмент (применять только после одобрения владельца и пробного запуска через обёртку):

```json
{
  "permissions": { "allow": ["read_file(*)", "write_file(*)"] },
  "trustedWorkspaces": ["/var/tmp/agy-jobs"]
}
```

## Известные заглушки

Нет.

## Threat Flags

Нет новых поверхностей сверх threat_model плана (T-261009bam-01..09 покрыты: защищённые префиксы, разбор только последней AGY_RESULT, сентинелы 11/13, отказ по секретам и NDA, dirty-tree, откат по сигналам, запреты в навыке).

## Self-Check: PASSED

- scripts/agy_cross_ai.sh, backend/tests/test_agy_cross_ai.py, SKILL.md — на месте; профили gsd-phase-agent и gsd-plan-executor отсутствуют.
- Коммиты 2c5fc79, c2116cd, c6ac2a4 — предки HEAD.
