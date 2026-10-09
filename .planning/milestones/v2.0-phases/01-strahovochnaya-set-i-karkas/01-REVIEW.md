---
phase: 01-strahovochnaya-set-i-karkas
reviewed: 2026-10-02T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - /opt/chat-app/.importlinter
  - /opt/chat-app/.gitignore
  - /opt/chat-app/CLAUDE.md
  - /opt/chat-app/backend/tests/conftest.py
  - /opt/chat-app/backend/tests/synthetic_persona.py
  - /opt/chat-app/backend/tests/test_architecture_contract.py
  - /opt/chat-app/backend/tests/test_gate.py
  - /opt/chat-app/backend/tests/test_synthetic_persona.py
  - /opt/chat-app/docs/BASELINE.md
  - /opt/chat-app/docs/baseline/pytest-assistant-core.txt
  - /opt/chat-app/docs/baseline/pytest-chat-app.txt
  - /opt/chat-app/requirements-dev.txt
  - /opt/chat-app/scripts/gate.py
  - /opt/assistant-core/.gitignore
  - /opt/assistant-core/.importlinter
  - /opt/assistant-core/requirements-dev.txt
  - /opt/assistant-core/tests/conftest.py
  - /opt/assistant-core/tests/synthetic_persona.py
  - /opt/assistant-core/tests/test_architecture_contract.py
  - /opt/assistant-core/tests/test_synthetic_persona.py
findings:
  critical: 0
  warning: 9
  info: 5
  total: 14
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-02
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Reviewed gate.py (the central file), both import-linter contracts, the contract tests, the synthetic persona scaffold, and the baseline documents in both repositories. gate.py was read only, never executed. The live `assistant.db` was not opened. I read only its first 100 bytes, to check the SQLite journal mode. I did not read `.env` (a secret-read hook blocked one such attempt, which is fine).

Confirmed good:
- All subprocess calls use list arguments with `shell=False` and a timeout.
- `make_db_copy` opens the source with `mode=ro`.
- `chat_pytest_env` refuses a missing copy and the live path.
- Both `synthetic_persona.py` copies and both `test_synthetic_persona.py` copies are currently byte-identical (checked with sha256sum).
- No remote URL, e-mail or secret leaks through gate.py's output or through the committed files `docs/BASELINE.md` and `docs/baseline/*.txt`. `parse_shield_findings` discards everything except path, kind and count.

I found no outright blockers. The main weaknesses are in what the gate promises about protecting the live DB and about "no false green":
- The live-DB guard only detects damage after the fact, and its scope is one file.
- The pytest environment is not isolated from the caller's environment.
- There is no floor on the number of tests.
- The gate leaves junk files in the assistant-core repository.
- The persona denylist contains the owner's PII, and it is committed.

## Warnings

### WR-01: Live-DB guard is detect-only; the recovery snapshot is deleted or already mutated

**File:** `/opt/chat-app/scripts/gate.py:486-528` (also 97-113, 515-518)
**Issue:** The assistant-core pytest run has `env_extra=None` and `cwd=CORE_DIR`. Nothing physically stops it from writing to `/opt/assistant-core/data/assistant.db`.
- `Database.__init__` defaults to `./data/assistant.db`, which is the live DB when cwd is `CORE_DIR`.
- `EmailCollector()` falls back to `Database(config.SQLITE_DB_PATH)`, the live path.
- Any future test calling `Database()` or `init_db()` without an argument would write the live DB.
- The only defence is the SHA-256 comparison after all steps, which makes the run red after the damage is done.
- The `finally` block then runs `shutil.rmtree(tmp_dir)`, so the pre-run copy is deleted exactly when it is needed.
- That copy is also not pristine. The chat-app CRUD tests write into it (`SQLITE_DB_PATH` points there), so it cannot serve as a recovery source.

Net effect: on a "боевая assistant.db не изменена" red result there is nothing to restore from.

**Fix:** Take a second pristine backup (the DB is about 7.6 MB) before any pytest run. Keep it, and print its path, when `db_unchanged_check` is red.
```python
pristine = make_db_copy(LIVE_DB, tmp_dir)  # before the chat-app pytest run
shutil.copy2(pristine, tmp_dir / "pristine.db")
...
if not db_check.ok:
    keep = Path("/root/gate-recovery"); keep.mkdir(mode=0o700, exist_ok=True)
    shutil.copy2(tmp_dir / "pristine.db", keep / f"assistant-{datetime.now():%Y%m%d-%H%M%S}.db")
```
Better still, prevent the write. For example, run the core pytest under `systemd-run --property=ReadOnlyPaths=/opt/assistant-core/data` (or `unshare -m` plus a read-only bind mount), so a stray write fails instead of silently corrupting.

