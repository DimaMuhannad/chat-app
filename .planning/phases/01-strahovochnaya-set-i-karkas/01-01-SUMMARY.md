---
phase: 01-strahovochnaya-set-i-karkas
plan: 01
subsystem: testing
tags: [quality-gate, pytest, sqlite, baseline, import-linter, grimp]

requires: []
provides:
  - "scripts/gate.py: one-command local gate (both pytest suites, chat-app on a DB copy, SHA-256 control of the live DB, Russian table, ITOG line)"
  - "docs/baseline/*.txt: raw pytest -v start snapshots of both repos"
  - "docs/BASELINE.md: start state, environment, DB protection, rules"
  - "import-linter 2.15 and grimp 3.17 in both venvs, declared in requirements-dev.txt of both repos"
affects: [01-02, 01-03, 01-04, phase-2, phase-4]

plan_head_before: 11b0c5ebb9697f525fa37202a2871f1e4a7f6732
plan_head_after: 67291a8d3b0faba5ee09e513cecfb5ad1b29ab67

actuals:
  tokens: 11200
  tasks: 3
  commits: 3   # chat-app, measured 11b0c5e..HEAD; plus 1 commit in assistant-core (6e0850b..98ea591), 4 code commits total

tech-stack:
  added: [import-linter 2.15, grimp 3.17, rich 15.0.0 (transitive), markdown-it-py 4.2.0 (transitive), mdurl 0.1.2 (transitive)]
  patterns: ["stdlib-only gate script with pure, unit-tested functions", "DB copy via sqlite3 backup from mode=ro URI", "SHA-256 before/after control of the live DB"]

key-files:
  created:
    - scripts/gate.py
    - backend/tests/test_gate.py
    - docs/baseline/pytest-chat-app.txt
    - docs/baseline/pytest-assistant-core.txt
    - docs/BASELINE.md
    - requirements-dev.txt
    - /opt/assistant-core/requirements-dev.txt
  modified: []

key-decisions:
  - "Gate does not override the DB URL for assistant-core (load_dotenv override=True defeats it); protection for both repos is the SHA-256 control, chat-app additionally gets SQLITE_DB_PATH on a copy"
  - "Start snapshot taken by the gate itself (--save-pytest-output) so the chat-app run on a DB copy is guaranteed by construction"
  - "Owner decision: local commits directly on main of /opt/assistant-core for all of Phase 1, no push"

requirements-completed: [FND-01, FND-04]

coverage:
  - id: D1
    description: "scripts/gate.py: one command gives a green/red verdict for both repos, chat-app tests run on a DB copy, live DB hash is checked"
    requirement: "FND-04"
    verification:
      - kind: unit
        ref: "backend/tests/test_gate.py (25 tests of the pure functions)"
        status: pass
      - kind: other
        ref: "python3 scripts/gate.py -> ITOG: ZELENYJ, rc 0 (39 + 127 tests, live DB hash unchanged)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Start-of-phase baseline of both repos captured as raw pytest output (14 and 127 passed) and described in docs/BASELINE.md"
    requirement: "FND-01"
    verification:
      - kind: other
        ref: "grep checks of docs/baseline/*.txt headers and summary lines; BASELINE section/hash checks; shield check_file_content = 0 violations"
        status: pass
    human_judgment: true
    rationale: "FND-01 edge-probe was left unresolved at planning (meaning of 'status of each' and 'on start'); the planner's interpretation needs a human check at verification"
  - id: D3
    description: "import-linter 2.15 and grimp 3.17 installed in both venvs only after explicit owner approval; dev requirements declared in both repos"
    requirement: "FND-04"
    verification:
      - kind: other
        ref: "importlib.metadata in both venvs -> ('2.15', '3.17'); lint-imports present in both venvs"
        status: pass
    human_judgment: false

duration: ~30min (approximate; plan ran across four executor sessions with two owner checkpoints)
completed: 2026-10-02
status: complete
---

# Phase 1 Plan 1: Quality gate and start baseline Summary

**Stdlib-only `python3 scripts/gate.py` runs both pytest suites (chat-app on a sqlite3-backup copy of the live DB), hash-controls the live `assistant.db`, and prints a Russian table ending in ITOG: ZELENYJ/KRASNYJ; start baseline (14 + 127 passed) captured, import-linter 2.15 / grimp 3.17 installed after owner approval.**

(Final verdict strings in the tool output are the Russian «ИТОГ: ЗЕЛЁНЫЙ» / «ИТОГ: КРАСНЫЙ».)

## Performance

- **Duration:** about 30 min (approximate, four executor sessions)
- **Completed:** 2026-10-02
- **Tasks:** 3 of 3 (Task 1 tracer, Task 2 package-legitimacy checkpoint, Task 3)
- **Files:** 7 created, 0 modified (one of them in /opt/assistant-core)

## Accomplishments

