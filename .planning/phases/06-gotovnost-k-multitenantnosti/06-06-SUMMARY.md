# Summary: Wave 6 (Plan 06-06) — Параметризация скриптов, перенос reconcile_report и обнуление HARDCODE_BASELINE = {}

## Status: COMPLETE
- **Requirements Covered:** FIN-01 (Part 2 — Final Metric)
- **Commits:**
  - `fa76c11` (`chat-app`): `feat(scripts): parameterize notion_dev and daedalus scripts, zero out HARDCODE_BASELINE (FIN-01)`
  - `ab859dd` (`assistant-core`): `feat(scripts): move reconcile_report, parameterize scripts, and zero out HARDCODE_BASELINE (FIN-01)`

## What Changed:
1. **Перенос архивных отчетов (D-15):**
   - Файл `/opt/assistant-core/reconcile_report.json` перемещен в `docs/baseline/reconcile_report.json` через `git mv` и исключен из корня сканирования хардкода.

2. **Параметризация вспомогательных скриптов (D-14):**
   - В `chat-app`:
     - `scripts/run_daedalus.sh`: устранены персональные и организационные токены, заменены на нейтральные формулировки.
     - `scripts/notion_dev.py`: статические токены организаций в кэше проектов заменены на обобщенные ключи (`corporate`, `academic`, `science`), дефолтный модуль изменен на `Core`.
   - В `assistant-core`:
     - `scripts/notion_dev.py`: синхронизирован с версией из `chat-app`.
     - `scripts/create_lab_tasks.py`: динамический импорт LMS-клиента, базовый URL из персоны, параметризация через `argparse`.
     - `scripts/download_fizikaguap_materials.py`: замена абсолютных URL на относительные пути ресурсов с поддержкой `--base-url` через `argparse`.
     - `scripts/generate_brief.py`: устранение жестко зашитого префикса `rasp_guap_`, поддержка `--source-id` и `--no-telegram` через `argparse`.
     - `scripts/populate_notion_retrospective.py`: обобщение исторических описаний майлстоунов без персональных токенов, интеграция `argparse`.
     - `scripts/provision_dev_roadmap.py`: замена жестких наименований организаций и модулей на обобщенные категории архитектурного роадмапа, добавление `argparse`.
     - `scripts/provision_notion.py`: динамическое получение названий организаций из `current_persona()` при развертывании баз данных Notion.
     - `scripts/publish_lab1_tasks.py`: динамический импорт LMS-клиента, фильтрация по фамилии из `current_persona()`, параметры `--teacher`, `--semester` через `argparse`.
     - `scripts/reconcile_schedule.py`: динамический fallback на конфигурацию расписания персоны, сохранение отчета в `docs/baseline/`, добавление `argparse`.
     - `scripts/run_stt_stress_test.py`: выборка названий организаций из `current_persona()`, добавление `argparse`.
     - `scripts/test_secretary_simulation.py`: динамический импорт LMS, получение названий организаций из `current_persona()`, безопасные сценарии диалога.

3. **Полное обнуление HARDCODE_BASELINE (FIN-01, D-16):**
   - `/opt/chat-app/backend/tests/hardcode_baseline.py`: `HARDCODE_BASELINE = {}`.
   - `/opt/assistant-core/tests/hardcode_baseline.py`: `HARDCODE_BASELINE = {}`.
   - `test_hardcode_scanner.py` в обоих репозиториях: 3 passed (0 новых находок, 0 устаревших записей).

4. **Полный Quality Gate платформы (`scripts/gate.py`):**
   - `chat-app`: pytest — 171 passed.
   - `chat-app`: import-linter — passed.
   - `assistant-core`: pytest — 353 passed.
   - `assistant-core`: import-linter — passed.
   - `chat-app` & `assistant-core`: security_shield (--all) — clean.
   - Дрейф синтетической персоны и токенов персоны — SHA-256 идентичен.
   - Боевая база `data/assistant.db` — SHA-256 не изменен.
   - **ИТОГ: ЗЕЛЁНЫЙ** (код возврата 0).
