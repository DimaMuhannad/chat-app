# Фаза 8: Исполнительный инструментальный контур (Tool Calling)
## Отчет об исполнении Плана 08-02 (Wave 2)

**Дата:** 2026-10-05  
**Статус:** Успешно завершен (100% pass, Quality Gate ЗЕЛЁНЫЙ)  
**Коммит assistant-core:** `fdafcec`  
**Требования:** ACT-03, D-01, D-04, T-08-03, T-08-04  

---

### 1. Цели и назначение плана
Реализация интерактивного Telegram HITL-интерфейса (Human-In-The-Loop) для подтверждения действий персонального секретаря:
- Любое действие (`ActionProposal`), сформированное генеративной моделью через Function Calling, преобразуется в интерактивную Telegram-карточку с инлайн-кнопками подтверждения и отмены.
- Запрос регистрируется в едином примитиве `ConfirmationStore` (таблица `pending_confirmations`) со статусом `pending` и TTL 15 минут.
- Физическая запись в Google Calendar API или в таблицы SQLite (`reminders`, `email_drafts`) выполняется **СТРОГО** внутри зарегистрированных action-хэндлеров по факту нажатия кнопки владельцем (ACT-03).
- Внедрена строгая защита от повторных кликов (дедупликация T-08-03): при повторном клике возвращается уведомление «Запрос уже обработан или истек», а инлайн-клавиатура сообщений удаляется или текст заменяется на статус выполнения.
- Защита от истекших запросов (T-08-04): при истечении TTL действие блокируется.

---

### 2. Выполненные работы

