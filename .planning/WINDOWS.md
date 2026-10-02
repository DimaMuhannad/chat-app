---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-10-02T15:36:40.605Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03 | stub |  |  | assistant-core src/persona/seed.py: persona_rows возвращает пустые списки, пространства и привязки заполняет план 03-03 | open |  | 2026-10-02T15:36:40.605Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "03",
    "file": "",
    "line": null,
    "description": "assistant-core src/persona/seed.py: persona_rows возвращает пустые списки, пространства и привязки заполняет план 03-03",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-02T15:36:40.605Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