### WR-02: Hash scope is too narrow: only the main DB file, no sidecars, no session or token files

**File:** `/opt/chat-app/scripts/gate.py:44, 488, 525, 406-412`
**Issue:** `before` and `after` are SHA-256 of `data/assistant.db` alone.
- If the DB is ever switched to WAL, writes land in `assistant.db-wal` and the main file's hash stays unchanged until a checkpoint. The guard goes false-green. The header currently shows journal mode 1/1 (rollback journal), so this is latent today, but `journal_mode=WAL` is persistent and trivial to enable.
- `-journal` and `-shm` files are not compared.
- Other live assets that the assistant-core tests touch are not covered at all:
  - `data/assistant_worker.session`
  - `data/telethon_userbot.session`
  - `token.json`
  - `credentials.json`
  - `.env`
  - the stray 0-byte `/opt/assistant-core/assistant.db`
- A Google OAuth token refresh would rewrite `token.json` silently.

Hashing `.env` would conflict with the docstring's "не читает .env", so use stat fingerprints for those files.

**Fix:** Add a fingerprint of `(st_size, st_mtime_ns, st_ino)` for the sidecars and secret files, and make the DB hash cover `-wal` when it exists.
```python
GUARDED = [LIVE_DB, *(LIVE_DB.with_name(LIVE_DB.name + s) for s in ("-wal", "-shm", "-journal")),
           *CORE_DIR.joinpath("data").glob("*.session"), CORE_DIR / "token.json",
           CORE_DIR / "credentials.json", CORE_DIR / ".env"]
def fingerprint():
    return {str(p): (p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ino) if p.exists() else None for p in GUARDED}
```

### WR-03: Ambient environment is inherited by pytest; the test set can be narrowed silently, and there is no test-count floor

**File:** `/opt/chat-app/scripts/gate.py:116-134, 198-207, 240-271`
**Issue:** `run_cmd` copies `os.environ` wholesale. `PYTEST_ADDOPTS` (for example `--ignore=tests/test_voice.py`, `--ignore-glob`, `-p no:...`), `PYTEST_PLUGINS`, and `PYTEST_DISABLE_PLUGIN_AUTOLOAD` therefore reach pytest.
- `--deselect` and `-k` are caught by `pytest_summary_flags`, but `--ignore` and `--ignore-glob` produce no "deselected" word. With tests greater than 0, the gate reports "ЗЕЛЁНЫЙ". This contradicts BASELINE ("набор тестов не сужается").
- `pytest_ok` only requires `tests > 0`. Deleting 100 of 127 assistant-core tests stays green, although rule 3 in BASELINE ("существующие тесты не удаляются") is meant to be enforced by the gate. The baseline counts (14 and 127) are not used.

**Fix:** Scrub the environment for pytest and add a minimum from the baseline:
```python
_DROP = ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST")
env = {k: v for k, v in os.environ.items() if k not in _DROP}
MIN_TESTS = {REPO_CHAT: 68, REPO_CORE: 139}   # only grows
# in pytest_ok / run_pytest_step: counts["tests"] >= MIN_TESTS[repo]
```

### WR-04: `--save-pytest-output` writes raw stdout into a tracked directory without sanitising, and also writes red runs

**File:** `/opt/chat-app/scripts/gate.py:219-228, 255-256`
**Issue:**
- `_write_snapshot` sanitises only the command line (`tmp_dir` replaced). `proc.stdout` is written verbatim.
  - The committed baselines still contain `/tmp/gate-0iai7ww_/junit-*.xml` (`docs/baseline/pytest-chat-app.txt:25`, `pytest-assistant-core.txt:150`).
  - On a failing run, tracebacks and assertion diffs include data read from the live-DB copy (chat-app CRUD tests) or from `.env`-derived settings (assistant-core). That text would go straight into `docs/baseline/`, which is under git.