#### Задача 08-02-01: Создание генераторов HITL-карточек и инлайн-клавиатур в `telegram.py`
1. В `/opt/assistant-core/src/notifier/telegram.py` реализованы функции:
   - `build_hitl_action_keyboard(conf_id: str, action_type: str) -> InlineKeyboardMarkup`:
     * Для `create_calendar_event`: кнопка `[📅 Записать в Google Calendar]` с `callback_data=f"act:cal:conf:{conf_id}"` и `[❌ Отмена]` с `callback_data=f"act:cal:rej:{conf_id}"`.
     * Для `create_reminder`: кнопка `[⏰ Создать напоминание]` с `callback_data=f"act:rem:conf:{conf_id}"` и `[❌ Отмена]` с `callback_data=f"act:rem:rej:{conf_id}"`.
     * Для `draft_email_reply`: кнопка `[📝 Сохранить черновик]` с `callback_data=f"act:drf:conf:{conf_id}"` и `[❌ Отмена]` с `callback_data=f"act:drf:rej:{conf_id}"`.
     * Универсальный фолбек для иных действий: `[✅ Подтвердить]` / `[❌ Отмена]`.
     * Обе кнопки компонуются в один ряд: `len(kb.inline_keyboard[0]) == 2`.
   - `format_hitl_proposal_card(action_type: str, params: dict[str, Any]) -> str`:
     * Четкое визуальное форматирование параметров с эмодзи в соответствии со стандартами проекта (без локальных file:/// ссылок).
     * Выделение параметров моноширинным текстом для дат, времени, кодов.
     * Завершающий вопрос: «Подтверждаете данное действие?».

#### Задача 08-02-02: Регистрация action-хэндлеров HITL и обработка callback_query в `bot_handler.py`
1. В `/opt/assistant-core/src/notifier/bot_handler.py`:
   - В `EmailBotHandler.__init__` добавлен параметр `calendar_client: Any | None = None`.
   - В `_register_hitl_action_handlers` зарегистрированы хэндлеры через `register_action_handler`:
     * `create_calendar_event`: парсинг даты и временных интервалов, инстанцирование модели `Lesson`, вызов `calendar_client.create_event(calendar_id, lesson)` с перехватом сетевых сбоев (D-04).
     * `create_reminder`: запись в БД через `self.db.create_reminder(...)`.
     * `draft_email_reply`: запись черновика в БД через `self.db.create_email_draft(...)`.
   - В `_register_handlers` зарегистрированы callback-роуты:
     * `act:cal:conf:` -> `self.cb_act_calendar_confirm`
     * `act:cal:rej:` -> `self.cb_act_calendar_reject`
     * `act:rem:conf:` -> `self.cb_act_reminder_confirm`
     * `act:rem:rej:` -> `self.cb_act_reminder_reject`
     * `act:drf:conf:` -> `self.cb_act_draft_confirm`
     * `act:drf:rej:` -> `self.cb_act_draft_reject`
   - Реализован централизованный обработчик `_handle_hitl_action_callback`:
     * Проверка авторизации пользователя (`self._is_authorized`).
     * Проверка статуса в `ConfirmationStore` (если не `pending` или истек срок: `callback.answer("Запрос уже обработан или истек", show_alert=True)` и снятие клавиатуры).
     * При подтверждении: вызов `resume_action`, редактирование сообщения с плашкой «✅ Событие добавлено в Google Calendar» / «✅ Напоминание успешно создано» / «✅ Черновик ответа сохранен» и снятием инлайн-клавиатуры (`reply_markup=None`).
     * При отмене: вызов `reject_action`, редактирование сообщения с плашкой «❌ Создание события отменено» / «❌ Создание напоминания отменено» / «❌ Создание черновика отменено» и снятием кнопок.
   - Метод `_handle_secretary_dialog` обновлен:
     * Запрос к `dialog_engine.answer_user_message` с `return_proposal=True` и безопасной обратной совместимостью по распаковке кортежей.
     * При получении `ActionProposal`: создание записи в `ConfirmationStore` (TTL 15 минут, канал `telegram`), объединение текстового ответа модели с карточкой `format_hitl_proposal_card` и прикрепление инлайн-клавиатуры `build_hitl_action_keyboard`.
2. Создан файл комплексных тестов `/opt/assistant-core/tests/test_hitl_telegram_cards.py`:
   - `test_hitl_action_keyboard_generation`: проверка структуры и callback_data всех видов клавиатур.
   - `test_format_hitl_proposal_card`: проверка разметки карточек предложений.
   - `test_secretary_dialog_creates_confirmation_and_sends_card`: проверка полного цикла ответа секретаря с формированием записи в `ConfirmationStore` и отправкой Telegram-сообщения с кнопками.
   - `test_cb_act_calendar_confirm_and_reject`: проверка подтверждения создания события в Google Calendar и отмены.
   - `test_cb_act_reminder_confirm_and_reject`: проверка физической записи напоминания в БД строго по факту подтверждения.
   - `test_cb_act_draft_confirm_and_reject`: проверка физического создания черновика письма в БД строго по подтверждению.
   - `test_cb_act_deduplication_and_protection`: проверка защиты от race condition / повторных кликов (T-08-03).
   - `test_cb_act_unauthorized_user_blocked`: проверка блокировки действий неавторизованными пользователями.
   - `test_cb_act_expired_action_blocked`: проверка блокировки просроченных действий (T-08-04).

---

### 3. Результаты верификации

1. **Модульные тесты `test_hitl_telegram_cards.py`:**
   ```
   tests/test_hitl_telegram_cards.py::test_hitl_action_keyboard_generation PASSED [ 11%]
   tests/test_hitl_telegram_cards.py::test_format_hitl_proposal_card PASSED [ 22%]
   tests/test_hitl_telegram_cards.py::test_secretary_dialog_creates_confirmation_and_sends_card PASSED [ 33%]
   tests/test_hitl_telegram_cards.py::test_cb_act_calendar_confirm_and_reject PASSED [ 44%]
   tests/test_hitl_telegram_cards.py::test_cb_act_reminder_confirm_and_reject PASSED [ 55%]
   tests/test_hitl_telegram_cards.py::test_cb_act_draft_confirm_and_reject PASSED [ 66%]
   tests/test_hitl_telegram_cards.py::test_cb_act_deduplication_and_protection PASSED [ 77%]
   tests/test_hitl_telegram_cards.py::test_cb_act_unauthorized_user_blocked PASSED [ 88%]
   tests/test_hitl_telegram_cards.py::test_cb_act_expired_action_blocked PASSED [100%]
   ============================== 9 passed in 30.93s ==============================
   ```

2. **Тесты предыдущего плана `test_secretary_tools.py`:**
   ```
   ========================= 7 passed, 1 warning in 1.91s =========================
   ```

3. **Изоляция групп `test_bot_group_isolation.py`:**
   ```
   ============================== 3 passed in 8.51s ===============================
   ```

4. **Общий Quality Gate (`scripts/gate.py`):**
   ```
   Гейт качества

   Репозиторий     Проверка                               Результат
   chat-app        pytest — тестов: 171                   ✓
   chat-app        import-linter                          ✓
   assistant-core  pytest — тестов: 395                   ✓
   assistant-core  import-linter                          ✓
   chat-app        security_shield (--all)                ✓
   assistant-core  security_shield (--all)                ✓
   оба             синтетическая персона (дрейф SHA-256)  ✓
   оба             токены персоны (дрейф SHA-256)         ✓
   оба             боевая assistant.db не изменена        ✓

   ИТОГ: ЗЕЛЁНЫЙ
   ```

---

### 4. Измененные и созданные файлы

```diff
+ /opt/assistant-core/tests/test_hitl_telegram_cards.py
+ /opt/chat-app/.planning/phases/08-ispolnitelnyy-kontur-tool-calling/08-02-SUMMARY.md
! /opt/assistant-core/src/notifier/telegram.py
! /opt/assistant-core/src/notifier/bot_handler.py
# Статус: Закоммичено в assistant-core [fdafcec] (Quality Gate: ЗЕЛЁНЫЙ)
```
