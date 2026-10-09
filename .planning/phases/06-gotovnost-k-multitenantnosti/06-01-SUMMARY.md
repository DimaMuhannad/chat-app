---
phase: "06"
plan: "01"
requirements-completed: [ISO-01]
key-files:
  modified:
    - /opt/assistant-core/src/brain/key_rotator.py
    - /opt/assistant-core/src/persona/models.py
    - /opt/assistant-core/tests/test_key_rotator.py
backfilled: 2026-10-09
---

# Summary: Plan 06-01 — Изоляция пулов API-ключей Gemini через ContextVar и фабрику персон

## Status: COMPLETE
- **Requirements Covered:** ISO-01
- **Commits:**
  - `806eef4` (`assistant-core`): `feat(06-01): isolate gemini key rotator per persona and context`

> Отчёт восстановлен 2026-10-09 по коммиту при закрытии цикла v2.0: план был выполнен 2026-10-04, но SUMMARY не был записан.

## What Changed:
- `src/brain/key_rotator.py`: ротатор ключей больше не мутирует глобальный `config.GEMINI_API_KEY`; добавлены `ContextVar` `_current_rotator`, фабрика `get_key_rotator(persona_id)` с кэшем по персоне и прокси `_KeyRotatorProxy` для обратной совместимости модульного объекта.
- `src/persona/models.py`: в `PersonaConfig` добавлено поле для пула ключей персоны.

## Tests:
- `tests/test_key_rotator.py`: `test_key_rotator_no_global_config_mutation`, `test_key_rotator_default_env_path_is_none`, `test_key_rotator_persona_isolation`.
