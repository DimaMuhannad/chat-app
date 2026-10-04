---
phase: "5"
slug: "edinyy-hitl-primitiv"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-10-04"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x / pytest-asyncio |
| **Config file** | `backend/pytest.ini` / `/opt/assistant-core/pytest.ini` |
| **Quick run command** | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_web_hitl_guardrails.py -q` |
| **Full suite command** | `python3 /opt/chat-app/scripts/gate.py` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run task quick command
- **After every plan wave:** Run `python3 /opt/chat-app/scripts/gate.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | HIT-01 | T-05-01 | Миграция 0002 создаёт таблицу pending_confirmations в SQLite | unit | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_hitl_shared.py -k test_migration_0002 -q` | ✅ | ✅ green |
| 05-01-02 | 01 | 1 | HIT-01 | T-05-02 | ConfirmationStore и декоратор @requires_confirmation работают изолированно | unit | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_hitl_shared.py -q` | ✅ | ✅ green |
| 05-02-01 | 02 | 2 | HIT-03, HIT-04 | T-05-03 | DELETE projects/tasks/documents/reminders возвращает 409 без удаления | integration | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_web_hitl_guardrails.py -k test_delete_returns_409 -q` | ✅ | ✅ green |
| 05-02-02 | 02 | 2 | HIT-03, HIT-04 | T-05-04 | GET /confirmations/{id} и confirm_action выполняют удаление ровно один раз | integration | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_web_hitl_guardrails.py -q` | ✅ | ✅ green |
| 05-03-01 | 03 | 3 | HIT-02 | T-05-05 | Telegram bot_handler подтверждает/отклоняет Web-действия только от allowed_user_id | integration | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_bot_hitl_parity.py -q` | ✅ | ✅ green |
| 05-03-02 | 03 | 3 | HIT-02 | T-05-06 | Перевод dlg:confirm_clear на общий примитив сохраняет UX 1:1 | parity | `/opt/assistant-core/.venv/bin/pytest /opt/assistant-core/tests/test_hitl_safety_guardrails.py /opt/assistant-core/tests/test_bot_group_isolation.py -q` | ✅ | ✅ green |
| 05-04-01 | 04 | 4 | HIT-03, HIT-04 | T-05-07 | Web UI поллит статус подтверждения и скрывает удаленный элемент | integration | `/opt/chat-app/backend/.venv/bin/pytest backend/tests/test_web_hitl_guardrails.py -k test_ui_polling_contract -q` | ❌ W0 | ⬜ pending |
| 05-04-02 | 04 | 4 | HIT-01..04 | T-05-08 | Все CRUD-тесты chat-app переведены на двухшаговый поток, gate.py ЗЕЛЁНЫЙ | gate | `python3 /opt/chat-app/scripts/gate.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/test_hitl_shared.py` — тесты миграции 0002, моделей и хранилища `assistant_shared.hitl`
- [x] `backend/tests/test_web_hitl_guardrails.py` — тесты перехвата DELETE, 409 Conflict, поллинга и подтверждения

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Нажатие инлайн-кнопки в Telegram с реального мобильного клиента | HIT-02 | Живой Telegram API требует разморозки сервиса | Нажать «Да, удалить» в Telegram, убедиться в исчезновении карточки |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 45s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-04
