---
phase: 03-persona-kak-dannye
fixed_at: 2026-10-03T00:00:00Z
review_path: /opt/chat-app/.planning/phases/03-persona-kak-dannye/03-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 11
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-10-03
**Source review:** /opt/chat-app/.planning/phases/03-persona-kak-dannye/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 11 (CR-01, CR-02, WR-01..WR-09)
- Fixed: 11 (several partially, see "Deviations from the suggested fix")
- Skipped: 0

**Environment:** `workflow.use_worktrees=false`, so edits and commits were made in the main checkouts (no worktree, no sentinel). Verification ran in the main checkouts: `backend/.venv/bin/pytest backend/tests` in /opt/chat-app (128 passed), `.venv/bin/pytest tests` in /opt/assistant-core (330 passed) and `lint-imports` (5 contracts kept). Services were not restarted.

The fixes live in two git repos. Commits for CR-01, CR-02, WR-01 and WR-07 are in /opt/chat-app (branch master). Commits for WR-02 through WR-06, WR-08 and WR-09 are in /opt/assistant-core (branch main).

## Fixed Issues

### CR-01: NDA remote rule disabled silently for empty workspace data (fail-open)

**Repo:** /opt/chat-app
**Files modified:** `backend/app/api/v1/security.py`
**Commit:** 703513a
**Applied fix:** `nda_rule_for` drops empty substrings. `audit_path` adds a CRITICAL violation when a restricted_nda workspace has no remote rules (fail-closed). `/security/audit` with an unknown `project_id` now returns 404 instead of `passed` with `audited_count: 0`.
**Status:** fixed: requires human verification (logic change in a security gate)

### CR-02: Task form wipes area with an empty string

**Repo:** /opt/chat-app
**Files modified:** `backend/app/static/index.html`, `backend/app/api/v1/tasks.py`
**Commit:** e4737c6
**Applied fix:** All three suggested parts were applied. `editTask` adds a missing area as an option before selecting it. `saveTaskModal` omits `area` from the payload when empty. `update_task` on the server drops an empty or None `area` from the update.
**Status:** fixed: requires human verification (UI logic, not browser-tested)

### WR-01: Stored XSS via unescaped task and reminder fields

**Repo:** /opt/chat-app
**Files modified:** `backend/app/static/index.html`
**Commit:** dcf06ef
**Applied fix:** `due_date`, `priority` and `check_date` (all 5 places) are wrapped in `escapeHtml`. The workspace id in the security table button moved from an inline `'${p.id}'` in `onclick` to `data-project-id="${escapeHtml(p.id)}"` plus `onclick="runSecurityAudit(this.dataset.projectId)"`.
**Not applied:** server-side validation of `due_date`/`check_date` as dates and `priority` as `Literal`. Existing rows and other writers (the daemon) could be rejected, so this needs a separate decision.

### WR-02: PersonaConfigError swallowed by generic `except Exception`

**Repo:** /opt/assistant-core
**Files modified:** `src/brain/summarizer.py`, `src/brain/methodist.py`, `src/main.py`, `src/brain/secretary_dialog.py`, `src/notifier/live_ticker.py`
**Commit:** 596fd6b
**Applied fix:** Each site now handles `PersonaConfigError` explicitly and logs at `error` level. The summarizer, methodist, main (morning-brief timesheet) and live_ticker use a separate `except PersonaConfigError` branch. secretary_dialog picks `logger.error` or `logger.debug` by exception type in a single handler, so the "Тидекс" literal is not duplicated (the hardcode baseline would otherwise grow).
**Deviation:** the degraded behaviour (fallback template, "out of scope", missing timesheet) is kept rather than re-raising. Re-raising would crash the daily digest and the live ticker. This is the second option the review offered (log at error level). A startup completeness check was not added (see WR-03).
**Status:** fixed: requires human verification (behavioural choice)

### WR-03: Jinja2 render errors not converted to PersonaConfigError

**Repo:** /opt/assistant-core
**Files modified:** `src/persona/prompts.py`, `tests/test_persona_loader.py`
**Commit:** 10d8076
**Applied fix:** `render_prompt` wraps `jinja2.TemplateError` (UndefinedError, TemplateNotFound, TemplateSyntaxError) in `PersonaConfigError`. The message has only the key, persona id and exception class name, with no context values. `test_render_unknown_variable_raises` now expects `PersonaConfigError`.
**Not applied:** requiring the 8 `prompts` keys at load time and a trial render of all templates at startup. Partial fix only. A broken persona now fails with a clear `PersonaConfigError` at the call, but not at startup.

