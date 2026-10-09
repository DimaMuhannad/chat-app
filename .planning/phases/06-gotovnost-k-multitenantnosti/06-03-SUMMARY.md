---
phase: "06"
plan: "03"
requirements: [ISO-03]
key-files:
  created:
    - /opt/chat-app/backend/tests/test_credentials_isolation.py
  modified:
    - /opt/assistant-core/src/core/exceptions.py
    - /opt/assistant-core/src/core/ports/connectors.py
    - /opt/assistant-core/src/connectors/guap_lms/client.py
    - /opt/assistant-core/src/composition.py
    - /opt/assistant-core/tests/test_ports_conformance.py
backfilled: 2026-10-09
---

# Summary: Plan 06-03 — Zero-Trust Scopes для коннекторов ядра и изоляция учётных данных LMS

## Status: COMPLETE
- **Requirements Covered:** ISO-03
- **Commits:**
  - `9d713c9` (`assistant-core`): `feat(06-03): declare required_scopes on ports and enforce zero-trust in composition`
  - `d90e607` (`chat-app`): `test(06-03): add credentials isolation test in chat-app`

> Отчёт восстановлен 2026-10-09 по коммитам при закрытии цикла v2.0: план был выполнен 2026-10-04, но SUMMARY не был записан.

## What Changed:
- `src/core/ports/connectors.py`: порты объявляют `required_scopes` (timesheet, schedule, calendar, LMS).
- `src/connectors/guap_lms/client.py`: клиент LMS объявляет `required_scopes`.
- `src/core/exceptions.py`: `MissingScopeError(PermissionError)`.
- `src/composition.py`: фабрики коннекторов сверяют scopes привязки персоны с требуемыми и бросают `MissingScopeError`; при отсутствии привязки роли возвращают `None`.
- Отклонение от плана: `src/connectors/aadhk/provider.py` не менялся (scopes проверяются в composition).

## Tests:
- `tests/test_ports_conformance.py`: `test_connectors_declare_required_scopes`, `test_composition_missing_scope_error`, `test_composition_unbound_role_returns_none`.
- chat-app `backend/tests/test_credentials_isolation.py`: изоляция учётных данных.
