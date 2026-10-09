---
phase: 01-strahovochnaya-set-i-karkas
plan: 03
subsystem: testing
tags: [synthetic-persona, pytest-fixture, sha256-drift, quality-gate, white-label]

requires:
  - phase: 01-strahovochnaya-set-i-karkas
    provides: "scripts/gate.py (CheckResult, sha256_file, CHAT_DIR, CORE_DIR), docs/BASELINE.md, import-linter rows"
provides:
  - "SYNTHETIC_PERSONA dict (second fictional persona, three workspaces: public / internal / restricted_nda) in both test suites"
  - "synthetic_persona fixture (deepcopy) in a new conftest.py of each suite"
  - "7 scaffold tests per repo (test_synthetic_persona.py), green now, no skip/xfail"
  - "gate step 'синтетическая персона (дрейф SHA-256)' (persona_drift_check)"
  - "docs/BASELINE.md section 'Ожидают Фазы 3' (8 deferred checks as text only)"
affects: [01-04, phase-3, phase-4]

plan_head_before: 05334f7354fd26a0fab7c6305efd57aefbb07374
plan_head_after: 667c6ea7f0d4278c407bde0c904180ce183d9c5a

actuals:
  tokens: 9000
  tasks: 2
  commits: 2   # chat-app, measured 05334f7..HEAD; plus 1 commit in assistant-core (8add0c3..06792b7), 3 code commits total

tech-stack:
  added: []
  patterns:
    - "two byte-identical test-data copies guarded by a SHA-256 gate step until the shared library of Phase 4"
    - "repo-independent test file: locates scripts/security_shield.py by walking Path(__file__).parents"
    - "reserved-value fictional data (.example hosts, /synthetic/ paths, Telegram ID range 100000000..100000999)"

key-files:
  created:
    - backend/tests/synthetic_persona.py
    - backend/tests/conftest.py
    - backend/tests/test_synthetic_persona.py
    - /opt/assistant-core/tests/synthetic_persona.py
    - /opt/assistant-core/tests/conftest.py
    - /opt/assistant-core/tests/test_synthetic_persona.py
  modified:
    - scripts/gate.py
    - backend/tests/test_gate.py
    - docs/BASELINE.md

key-decisions:
  - "Phase 3 checks (PER-01..PER-09, BCK-02) are listed as text in the module docstring and BASELINE, never as skip/xfail markers"
  - "Real owner Telegram ID is not copied; distinctness is shown by the reserved range 100000000..100000999"
  - "Real NDA keywords are read at test time from scripts/security_shield.py; they are not copied into any file"
  - "Owner decision (assistant-core branch protection): local commits straight to main for all of Phase 1, no push, no .planning/ or config created there; chat-app config unchanged"

requirements-completed: [FND-03, FND-04]

coverage:
  - id: D1
    description: "synthetic_persona fixture and SYNTHETIC_PERSONA exist in both suites; every identifying field is present, non-empty and different from today's hardcode"
    requirement: "FND-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_synthetic_persona.py (7 passed) and /opt/assistant-core/tests/test_synthetic_persona.py (7 passed)"
        status: pass
    human_judgment: true
    rationale: "FND-03 edge-probe was left unresolved at planning: the reading of 'identifying fields' (D-13 list plus short_name, account, remote) and 'differs in all fields' (scalar inequality, empty set intersections, reserved Telegram range) needs a human check at verification"
  - id: D2
    description: "No owner tokens, no real NDA keywords, no e-mail in persona data; exactly three clearance levels; reserved synthetic values"
    requirement: "FND-03"
    verification:
      - kind: unit
        ref: "test_no_owner_tokens, test_no_real_nda_keywords, test_clearances_are_exactly_three_levels, test_reserved_synthetic_values"
        status: pass
      - kind: other
        ref: "scripts/security_shield.py check_file_content on all new and changed files -> нарушений: 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Phase 3 checks are enumerated as text (docstring and BASELINE) without skip/xfail markers"
    requirement: "FND-03"
    verification:
      - kind: other
        ref: "grep PER-01..PER-09 and BCK-02 in synthetic_persona.py and docs/BASELINE.md; grep for pytest.mark.skip/xfail finds nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "Gate compares the two persona copies by SHA-256 and prints a drift row; red on difference or missing file"
    requirement: "FND-04"
    verification:
      - kind: unit
        ref: "backend/tests/test_gate.py::test_persona_drift_check_identical_copies_is_green / _different_copies_is_red / _missing_file_is_red_without_exception"
        status: pass
      - kind: other
        ref: "python3 scripts/gate.py -> row 'синтетическая персона (дрейф SHA-256)' ✓, ИТОГ: ЗЕЛЁНЫЙ, rc 0 (55 + 139 tests, live DB hash unchanged)"
        status: pass
    human_judgment: false

duration: ~6min
completed: 2026-10-02
status: complete
---

# Phase 1 Plan 3: Synthetic persona scaffold Summary

**A second fictional persona (three workspaces, one per clearance level) with a deepcopy fixture and seven green scaffold tests in both repositories, kept identical by a SHA-256 drift row in the quality gate, with the eight Phase 3 checks listed as text only.**

## Performance

- **Duration:** about 6 min
- **Started:** 2026-10-02T05:11:10Z
- **Completed:** 2026-10-02T05:14:36Z (code commits; close-out follows)
- **Tasks:** 2 of 2 (Task 1 tracer, Task 2 auto)
- **Files:** 6 created, 3 modified (3 of the created files are in /opt/assistant-core)

