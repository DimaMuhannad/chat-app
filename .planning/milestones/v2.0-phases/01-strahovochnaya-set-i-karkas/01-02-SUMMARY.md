---
phase: 01-strahovochnaya-set-i-karkas
plan: 02
subsystem: testing
tags: [import-linter, grimp, architecture-contract, namespace-packages, quality-gate]

requires:
  - phase: 01-strahovochnaya-set-i-karkas
    provides: "scripts/gate.py (run_cmd, CheckResult), import-linter 2.15 and grimp 3.17 in both venvs, docs/BASELINE.md"
provides:
  - "assistant-core .importlinter: brain-no-adapters and bot-handler-no-adapters contracts (2 kept, 0 broken), 5 ignore_imports entries as shrinking debt"
  - "chat-app .importlinter: app-no-assistant-core contract (1 kept, 0 broken), no ignore_imports"
  - "test_architecture_contract.py in both repos (5 tests: synthetic fail/pass, graph guard, debt cap, injected violation on a copy of the real package)"
  - "scripts/gate.py run_lint_imports_step: an 'import-linter' row per repository"
  - "docs/BASELINE.md section 'Архитектурный контракт и долг'"
affects: [01-03, 01-04, phase-2]

plan_head_before: d70b690aee1a189ac8e978e0ea4e12f2c2092a54
plan_head_after: 7e0f7144ce110799e8fa58884b92bc30e92d35ee

actuals:
  tokens: 6900
  tasks: 2
  commits: 2   # chat-app, measured d70b690..HEAD; plus 1 commit in assistant-core (98ea591..8add0c3), 3 code commits total

tech-stack:
  added: []
  patterns:
    - "import-linter forbidden contract with namespace-package portions in root_packages"
    - "ignore_imports as an explicit debt list, one full-line comment per entry, capped by a test"
    - "contract proven to fail via a copy of the real package with an injected forbidden import"

key-files:
  created:
    - /opt/assistant-core/.importlinter
    - /opt/assistant-core/tests/test_architecture_contract.py
    - .importlinter
    - backend/tests/test_architecture_contract.py
  modified:
    - /opt/assistant-core/.gitignore
    - .gitignore
    - scripts/gate.py
    - backend/tests/test_gate.py
    - docs/BASELINE.md

key-decisions:
  - "root_packages lists namespace portions (src, src.connectors, src.sender; app, app.core) instead of adding __init__.py: production tree unchanged, silent-empty-contract trap closed by a graph guard test"
  - "allow_indirect_imports = True: only direct imports count, so Phase 2 does not need a live_ticker refactor"
  - "live_ticker -> connectors violation is only recorded in BASELINE, decision deferred to Phase 2 (Open Question 3)"
  - "Owner decision reused: local commits straight to main of /opt/assistant-core for all of Phase 1, no push, no config created there"

requirements-completed: [FND-02, FND-04]

coverage:
  - id: D1
    description: "assistant-core contract: use-cases (brain) and bot_handler do not import adapters; 5 known violations listed in ignore_imports"
    requirement: "FND-02"
    verification:
      - kind: other
        ref: "cd /opt/assistant-core && .venv/bin/lint-imports --no-logo --no-cache -> 2 kept, 0 broken"
        status: pass
      - kind: unit
        ref: "/opt/assistant-core/tests/test_architecture_contract.py (5 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "chat-app contract: backend app does not import src (assistant-core)"
    requirement: "FND-02"
    verification:
      - kind: other
        ref: "PYTHONPATH=backend backend/.venv/bin/lint-imports --no-logo --no-cache -> 1 kept, 0 broken"
        status: pass
      - kind: unit
        ref: "backend/tests/test_architecture_contract.py (5 tests, MAX_IGNORED_IMPORTS = 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Contract provably fails on a deliberate violation and cannot be empty (injected import on a copy of the real package, graph guard, debt cap)"
    requirement: "FND-02"
    verification:
      - kind: unit
        ref: "test_real_contract_fails_on_injected_violation, test_real_contract_modules_exist_in_graph, test_ignore_imports_debt_only_shrinks (both repos)"
        status: pass
    human_judgment: true
    rationale: "FND-02 edge-probe was left unresolved at planning: the planner's reading of 'adapters' and 'provably fails' needs a human check at verification"
  - id: D4
    description: "Gate prints an 'import-linter' row for each repository and ends with the green verdict"
    requirement: "FND-04"
    verification:
      - kind: other
        ref: "python3 scripts/gate.py -> two import-linter rows, ITOG green, rc 0 (45 + 132 tests, live DB hash unchanged)"
        status: pass
      - kind: unit
        ref: "backend/tests/test_gate.py::test_lint_imports_step_missing_binary_is_red_without_exception"
        status: pass
    human_judgment: false

