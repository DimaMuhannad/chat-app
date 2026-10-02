---
phase: 01-strahovochnaya-set-i-karkas
plan: 04
subsystem: testing
tags: [security-shield, quality-gate, baseline, import-linter, owner-decision]

requires:
  - phase: 01-strahovochnaya-set-i-karkas
    provides: "scripts/gate.py (CheckResult, run_cmd, pytest/import-linter/persona/db steps), docs/BASELINE.md, synthetic persona scaffold"
provides:
  - "gate step security_shield (--all) for chat-app and assistant-core with normalised findings and a frozen list of 15 known false positives"
  - "docs/BASELINE.md sections 'Политика security_shield' and 'Итог после Фазы 1'"
  - "one-line gate command in CLAUDE.md (Development Commands)"
  - "final gate: eight rows, ИТОГ: ЗЕЛЁНЫЙ, rc 0"
affects: [phase-2, phase-3, phase-4, all-later-phases]

plan_head_before: e51c7296c9c277c493d96d716397fdc50bbc4517
plan_head_after: 539c55acac24c24b1cd1f9393745ba5b0ffc78d4

actuals:
  tokens: 6000
  tasks: 3
  commits: 3   # MEASURED chat-app e51c729..HEAD; no commits in assistant-core for this plan

tech-stack:
  added: []
  patterns:
    - "shield output is only parsed, never printed: findings reduced to (relative path, kind, count)"
    - "debt lists only shrink: stale entry in KNOWN_SHIELD_FALSE_POSITIVES turns the row red, like ignore_imports"

key-files:
  created: []
  modified:
    - scripts/gate.py
    - backend/tests/test_gate.py
    - docs/BASELINE.md
    - CLAUDE.md

key-decisions:
  - "Owner, 2026-10-02: shield mode b-all-frozen (--all plus frozen list of 15 known false positives); red on new finding, shield failure or stale entry"
  - "Owner: local commits directly on main in /opt/assistant-core allowed for all of Phase 1 (no push, no .planning/ there); this plan needed none"
  - "No code change to gate.py/test_gate.py after the owner choice: the interim variant from Task 1 was the chosen one"

patterns-established:
  - "Finding key = relative path + kind + count, without line numbers or keyword text"
  - "Phase acceptance = full gate green with eight rows + production-code/service/live-DB invariants"

requirements-completed: [FND-04, FND-01]

coverage:
  - id: D1
    description: "Gate runs security_shield --all in both repos, compares findings to the frozen list of 15, and goes red on new finding, failure or stale entry"
    requirement: "FND-04"
    verification:
      - kind: unit
        ref: "backend/tests/test_gate.py (parse_shield_findings / compare_shield_findings tests)"
        status: pass
      - kind: other
        ref: "python3 scripts/gate.py -> two security_shield (--all) rows, rc 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "BASELINE records shield policy with owner decision and date, and the Phase 1 outcome (test counts before/after, eight gate rows, ignore_imports cross-check)"
    requirement: "FND-01"
    verification:
      - kind: other
        ref: "grep -qxF section headings in docs/BASELINE.md; ignore_imports cross-check loop against /opt/assistant-core/.importlinter"
        status: pass
    human_judgment: true
    rationale: "Prose accuracy of the FND-04 interpretation ('итог по каждому репозиторию') requires manual review (edge-probe flag: unclassified)"
  - id: D3
    description: "Exactly one added line with the gate command in CLAUDE.md"
    verification:
      - kind: other
        ref: "git diff --numstat 7925190 -- CLAUDE.md -> 1 0"
        status: pass
    human_judgment: true
    rationale: "CLAUDE.md is an agent instruction file; the owner must review the change"

duration: 8min
completed: 2026-10-02
status: complete
---

# Phase 1 Plan 04: security_shield in the gate, shield policy and Phase 1 close-out Summary

**One command `python3 scripts/gate.py` now runs both pytest suites (68 + 139 tests), both import-linter contracts, `security_shield --all` in both repos against a frozen list of 15 known false positives, the persona drift check and the live-DB hash check, and prints «ИТОГ: ЗЕЛЁНЫЙ» (rc 0)**

## Performance

- **Duration:** about 8 min for the continuation session (Task 1 and the decision checkpoint were done in the earlier session)
- **Started:** 2026-10-02T05:20Z (continuation, approximate)
- **Completed:** 2026-10-02T05:28Z
- **Tasks:** 3 (Task 1 tracer, Task 2 owner decision, Task 3 close-out)
- **Files modified:** 4

## Accomplishments

- Shield step in the gate: only 🚨-finding lines are parsed, reduced to (relative path, kind, count); remote address, author e-mail, keyword text and line numbers are never printed or stored. Verified: the gate output contains no remote/e-mail lines and no e-mail addresses.
- Owner decision on shield mode recorded in BASELINE with the date and its meaning; frozen list of 15 entries tabulated as «path - kind - count».
- BASELINE section «Итог после Фазы 1»: eight-row gate table, test counts before and after (chat-app 14 -> 68, assistant-core 127 -> 139, total 141 -> 207; all 141 starting tests kept), tool versions, invariants, verbatim cross-check of the five `ignore_imports` entries against `/opt/assistant-core/.importlinter` (5 of 5).
- One line added to CLAUDE.md in its own commit.
- Final acceptance: gate green with eight rows; `ASSISTANT_CORE_DIR=/nonexistent` gives rc 1 «ИТОГ: КРАСНЫЙ» (red path intact).