## Accomplishments

- `SYNTHETIC_PERSONA` plain dict (not Pydantic, not YAML; the persona.yaml schema stays with PER-01): fictional name, title, organizations, bot, three workspaces (public, internal, restricted_nda), timesheet project and 6.0 h norm, schedule and LMS `.example` URLs, default area, one subject, one lesson slot. Docstring holds the "Ожидают Фазы 3" list (PER-01..PER-09, BCK-02) and the two-copies rule.
- `synthetic_persona` fixture in a new `conftest.py` per suite (relative import, `copy.deepcopy`, touches neither app nor DB).
- Seven scaffold tests per suite pass now: independent copy, fields present and non-empty, no owner tokens, differs from the hardcode (scalars unequal, set intersections empty, workspace count differs from four), exactly three clearances, reserved values, no real NDA keywords (read from `scripts/security_shield.py` at test time).
- Gate: `persona_drift_check` + `CHAT_PERSONA`/`CORE_PERSONA`, called in `_run_all` before the live-DB hash "after". Three unit tests. Final gate run: chat-app 55 passed, assistant-core 139 passed, both import-linter rows green, drift row green, live DB unchanged, ITOG green, rc 0.
- `docs/BASELINE.md`: new section "Ожидают Фазы 3" with the same eight items as the docstring.

## Task Commits

1. **Task 1 (tracer): persona data, fixture, tests, BASELINE section (chat-app)** - `c154e9a` (feat, chat-app/master)
2. **Task 2: byte-identical copies in assistant-core** - `06792b7` (feat, assistant-core/main); **gate drift step and tests** - `667c6ea` (feat, chat-app/master)

Tracer feedback gate: Task 1 `<verify>` (7 passed, gate green, shield 0 violations, PER/BCK ids present in docstring and BASELINE) was re-run end to end before expansion; it passed.

**Plan metadata:** the docs(01-03) close-out commit follows this file.

## Files Created/Modified

- `backend/tests/synthetic_persona.py`, `/opt/assistant-core/tests/synthetic_persona.py` - persona dict and Phase 3 list in the docstring
- `backend/tests/conftest.py`, `/opt/assistant-core/tests/conftest.py` - `synthetic_persona` fixture
- `backend/tests/test_synthetic_persona.py`, `/opt/assistant-core/tests/test_synthetic_persona.py` - seven scaffold tests
- `scripts/gate.py` - `CHAT_PERSONA`, `CORE_PERSONA`, `persona_drift_check`, module docstring item
- `backend/tests/test_gate.py` - three drift tests
- `docs/BASELINE.md` - section "Ожидают Фазы 3"

## Decisions Made

- Persona stays a plain dict with the fields from D-13 plus `short_name`, `account`, `remote` (planner's discretion); the `persona.yaml` schema is not anticipated.
- Distinctness for the Telegram ID is shown by a reserved range, because the real ID is personal data.
- `OWNER_TOKEN_DENYLIST` is a single constant in the test; PER-08 in Phase 3 replaces it with the default persona's data.
- **Owner decision (assistant-core branch protection), applied again:** the owner explicitly answered «Коммиты в main для всей Фазы 1» via AskUserQuestion. The protected-branch check in `/opt/assistant-core` returns true only because that repo has no `.planning/config.json`; the halt is treated as satisfied by that decision. One local commit (`06792b7`) went to `main` there; nothing was pushed, no `.planning/` or config was created or edited in `/opt/assistant-core`, and `/opt/chat-app/.planning/config.json` is unchanged.

## Deviations from Plan

### Minor additions

**1. [Scope note] Gate module docstring updated**
- **Found during:** Task 2
- **Issue:** the docstring of `scripts/gate.py` lists what the gate does; the new drift step was missing from it.
- **Fix:** added item 5 (persona SHA-256 comparison) and renumbered the following items.
- **Files modified:** scripts/gate.py
- **Committed in:** 667c6ea

---

**Total deviations:** 0 auto-fixed, 1 documentation addition.
**Impact on plan:** None on behavior. No production code touched (`backend/app` since 7925190 and assistant-core `src` since 6e0850b: empty git log).

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. Threat model mitigations as planned: T-01-11 (fictional values only, `test_no_owner_tokens`, `test_reserved_synthetic_values`, no e-mail by grep, real Telegram ID not copied), T-01-12 (NDA keywords read at test time; shield `check_file_content` 0 violations on all new and changed files in both repos), T-01-13 (`persona_drift_check` in the gate, `cmp` at creation), T-01-SC (no installs; `requirements-dev.txt` unchanged).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 01-04 can build on the gate (pytest, import-linter and drift rows are in place).
- Phase 3 connects the persona to real code paths using the eight listed checks; Phase 4 replaces the two copies with a shared library and can then drop the drift row.
- Services untouched (chat-app inactive, assistant-worker failed as before). Live `assistant.db` SHA-256 still `baef14f7`.
- FND-03 interpretation flag (meaning of "identifying fields" and "differs in all fields") is left for verification.

## Self-Check: PASSED

- Files exist: all six new test files in both repos, scripts/gate.py, backend/tests/test_gate.py, docs/BASELINE.md.
- Commits exist: c154e9a and 667c6ea (chat-app), 06792b7 (assistant-core).
- Plan verification re-run: 7 passed in each suite; `cmp` of three file pairs silent; gate green with the drift row; `git -C /opt/assistant-core status --porcelain` empty; production code unchanged.

---
*Phase: 01-strahovochnaya-set-i-karkas*
*Completed: 2026-10-02*