### WR-04: Connector binding params not validated

**Repo:** /opt/assistant-core
**Files modified:** `src/persona/models.py`, `tests/test_persona_loader.py`
**Commit:** 09521aa
**Applied fix:** Pydantic models (extra=forbid) for the `schedule_source`, `timesheet` and `lms` roles are validated when `ConnectorsConfig` is built. Slot `start` and `end` must be strings matching `HH:MM`, so an unquoted `11:10` (read by PyYAML as 670) is rejected. `number >= 1`, `daily_norm_hours > 0`, `base_url` must match `^https?://`, and `default_project` must be non-empty. Errors name the role, binding id and field, never the values. Tests that built lms bindings without config were given a valid config, and a new test covers the 670 case and a zero norm.
**Deviation:** `bindings.*_settings` were left as they were (they still convert values), and the other roles (`calendar_sync`, `git_source`, `notion`) have no param schema yet.
**Status:** fixed: requires human verification (a binding with no config now fails persona load)

### WR-05: Whole persona passed into every template context

**Repo:** /opt/assistant-core
**Files modified:** `src/persona/prompts.py`, `tests/test_persona_prompts.py`
**Commit:** 497a709
**Applied fix:** The context contains only a whitelist of persona fields (`TEMPLATE_PERSONA_FIELDS`). `workspaces` (NDA rules), `telegram`, `methodist` and `prompts` are excluded. A new test checks that `{{ persona.workspaces }}` fails to render.
**Deviation from the suggested whitelist:** `connectors` is kept because `secretary_default.jinja2` reads `persona.connectors.timesheet[0].config.daily_norm_hours`. Connector configs hold URLs, slots and the hours norm, and no NDA rules. Narrowing this further needs a template change.

### WR-06: file_catalog paths and keywords not validated

**Repo:** /opt/assistant-core
**Files modified:** `src/persona/models.py`, `src/brain/secretary_dialog.py`, `tests/test_persona_config.py`
**Commit:** 5756d60
**Applied fix:** `FileCatalogEntry.relpath` must be relative, with no `..` and no backslash. Keyword lists (file catalog, `out_of_scope_keywords`, `academic_keywords`) are normalized with `strip().lower()`, matching the `.lower()` applied to the query at the call sites, and an empty keyword is rejected. `_search_local_files_context` also checks `path.resolve().is_relative_to(raw_dir.resolve())`.
**Deviation:** `.lower()` rather than `.casefold()`, for consistency with the matching code. The `raw_dir` and `kb_dir` values themselves are not validated.

### WR-07: Weak remote matching in the web NDA audit

**Repo:** /opt/chat-app
**Files modified:** `backend/app/api/v1/security.py`, `backend/tests/test_nda_equivalence.py`
**Commit:** 1f6959d
**Applied fix:** New `normalize_remote` (casefold, strips `scheme://`, `user@`, a trailing `.git` and slash, converts scp form `host:owner/repo` to `host/owner/repo`). It is applied to both the origin and the forbidden substrings. A test covers the https, scp, ssh:// and token forms.
**Not applied:** a violation for an NDA repo with no origin. Golden test N05 pins "no origin is clean", so changing it is a policy decision. SSH host aliases (`git@alias:owner/repo`) still cannot match a `host/owner` substring.
**Status:** fixed: requires human verification (matching logic)

### WR-08: Cosmetic accessors fail without a schedule_source binding

**Repo:** /opt/assistant-core
**Files modified:** `src/persona/bindings.py`, `src/models/schedule.py`, `tests/test_persona_loader.py`
**Commit:** 9a7c94e
**Applied fix:** New `has_binding(role)`. `lesson_slot_numbers()` and `subject_short_names()` return `{}` when there is no schedule_source binding. Genuine config errors on an existing binding still raise. All callers (calendar/client, live_ticker, schedule formatting) go through these two functions, so no call sites changed. A test covers a persona without the binding.
**Not applied:** caching of the parsed settings (the review mentioned repeated parsing).

### WR-09: Loader does not wrap UnicodeDecodeError

**Repo:** /opt/assistant-core
**Files modified:** `src/persona/loader.py`
**Commit:** 2a3e8dc
**Applied fix:** `except (OSError, UnicodeDecodeError)` with a message that has no file contents. Confirmed manually on a file starting with the byte 0xFF.

## Skipped Issues

None. Info findings (IN-01 to IN-07) were out of scope for `fix_scope: critical_warning`.

---

_Fixed: 2026-10-03_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