## Task Commits

1. **Task 1 (tracer): security_shield step with frozen false-positive list** - `15a08df` (feat)
2. **Task 2: owner decision on shield mode** - no commit (decision `b-all-frozen`, 2026-10-02, option «Полный скан + список 15 (Рекомендуется)»; gate.py/test_gate.py unchanged)
3. **Task 3: apply decision, BASELINE, CLAUDE.md, acceptance**
   - `19acde0` (docs) BASELINE: shield policy and Phase 1 outcome
   - `539c55a` (docs) CLAUDE.md: gate command line (separate commit)

**Plan metadata:** the final docs commit (SUMMARY, STATE, ROADMAP, REQUIREMENTS) follows this file.

Ledger base for this plan: chat-app `e51c729`; measured `e51c729..539c55a` = 3 commits. assistant-core: no commits in this plan (its Phase 1 local commits on `main`: `98ea591`, `8add0c3`, `06792b7`, all from earlier plans; no push).

## Files Created/Modified

- `scripts/gate.py` - SHIELD_MODE, KNOWN_SHIELD_FALSE_POSITIVES (15), parse_shield_findings, compare_shield_findings, run_shield_step (Task 1)
- `backend/tests/test_gate.py` - tests for finding parsing and comparison on synthetic shield output (Task 1)
- `docs/BASELINE.md` - sections «Политика security_shield» and «Итог после Фазы 1»
- `CLAUDE.md` - one added line «Run Quality Gate (both repos)» after the Security Scan item

## Decisions Made

- Shield mode `b-all-frozen` chosen by the owner on 2026-10-02 via AskUserQuestion («Полный скан + список 15 (Рекомендуется)»). `--all` scans every tracked file; green means "no finding beyond the 15 known ones, shield ran, no stale entry". The list is not extended automatically and only shrinks.
- Owner decision on local commits on `main` in `/opt/assistant-core` («Коммиты в main для всей Фазы 1»): applied for the whole phase; no push; no `.planning/` or config there. This plan made no commits there.
- Because the chosen option equals the interim implementation, no gate.py/test_gate.py change was made in Task 3 (plan step 5, commit (1), is conditional on `a-staged`).

## Deviations from Plan

None - plan executed exactly as written. The cross-check of `ignore_imports` required the five entries to appear verbatim with `->`; the earlier BASELINE table used `→`, so the verbatim block was added in the new section (within the planned task scope).

## Issues Encountered

None. Note for the record: `assistant-worker` shows `failed` (not active) since before Phase 1, per STATE.md; it was not started or touched. `chat-app` and `dev-bridge` are `inactive`.

## Review for owner: CLAUDE.md changed

CLAUDE.md is a checked-in agent instruction file. Commit `539c55a` adds exactly one line (`git diff --numstat 7925190 -- CLAUDE.md` -> `1 0`), in section 3 right after the Security Scan item:

`- **Run Quality Gate (both repos):** python3 /opt/chat-app/scripts/gate.py ... exit 0 = «ЗЕЛЁНЫЙ»; см. docs/BASELINE.md`

Please review it; revert with `git revert 539c55a` if undesired.

## Edge-probe flag (FND-04)

FND-04 stays "unclassified — review manually" per the plan. Interpretation used: «итог по каждому репозиторию» = a table row per check with the repository named, plus the overall verdict; «правило зафиксировано документом baseline» = the BASELINE «Правила» and «Итог после Фазы 1» sections. Needs a manual check at verification.

## Known Stubs

None.

## Threat Flags

None. (T-01-14..T-01-17 mitigations hold: gate output free of remote/e-mail lines and addresses; stale or new findings make the row red; CLAUDE.md change is one line, flagged above.)

## Next Phase Readiness

- Phase 1 plans 4 of 4 complete; ready for phase verification (`/gsd-verify-work 1`), then Phase 2 (PRT-04 empties the five `ignore_imports`).
- Gate invariants for later phases: eight rows green, live `assistant.db` SHA-256 prefix `baef14f7`, services stopped.

## Self-Check: PASSED

- Files: scripts/gate.py, backend/tests/test_gate.py, docs/BASELINE.md, CLAUDE.md all FOUND.
- Commits: 15a08df, 19acde0, 539c55a FOUND on master.
- Acceptance: gate green (eight rows, rc 0); red path rc 1; backend/app and src untouched; services not active; DB prefix baef14f7; both `git status` clean apart from the three pre-existing untracked `.planning` files; hygiene check «нарушений: 0» for BASELINE.md and CLAUDE.md.

---
*Phase: 01-strahovochnaya-set-i-karkas*
*Completed: 2026-10-02*
