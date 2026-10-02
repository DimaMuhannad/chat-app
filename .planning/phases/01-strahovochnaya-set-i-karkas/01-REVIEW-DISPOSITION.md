---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Live-DB guard is detect-only; the recovery snapshot is deleted or already mutated"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Hash scope is too narrow: only the main DB file, no sidecars, no session or token files"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Ambient environment is inherited by pytest; the test set can be narrowed silently, and there is no test-count floor"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`--save-pytest-output` writes raw stdout into a tracked directory without sanitising, and also writes red runs"
  - id: WR-05
    severity: warning
    disposition: open
    title: "The gate leaves unbounded junk inside the assistant-core repository"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`test_known_shield_false_positives_total_is_fifteen` contradicts the \"list only shrinks\" policy"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Owner PII is committed in two repositories' test files, contradicting the file's own stated rule"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Drift check covers only one of the three \"byte-identical\" files"
  - id: WR-09
    severity: warning
    disposition: open
    title: "The safety-critical gate paths have no tests"
  - id: IN-01
    severity: info
    disposition: open
    title: "Dev dependencies use `>=` while BASELINE pins and vets exact versions"
  - id: IN-02
    severity: info
    disposition: open
    title: "Timeouts kill only the direct child"
  - id: IN-03
    severity: info
    disposition: open
    title: "`ASSISTANT_CORE_DIR` silently redirects both the executed binaries and the guarded DB"
  - id: IN-04
    severity: info
    disposition: open
    title: "Small defects in gate control flow"
  - id: IN-05
    severity: info
    disposition: open
    title: "Lint step success is judged only by the return code"
open: 14
total: 14
recorded: 2026-10-02T05:37:07.437Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
