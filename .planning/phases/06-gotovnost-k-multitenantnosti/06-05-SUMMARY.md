# Summary: Wave 5 (Plan 06-05) — Ликвидация остаточного хардкода в боевых модулях src/ ядра и веб-студии

## Status: COMPLETE
- **Requirements Covered:** FIN-01 (Part 1)
- **Commits:**
  - `ec5d580` (`chat-app`): `refactor: eliminate hardcoded rasp_guap prefix in chat-app db`
  - `3ed2e08` (`assistant-core`): `refactor(core): eliminate all hardcoded persona tokens from src/ modules and baseline (FIN-01)`

## What Changed:
1. **Chat-App Backend (`backend/app/db.py`):**
   - Заменен префикс `'rasp_guap_%'` на `'rasp_%'`.
   - Удалена запись `backend/app/db.py` из `backend/tests/hardcode_baseline.py`.
   - Прогон тестов бэкенда: 171 passed.

2. **Assistant Core (`src/`):**
   - Очищены от хардкода все 22 боевых модуля `src/`:
     - `src/brain/debrief_parser.py`
     - `src/brain/intent_router.py`
     - `src/brain/methodist.py`
     - `src/brain/reply_generator.py`
     - `src/brain/secretary_dialog.py`
     - `src/brain/summarizer.py`
     - `src/collector/email_collector.py`
     - `src/composition.py`
     - `src/config.py`
     - `src/connectors/aadhk/parser.py`
     - `src/connectors/guap_lms/__init__.py`
     - `src/connectors/guap_lms/client.py`
     - `src/connectors/guap_lms/provider.py`
     - `src/detector/tg_filter.py`
     - `src/main.py`
     - `src/models/schedule.py`
     - `src/models/second_brain.py`
     - `src/notifier/bot_handler.py`
     - `src/notifier/live_ticker.py`
     - `src/notifier/telegram.py`
     - `src/security/airgap.py`
     - `src/sender/email_sender.py`
     - `src/storage/db.py`
   - Все 22 записи `src/` удалены из `tests/hardcode_baseline.py`.
   - Сканер `tests/test_hardcode_scanner.py`: 3 passed, 0 stale, 0 new tokens.
   - Полный сьют `assistant-core`: 353 passed.
