---
phase: "04"
slug: "vladelets-shemy-bd-i-obschaya-biblioteka-bezopasnosti"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-03"
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (chat-app & assistant-core) |
| **Config file** | `pytest.ini` / `pyproject.toml` в обоих репозиториях |
| **Quick run command** | `pytest backend/tests/test_database_isolated.py backend/tests/test_security_shared.py -q` |
| **Full suite command** | `python3 /opt/chat-app/scripts/gate.py` |
| **Estimated runtime** | ~15-20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_database_isolated.py backend/tests/test_security_shared.py -q`
- **After every plan wave:** Run `python3 /opt/chat-app/scripts/gate.py`
- **Before `/gsd-verify-work`:** Full suite must be green (`ИТОГ: ЗЕЛЁНЫЙ`)
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | DAT-01 | T-04-01 | Схема БД разворачивается мигратором без ad hoc DDL | unit/integration | `pytest tests/test_migrations.py -k test_initial_schema` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | DAT-02 | T-04-02 | Путь к БД конфигурируется через env, хардкод убран | unit | `pytest tests/test_db_config.py` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | DAT-03 | T-04-03 | Конкурентная запись без database is locked при WAL | integration | `pytest tests/test_concurrent_write.py` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | DAT-04 | T-04-04 | Тесты chat-app проходят автономно без /opt/assistant-core | integration | `ASSISTANT_CORE_DIR="/nonexistent" pytest backend/tests` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | SEC-01 | T-04-05 | Общая библиотека проверок безопасности SECRET_PATTERNS | unit | `pytest tests/test_security_shared.py` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | SEC-02 | T-04-06 | security_shield.py — тонкая обёртка, эквивалентность NDA | integration | `pytest tests/test_shield_parity.py` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 4 | SEC-03 | T-04-07 | Pre-commit hook блокирует фиксацию синтетических секретов | integration | `pytest tests/test_pre_commit_hook.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/assistant-shared` или `/opt/assistant-shared` — создание пакета и установка в `.venv`
- [ ] `assistant_shared/db/migrations/0001_initial_schema.sql` — базовая DDL схема
- [ ] `assistant_shared/security/` — модуль правил безопасности

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| *None* | — | — | Все проверки автоматизированы через pytest и gate.py |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending 2026-10-03