duration: ~10min
completed: 2026-10-02
status: complete
---

# Phase 1 Plan 2: Architecture contract (import-linter) Summary

**Namespace-aware import-linter contracts in both repos (assistant-core 2 kept / 5 debt entries, chat-app 1 kept / 0 debt) with tests that prove they fail on a deliberate violation, cannot be empty and cap the debt, wired into the gate as one row per repository.**

## Performance

- **Duration:** about 10 min
- **Started:** 2026-10-02T05:04:15Z
- **Completed:** 2026-10-02T05:09Z
- **Tasks:** 2 of 2 (Task 1 tracer, Task 2 auto)
- **Files:** 4 created, 5 modified (3 of them in /opt/assistant-core)

## Accomplishments

- assistant-core: `.importlinter` with two `forbidden` contracts (`src.brain`; `src.notifier.bot_handler`), `root_packages = src, src.connectors, src.sender`. Result: 45 files analyzed, 2 kept, 0 broken. Exactly 5 `ignore_imports` entries, each with its own full-line "долг, только убывает" comment (file:lines, inline/top-level, removed by Phase 2 PRT-04).
- chat-app: `.importlinter` (`app` must not import `src`, `root_packages = app, app.core`, external package check on), run as `PYTHONPATH=backend lint-imports`: 1 kept, 0 broken, no ignored imports.
- Five tests per repo with identical names: synthetic violation fails (rc != 0, BROKEN), clean synthetic package passes, graph guard (every contract module is in the grimp graph), debt cap (`MAX_IGNORED_IMPORTS` 5 / 0), and a copy of the real package with an injected forbidden import makes the REAL config go BROKEN naming `src.brain._injected_violation` / `app._injected_violation`.
- Gate: `run_lint_imports_step` (+ `LINT_TIMEOUT_S`, safe wrapper); output now has two "import-linter" rows. Final gate run: chat-app 45 passed, assistant-core 132 passed, both import-linter rows green, live DB unchanged, ITOG green, rc 0.
- `docs/BASELINE.md`: new section "Архитектурный контракт и долг" (contracts, debt table of five entries, `live_ticker` violation outside the contract, why `allow_indirect_imports = True`, why namespace portions instead of `__init__.py`).

## Task Commits

1. **Task 1 (tracer): assistant-core contract end to end** - `8add0c3` (feat, assistant-core/main: `.importlinter`, `tests/test_architecture_contract.py`, `.gitignore`) and `6a3c3fa` (feat, chat-app/master: `scripts/gate.py`, `docs/BASELINE.md`)
2. **Task 2: chat-app contract, tests, gate row** - `7e0f714` (feat, chat-app/master)

Tracer feedback gate: Task 1 `<verify>` (lint-imports "2 kept, 0 broken", 5 passed, gate green with the import-linter row, src untouched) re-run end to end before expansion; it passed, so Task 2 started.

**Plan metadata:** the docs(01-02) close-out commit follows this file.

## Files Created/Modified

- `/opt/assistant-core/.importlinter` - two contracts, namespace portions, 5-entry debt list
- `/opt/assistant-core/tests/test_architecture_contract.py` - five contract tests (`MAX_IGNORED_IMPORTS = 5`)
- `/opt/assistant-core/.gitignore` - `.import_linter_cache/`, `.grimp_cache/`
- `.importlinter` - chat-app contract
- `backend/tests/test_architecture_contract.py` - five contract tests (`MAX_IGNORED_IMPORTS = 0`)
- `.gitignore` - cache directories
- `scripts/gate.py` - `LINT_TIMEOUT_S`, `run_lint_imports_step`, `_safe_lint_step`, two calls in `_run_all`
- `backend/tests/test_gate.py` - missing lint-imports binary is red without an exception
- `docs/BASELINE.md` - contract and debt section