- The snapshot is written regardless of the result, so a red run can overwrite the "known green" baseline.
- The `# Коммит:` header records HEAD without marking a dirty tree. The baseline header names `11b0c5e`, but the run happened with an untracked gate.py and uncommitted changes.

**Fix:** Write the snapshot only when the step is green. Apply `.replace(str(tmp_dir), "временный каталог")` to the stdout as well. Add `git status --porcelain` to the header and mark it `(есть незакоммиченные изменения)` when non-empty.

### WR-05: The gate leaves unbounded junk inside the assistant-core repository

**File:** `/opt/chat-app/scripts/gate.py:246-250, 489, 526-528`
**Issue:** `--basetemp={tmp_dir}/pytest-{repo}` is an absolute path under `/tmp`. Several assistant-core tests build `Database(f"sqlite+aiosqlite:///{tmp_path}/x.db")`, which BASELINE already notes as the `sqlite+aiosqlite:` side effect.
- With an absolute `/tmp/...` path after three slashes, the path becomes relative.
- Every gate run therefore creates `/opt/assistant-core/sqlite+aiosqlite:/tmp/gate-<random>/pytest-assistant-core/.../*.db`.
- I verified this on disk. There are 10 `gate-*` directories and 214 files, and the count grows with each run.
- The `finally` block removes only `tmp_dir`, not these directories.
- The module docstring and BASELINE promise isolation. The files are hidden from `git status` only because `.gitignore` has `*.db`.

**Fix:** In the `finally` block, also remove `CORE_DIR / "sqlite+aiosqlite:" / "tmp" / tmp_dir.name` (ignore errors). Longer term, fix the test paths in Phase 2.

### WR-06: `test_known_shield_false_positives_total_is_fifteen` contradicts the "list only shrinks" policy

**File:** `/opt/chat-app/backend/tests/test_gate.py:316-318`
**Issue:** The test asserts `total == 15`. When the owner legitimately removes a frozen false positive (BASELINE rule 4), the chat-app suite goes red, so the owner has to edit the test as well. That pushes people toward weakening or bypassing the check. The invariant that matters, "never grows", is `<= 15`. Stale entries are already caught at runtime by `compare_shield_findings`.
**Fix:**
```python
MAX_KNOWN_FALSE_POSITIVES = 15
assert total <= MAX_KNOWN_FALSE_POSITIVES
```

### WR-07: Owner PII is committed in two repositories' test files, contradicting the file's own stated rule

**File:** `/opt/chat-app/backend/tests/test_synthetic_persona.py:17-26, 28-64` (byte-identical copy at `/opt/assistant-core/tests/test_synthetic_persona.py`)
**Issue:** `OWNER_TOKEN_DENYLIST` and `CURRENT_HARDCODED_DEFAULTS` hold:
- the owner's full name with patronymic ("Попов Дмитрий Александрович"), the short name, and the personal GitHub handle `DimaMuhannad` with `github.com/DimaMuhannad`;
- employer names and the employer workspace paths (`/opt/work-tydex`, the "ООО «Тидекс»" workspace name).

The comment on line 28 says "Реальный Telegram ID владельца сюда не копируется (персональные данные)". By that same rule, the full name and handle are personal data. assistant-core's origin is `github.com/DimaMuhannad/assistant-core.git`, and committing corporate workspace identifiers into a personal account's repo is in tension with the project's NDA air-gap model. The fixture exists to prove the persona has no owner tokens, but it embeds them in plaintext.

**Fix:** Keep only SHA-256 digests of lowercased tokens in the committed denylist and compare against the digests of the persona's tokens. Or read the denylist at test time from an untracked local file such as `config/owner_denylist.local`, with the test failing loudly if it is missing. Phase 3 (PER-08) is intended to replace this with the default persona's data. Until then, at minimum drop the full name and the GitHub handle.

### WR-08: Drift check covers only one of the three "byte-identical" files

**File:** `/opt/chat-app/scripts/gate.py:47-48, 415-431, 524`
**Issue:** `test_synthetic_persona.py` states "лежит байт-в-байт в обоих тестовых наборах", and `conftest.py` is also duplicated. `persona_drift_check` compares only `synthetic_persona.py`. Today all three pairs match (verified for two). A one-sided edit of the test or conftest file, such as weakening an assertion in one repo only, is not detected.
**Fix:** Compare the list `[synthetic_persona.py, test_synthetic_persona.py, conftest.py]` pairwise, and name the differing file in `detail`.

