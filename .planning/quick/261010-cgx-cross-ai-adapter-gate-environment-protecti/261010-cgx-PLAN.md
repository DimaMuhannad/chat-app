---
phase: quick-261010-cgx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/agy_cross_ai.sh
  - backend/tests/test_agy_cross_ai.py
  - .claude/skills/agy-delegate/SKILL.md
  - backend/tests/test_security_shared.py
autonomous: true
requirements: []
---

# Quick 261010-cgx: cross-AI adapter protects gate environment, labels fallback gate, refuses symlinked gate path

Источник: `/opt/assistant-core/.planning/phases/02-bezopasnost-privatnost-i-nahodki-revyu/02-CHATAPP-CROSSAI-QUICK-BRIEF.md`
(план 02-09 assistant-core, решение D-17, находки WR-05, WR-06, остаточный риск T-uo4-02). Правку chat-app допускает только эта малая задача.
Владелец разрешил (опрос, 2026-10-10): сделать правку сейчас и в той же задаче заменить личный аккаунт в
`test_normalize_remote_formats` на синтетические значения example.org.

## Задачи

1. `scripts/agy_cross_ai.sh`: восемь новых записей `PROTECTED`, защита каталогов-предков, `GATE_KIND`, предупреждение для
   `adapter-fallback`, код 17 (до агента и перед гейтом), обновлённая шапка.
2. `backend/tests/test_agy_cross_ai.py`: тесты на заглушках (отказ 12 для каждого нового пути, ссылка `scripts` в патче,
   код 17 до агента, код 17 с откатом перед гейтом, предупреждение `adapter-fallback`).
3. `.claude/skills/agy-delegate/SKILL.md`: защищённые пути, виды гейта, код 17.
4. `backend/tests/test_security_shared.py`: `test_normalize_remote_formats` на значениях example.org.

## Ограничения

`scripts/gate.py` не менять; прежние защиты не ослаблять; без новых зависимостей, skip и xfail; сервис не перезапускать.
