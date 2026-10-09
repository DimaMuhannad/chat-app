---
phase: "06"
plan: "02"
requirements-completed: [ISO-02]
key-files:
  created:
    - /opt/assistant-core/src/security/airgap.py
    - /opt/assistant-core/tests/test_airgap_trap.py
  modified:
    - /opt/assistant-core/src/core/exceptions.py
    - /opt/assistant-core/src/brain/reply_generator.py
    - /opt/assistant-core/src/brain/secretary_dialog.py
    - /opt/assistant-core/src/brain/summarizer.py
    - /opt/assistant-core/.importlinter
backfilled: 2026-10-09
---

# Summary: Plan 06-02 — Внутренний Air-Gap для корпоративной почты и защита контекста LLM

## Status: COMPLETE
- **Requirements Covered:** ISO-02
- **Commits:**
  - `56e8fea` (`assistant-core`): `feat(06-02): enforce corporate nda air-gap for email and llm context`

> Отчёт восстановлен 2026-10-09 по коммиту при закрытии цикла v2.0: план был выполнен 2026-10-04, но SUMMARY не был записан.

## What Changed:
- Новый модуль `src/security/airgap.py`: `is_nda_email()` определяет письма рабочих пространств уровня `restricted_nda` персоны; `mask_nda_email_data()` заменяет тело и вложения маркером `NDA_MASK_MARKER`.
- `src/core/exceptions.py`: `AirGapViolationError`.
- `ReplyGenerator`: автогенерация ответа на NDA-письмо запрещена (исключение `AirGapViolationError`).
- `SecretaryDialogEngine` и `GeminiSummarizer`: NDA-письма маскируются до попадания в контекст LLM.
- `.importlinter`: контракт дополнен новым модулем безопасности.

## Tests:
- `tests/test_airgap_trap.py`: определение NDA-писем, маскирование, блокировка ответа, маскирование в обзоре/поиске секретаря и в саммари, полный сценарий диалога со шпионом LLM, обычные письма не затронуты.