### WR-09: The safety-critical gate paths have no tests

**File:** `/opt/chat-app/backend/tests/test_gate.py` (whole file)
**Issue:** The tests cover pure helpers well. Nothing tests `make_db_copy`, `run_pytest_step`, `_run_all`, or the before/after hash flow. The promises that carry the whole phase go unchecked:
- the source DB is byte-identical after `make_db_copy`;
- no `-journal`, `-wal` or `-shm` file appears next to the source;
- the copy is a valid SQLite file;
- the hash step runs after all other steps;
- the run is red when the live DB changes.

A regression in `make_db_copy` (for example replacing `backup()` with a plain `connect`) would pass all 42 gate tests.
**Fix:** Add tests with a synthetic SQLite file in `tmp_path`: sha256 before == after `make_db_copy`; `sorted(tmp_path.iterdir())` contains no sidecar files; the copy opens and has the same rows. Also add a `run_pytest_step` test against a tiny synthetic test directory that exercises the skipped, zero-test and failing cases.

## Info

### IN-01: Dev dependencies use `>=` while BASELINE pins and vets exact versions

**File:** `/opt/chat-app/requirements-dev.txt:3-4` (and `/opt/assistant-core/requirements-dev.txt:3-4`)
**Issue:** BASELINE records `import-linter 2.15`, `grimp 3.17`, and the owner's legitimacy approval of those packages. `>=` lets an unvetted newer release in on the next `pip install`.
**Fix:** Use `import-linter==2.15` and `grimp==3.17`, or `~=`.

### IN-02: Timeouts kill only the direct child

**File:** `/opt/chat-app/scripts/gate.py:126-134`
**Issue:** `subprocess.run(timeout=...)` kills pytest only. Grandchildren, such as the `lint-imports` processes spawned by the architecture-contract tests, are orphaned and keep running against `tmp_dir`, which is about to be deleted.
**Fix:** Use `start_new_session=True` with `Popen` and `os.killpg` on timeout.

### IN-03: `ASSISTANT_CORE_DIR` silently redirects both the executed binaries and the guarded DB

**File:** `/opt/chat-app/scripts/gate.py:43-46`
**Issue:** The env var selects `.venv/bin/pytest`, `.venv/bin/lint-imports`, `scripts/security_shield.py` (all executed), and `LIVE_DB`. If it points elsewhere, the real `/opt/assistant-core/data/assistant.db` stops being hashed, while chat-app's default `SQLITE_DB_PATH` still points at it.
**Fix:** Print a warning, and treat the run as red, when `CORE_DIR` is not `/opt/assistant-core`. Alternatively hash both paths.

### IN-04: Small defects in gate control flow

**File:** `/opt/chat-app/scripts/gate.py:23, 54, 377-385, 506, 526-528`
**Issue:**
- `chat_pytest_env(db_copy)` is evaluated as an argument at line 506, outside the `_safe_*` wrappers. A `ValueError` aborts the whole gate with one "внутренняя ошибка" row, contrary to the docstring "не обрывается на первой ошибке". The branch is unreachable today.
- `SHIELD_MODE == "staged"` is a dead branch of a constant, which is YAGNI.
- The docstring lists persona drift as step 5, before security_shield, but the code runs it after.
- `rmtree(..., ignore_errors=True)` can silently leave a copy of the live DB in `/tmp`.

**Fix:** Move the `chat_pytest_env` call inside the safe wrapper. Drop the unused branch or make it a CLI flag. Align the docstring with the code order. On `rmtree` failure, print a warning with the path.

### IN-05: Lint step success is judged only by the return code

**File:** `/opt/chat-app/scripts/gate.py:293-294`
**Issue:** `proc.returncode == 0` is treated as green with no check that the expected number of contracts were evaluated (BASELINE: "2 kept" in assistant-core, "1 kept" in chat-app). An empty or truncated `.importlinter` would silently weaken the gate. The test `test_real_contract_modules_exist_in_graph` only asserts that the contract is non-empty.
**Fix:** Parse "N kept, 0 broken" from stdout and compare N with a constant per repo (`{REPO_CHAT: 1, REPO_CORE: 2}`), which only grows.

---

_Reviewed: 2026-10-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