- Gate: 346-line stdlib-only `scripts/gate.py`, 25 unit tests of its pure functions. Current result: chat-app 39 passed, assistant-core 127 passed, live DB unchanged, ITOG: ZELENYJ, rc 0. With `ASSISTANT_CORE_DIR=/nonexistent` the gate returns rc 1 and ITOG: KRASNYJ without a traceback (verified in Task 1).
- Start baseline (before any new phase tests): chat-app 14 passed (2.80 s, HEAD 11b0c5e), assistant-core 127 passed with 31 warnings (26.62 s, HEAD 6e0850b); no failed/skipped/xfail/deselected. Raw output in `docs/baseline/`.
- import-linter 2.15 and grimp 3.17 installed in both venvs (only these plus transitive rich, markdown-it-py, mdurl; the pip dry run confirmed no existing package would change); `lint-imports` exists in both venvs; `requirements-dev.txt` in both repos.
- `docs/BASELINE.md` (Russian) with all nine required sections, full SHA-256 of the live DB (`baef14f7...9393`), override=True explanation, rules.

## Task Commits

1. **Task 1 (tracer): gate** - `46b3bc1` (feat), baseline snapshot `18be780` (docs), chat-app/master
2. **Task 2: package legitimacy checkpoint** - no commit; owner answered "Одобрено" (via AskUserQuestion) for exactly `import-linter==2.15` and `grimp==3.17`
3. **Task 3: requirements-dev, install, BASELINE** - `98ea591` (chore, assistant-core/main: `requirements-dev.txt`) and `67291a8` (docs, chat-app/master: `requirements-dev.txt`, `docs/BASELINE.md`)

**Plan metadata:** the docs(01-01) close-out commit follows this file.

## Files Created/Modified

- `scripts/gate.py` - gate (DB copy, SHA-256 control, pytest steps, report)
- `backend/tests/test_gate.py` - unit tests of gate pure functions (no main(), no subprocess)
- `docs/baseline/pytest-chat-app.txt`, `docs/baseline/pytest-assistant-core.txt` - raw start snapshots with Command/Commit/Date headers
- `docs/BASELINE.md` - baseline document
- `requirements-dev.txt` (chat-app) and `/opt/assistant-core/requirements-dev.txt` - dev dependencies

## Decisions Made

- No DB URL override for assistant-core (research found `load_dotenv(override=True)`); SHA-256 control protects both repos (documented deviation D-03 in the plan).
- Gate built first and used to take the baseline (tracer-first), so the DB-copy run is structural rather than manual.
- Package approval evidence (Task 2): `import_linter-2.15` wheel SHA-256 `9aaf16a88ac1e99d5a464cd7f66b6a05f7060bfa761162e0ed441773a267ed3b`; `grimp-3.17` cp312 manylinux wheel SHA-256 `ecf26d99a35ab7b5966af56118bb9344d1fd1b972d3c45dd5012effc7a68c844`. Observation: the grimp METADATA points to `github.com/python-grimp/grimp` (an organization), not the author's personal account; same author David Seddon. The owner was informed and approved.
- **Owner decision (assistant-core branch protection):** the owner explicitly answered «Коммиты в main для всей Фазы 1» via AskUserQuestion. Local commits directly on `main` of `/opt/assistant-core` are allowed for all of Phase 1 (the protected-branch check there returns true only because that repo has no `.planning/config.json`). Nothing is pushed; no `.planning/` or config was created in `/opt/assistant-core`; `/opt/chat-app/.planning/config.json` is unchanged. Only one commit was made there in this plan (`98ea591`).

## Deviations from Plan

None - plan executed exactly as written (the plan's own "Отклонения от CONTEXT.md" section, D-03/D-04/order, was followed as stated).

## Issues Encountered

- Branch protection halt in `/opt/assistant-core` before Task 3 (protected-branch check true because the repo has no planning config); resolved by the owner decision above, not by changing any config.
- `pytest-asyncio` is not installed in the chat-app venv (only anyio); BASELINE records this accurately.

## Known Stubs

None.

## Threat Flags

None. Mitigations implemented as planned: T-01-01/02 (read-only backup copy, removal in finally, SHA-256 before/after; live hash still `baef14f7`), T-01-03 (list args, no shell), T-01-04 (shield `check_file_content`: 0 violations on BASELINE and both requirements-dev files), T-01-05 (`--basetemp` inside the gate temp dir), T-01-06 (0 collected / skipped / xfail / deselected are red), T-01-SC (blocking-human checkpoint, exact `==` versions, metadata check after install).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Gate and baseline are ready to guard plans 01-02..01-04; import-linter and grimp are available for the architecture-contract plan.
- Services untouched: chat-app inactive, assistant-worker failed (pre-existing), dev-bridge inactive. Live `assistant.db` SHA-256 unchanged (`baef14f7`).
- FND-01 interpretation flag (status of each = per-test status in raw output plus per-file summary; "on start" = before the first Phase 1 commit; "copy" = sqlite3 backup) is left for verification.

## Self-Check: PASSED

- Files exist: scripts/gate.py, backend/tests/test_gate.py, docs/baseline/*.txt, docs/BASELINE.md, both requirements-dev.txt.
- Commits exist: 46b3bc1, 18be780, 67291a8 (chat-app); 98ea591 (assistant-core).
- Plan verification re-run: gate green rc 0; both venvs report ('2.15', '3.17'); BASELINE section/hash checks pass; shield check 0 violations; live DB hash unchanged.

---
*Phase: 01-strahovochnaya-set-i-karkas*
*Completed: 2026-10-02*
