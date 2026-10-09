# Фаза 8: Исполнительный инструментальный контур (Tool Calling)
## Отчет об исполнении Плана 08-03 (Wave 3)

**Дата:** 2026-10-05  
**Статус:** Успешно завершен (100% pass, Quality Gate ЗЕЛЁНЫЙ)  
**Коммит assistant-core:** `2e2c749`  
**Требования:** ACT-04, D-02, D-03, D-04, T-08-05, T-08-06  

---

### 1. Цели и назначение плана
Расширение возможностей маршрутизации намерений и реализация сложных сценариев взаимодействия:
- Расширение `FastIntentRouter` специализированными интентами планирования (`calendar_schedule`, `create_reminder`, `draft_reply`) для точного перенаправления запросов в исполнительный инструментальный контур.
- Реализация двухшагового Tool Calling (`D-02`): первый шаг выполняет `search_emails` по локальной базе SQLite/FTS5 для извлечения контекста и дедлайнов, второй шаг формирует целевой `ActionProposal` (например, напоминание или событие календаря).
- Внедрение строгого уточняющего диалога (`D-03`, `T-08-06`): при отсутствии точного времени встречи запрещено подставлять случайные значения (00:00 или 09:00); секретарь задает уточняющий вопрос пользователю.
- Создание локального буфера отказоустойчивости `pending_sync` в SQLite (`D-04`, `T-08-05`): при сбое сети или недоступности Google Calendar API событие не теряется, а сохраняется локально с кнопкой повтора синхронизации `[🔄 Повторить синхронизацию]`.

---

### 2. Выполненные работы

#### Задача 08-03-01: Добавление интентов планирования в FastIntentRouter и маршрутизация в bot_handler.py
1. В `/opt/assistant-core/src/brain/intent_router.py`:
   - Расширен список `VALID_ACTIONS`: добавлены `"calendar_schedule"`, `"create_reminder"`, `"draft_reply"`.
   - Внедрены детерминированные шорткаты:
     * Календарь: `запиши в календарь`, `добавь в календарь`, `запланируй встречу` -> `calendar_schedule`.
     * Напоминания: `поставь дедлайн`, `создай напоминание`, `добавь напоминание`, `напомни мне` (с фильтрацией запросов расписания) -> `create_reminder`.
     * Черновики: `ответь на письмо`, `черновик ответа`, `подготовь ответ` -> `draft_reply`.
2. В `/opt/assistant-core/config/prompts/intent_router_default.jinja2`:
   - Добавлены описания действий 10, 11, 12 с конкретными примерами для академического и корпоративного контекста.
   - Обновлен манифест и текстовый снимок `tests/fixtures/prompts_snapshot/intent_router.txt`.
3. В `/opt/assistant-core/src/notifier/bot_handler.py`:
   - В `handle_user_text` добавлена маршрутизация: интенты `calendar_schedule`, `create_reminder`, `draft_reply` передаются в `_handle_secretary_dialog(message, user_msg, intent=route_res.action)`.

#### Задача 08-03-02: Двухшаговый поиск по почте, уточнение времени и буфер pending_sync с retry-кнопкой
1. В `/opt/assistant-core/src/storage/db.py`:
   - Реализованы методы:
     * `save_pending_calendar_sync(event_data: dict[str, Any]) -> int`: сохранение параметров события в `calendar_sync_records` со статусом `pending_sync` и генерацией локального ID `pending_<uuid>`.
     * `get_pending_calendar_sync(sync_id: int) -> dict[str, Any] | None`: получение отложенной записи.
     * `update_calendar_sync_status(sync_id: int, google_event_id: str, status: str = 'active') -> bool`: перевод статуса в `active` при успешной отправке в Google.
2. В `/opt/assistant-core/src/calendar/client.py`:
   - Реализован метод `create_event_from_dict(calendar_id: str, event_data: dict[str, Any]) -> str`: парсинг даты/времени, создание объекта `Lesson` или словаря события и синхронизация с Google Calendar API.
3. В `/opt/assistant-core/src/notifier/bot_handler.py`:
   - В `cb_act_calendar_confirm`: перехват ошибок Google Calendar API -> сохранение в `save_pending_calendar_sync` -> отправка карточки «⚠️ Google Calendar временно недоступен. Событие сохранено локально (`pending_sync`).» с инлайн-кнопкой `[🔄 Повторить синхронизацию]` (`act:cal:retry:<sync_id>`).
   - Зарегистрирован callback-хэндлер `cb_act_calendar_retry`: повторная отправка в Google Calendar, обновление статуса в БД и редактирование сообщения на «✅ Синхронизировано с Google Calendar».
4. Создан тестовый модуль `/opt/assistant-core/tests/test_tool_calling_flow.py`:
   - `test_intent_router_actions_and_fast_rules`: проверка классификации интентов и шорткатов.
   - `test_bot_handler_routes_planning_intents_to_secretary_dialog`: проверка проброса интентов.
   - `test_two_step_search_emails_flow_d02`: сквозной тест `search_emails` -> `ActionProposal`.
   - `test_missing_time_clarification_no_action_proposal_d03`: тест уточнения времени встречи.
   - `test_calendar_pending_sync_buffer_and_retry_flow_d04`: тест буфера `pending_sync` и повтора синхронизации.
   - `test_google_calendar_client_create_event_from_dict`: тест парсинга и создания событий.

---

### 3. Результаты проверок и Quality Gates
- **Pytest (Phase 8 тесты):** 22/22 passed (100%).
- **Pytest (Prompts Snapshot):** 19/19 passed (100%).
- **Pytest (chat-app):** 171/171 passed (100%).
- **Pytest (assistant-core):** 401/401 passed (100%).
- **Security Shield:** 0 утечек, токены и приватные ключи защищены.
- **Дрейф синтетической персоны:** 0, хэши совпадают.
- **Боевая assistant.db:** Не затронута.
- **Quality Gate (`scripts/gate.py`):** **ИТОГ: ЗЕЛЁНЫЙ**.