## Decisions Made

- Namespace portions in `root_packages` instead of empty `__init__.py` files (production tree untouched, as the plan requires).
- `allow_indirect_imports = True`; only direct imports are counted.
- `src.notifier.live_ticker -> src.connectors.aadhk.parser` (line 115, inline) is only recorded in BASELINE; whether to widen the contract is a Phase 2 decision.
- **Owner decision (assistant-core branch protection), applied again:** the owner explicitly answered «Коммиты в main для всей Фазы 1» via AskUserQuestion. The protected-branch check in `/opt/assistant-core` returns true only because that repo has no `.planning/config.json`; the halt is treated as satisfied by that decision. One local commit (`8add0c3`) went to `main` there; nothing was pushed, no `.planning/` or config was created or edited in `/opt/assistant-core`, and `/opt/chat-app/.planning/config.json` is unchanged.

## Deviations from Plan

### Minor additions

**1. [Scope note] chat-app subsection added to BASELINE in Task 2**
- **Found during:** Task 2
- **Issue:** The plan's Task 2 file list does not name `docs/BASELINE.md`, but the section written in Task 1 described only assistant-core, while the section's first paragraph and the plan's frontmatter promise both repos.
- **Fix:** Added a short "chat-app" subsection (contract, launch with `PYTHONPATH=backend`, result 1 kept, debt cap 0) and committed it with Task 2.
- **Files modified:** docs/BASELINE.md
- **Committed in:** 7e0f714

---

**Total deviations:** 0 auto-fixed, 1 documentation addition. 
**Impact on plan:** None on behavior; BASELINE now matches the frontmatter promise. No production code touched.

## Issues Encountered

- During Task 1 an `Edit` of BASELINE.md briefly dropped the "## Правила" heading (replacement string ended before it); caught immediately and restored before any commit.
- The `tests/` copy of the real package for the injected-violation test runs lint-imports with `PYTHONPATH` set to the temp directory; confirmed it does not leave cache directories in either repo (`git status` clean of caches).

## Known Stubs

None.

## Threat Flags

None. Threat model mitigations as planned: T-01-07 (namespace portions, graph guard, injected-violation test on the real config), T-01-08 (debt cap test, stale entry is a native lint-imports error), T-01-09 (shield `check_file_content`: 0 violations on all new and changed files; gate's chat-app pytest includes `test_security_audit_all` and is green), T-01-10 (subprocesses use `sys.executable`-relative path, argument list, 120 s timeout, inputs only synthetic or tmp copies), T-01-SC (no installs in this plan).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Gate now covers pytest, import-linter and DB-hash control for both repos; plan 01-03 (synthetic persona) and 01-04 (shield step, drift check, rules) can build on it.
- Phase 2 (PRT-04) must delete the five `ignore_imports` entries together with the refactoring and lower `MAX_IGNORED_IMPORTS` to 0.
- Services untouched (chat-app inactive, assistant-worker failed as before). Live `assistant.db` SHA-256 still `baef14f7`. Production code unchanged: `git status`/`git log` on `src/` (assistant-core, since 6e0850b) and `backend/app` (chat-app, since 7925190) are empty.
- FND-02 interpretation flag (what counts as an "adapter", what "provably fails" means, "can only shrink" = test cap plus native stale-entry error) is left for verification.

## Self-Check: PASSED

- Files exist: /opt/assistant-core/.importlinter, /opt/assistant-core/tests/test_architecture_contract.py, .importlinter, backend/tests/test_architecture_contract.py, scripts/gate.py, docs/BASELINE.md.
- Commits exist: 8add0c3 (assistant-core), 6a3c3fa and 7e0f714 (chat-app).
- Plan verification re-run: lint-imports 2 kept / 1 kept; 5 passed in each architecture test file; gate green with two import-linter rows; shield check 0 violations; no cache directories in `git status`.

---
*Phase: 01-strahovochnaya-set-i-karkas*
*Completed: 2026-10-02*
