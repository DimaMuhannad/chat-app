# Фаза 8: Исполнительный инструментальный контур (Tool Calling)
## Отчет об исполнении Плана 08-01 (Wave 1)

**Дата:** 2026-10-05  
**Статус:** Успешно завершен (100% pass, Quality Gate ЗЕЛЁНЫЙ)  
**Ветвь:** main / master  
**Требования:** ACT-01, ACT-02  

---

### 1. Цели и назначение плана
Реализация фундаментального слоя исполнительного инструментального контура (Function Calling) на базе Google GenAI SDK (`types.Tool`, `types.FunctionDeclaration`) для устранения иллюзии выполнения действий («галлюцинаций») персональным секретарем доцента Попова Д.А.

Ключевые принципы:
- **HITL Guardrail (D-01, ACT-01):** Никаких прямых мутаций внешних систем (Google Calendar API) или локальных таблиц SQLite (`reminders`, `email_drafts`) из генеративного цикла. Любой вызов действия трансформируется в объект предварительного предложения `ActionProposal`.
- **Строгий антигаллюцинационный промпт (D-05, ACT-02):** Запрет утверждать об исполнении без вызова инструмента; требование переспрашивать время при неполных датах («В какое время запланировать встречу?»); обязательный вызов `search_emails` при ссылках на входящую корреспонденцию.
- **Двухшаговый Tool Calling (D-02):** Поддержка сценариев «из письма Новиковой» (поиск письма -> передача `types.Part.from_function_response` -> формирование `ActionProposal`).

---

### 2. Выполненные работы

#### Задача 08-01-01: Создание модуля `tools_schema.py` и обновление системного промпта секретаря
1. Создан модуль `/opt/assistant-core/src/brain/tools_schema.py`:
   - Объявлен датакласс `ActionProposal(action_type: str, params: dict[str, Any], proposal_text: str = "")`.
   - Описаны 4 декларативные схемы `types.FunctionDeclaration`:
     * `create_calendar_event`: свойства `title`, `date`, `start_time`, `end_time`, `description`, `location`. Обязательные: `["title", "date", "start_time", "end_time"]`.
     * `create_reminder`: свойства `text`, `due_date`, `target`, `category`. Обязательные: `["text", "due_date"]`.
     * `draft_email_reply`: свойства `email_id`, `reply_text`. Обязательные: `["email_id", "reply_text"]`.
     * `search_emails`: свойства `query`, `sender`, `limit`. Обязательные: `["query"]`.
   - Экспортирован контейнер `SECRETARY_TOOLS = [types.Tool(function_declarations=[...])]`.
2. В `/opt/assistant-core/config/prompts/secretary_default.jinja2` добавлен блок:
   - `СТРОЖАЙШИЙ ЗАПРЕТ ГАЛЛЮЦИНАЦИЙ И ПРАВИЛО ИСПОЛНИТЕЛЬНОГО КОНТУРА (D-05, ACT-02)`.
   - Запрет утверждений вроде «Я записал в календарь» — замена на «Я подготовил карточку для внесения в календарь. Пожалуйста, подтвердите действие кнопкой ниже».
   - Запрет подстановки произвольных часов без уточнения у пользователя.
   - Требование предварительного поиска через `search_emails`.
3. Синхронизирован эталонный снимок промпта секретаря в `tests/fixtures/prompts_snapshot/secretary.txt` и `MANIFEST.json`.

#### Задача 08-01-02: Интеграция tools в `SecretaryDialogEngine` и автотесты
1. В `/opt/assistant-core/src/brain/secretary_dialog.py`:
   - Метод `answer_user_message` расширен параметром `return_proposal: bool = False` (с сохранением 100% обратной совместимости со старыми вызовами).
   - В `types.GenerateContentConfig` передаются `tools=SECRETARY_TOOLS`.
   - Реализована диспетчеризация `resp.function_calls`:
     * `search_emails`: выполнение локального поиска через `self.db.search_emails`, NDA-санитизация, возврат `types.Part.from_function_response` и выполнение follow-up вызова к модели.
     * `create_calendar_event`, `create_reminder`, `draft_email_reply`: упаковка в `ActionProposal` без физических мутаций БД/Google Calendar.
     * При отсутствии текста от модели генерируется вежливый текст с реквизитами карточки и призывом подтвердить действие.
     * Текстовая реплика модели сохраняется в `bot_dialog_history`.
2. Создан комплексный файл тестов `/opt/assistant-core/tests/test_secretary_tools.py`:
   - `test_secretary_tools_schema_declarations`: проверка всех сигнатур, свойств и `required` полей.
   - `test_action_proposal_dataclass`: проверка структуры датакласса.
   - `test_calendar_event_action_proposal_interception`: проверка перехвата вызова календаря и формирования `ActionProposal` без физической записи (ACT-01).
   - `test_two_step_search_emails_flow`: проверка двухшагового вызова с поиском письма Новиковой и извлечением параметров дедлайна.
   - `test_antihallucination_prompt_content`: проверка директивы D-05 в скомпилированном системном промпте.
   - `test_missing_time_clarification_no_action_proposal`: проверка возврата уточняющего вопроса при неполных датах без генерации фейковых предложений.
   - `test_return_flags_backward_compatibility`: проверка работы всех комбинаций `return_files` и `return_proposal`.

---

### 3. Результаты верификации

1. **Модульные тесты `test_secretary_tools.py`:**
   ```
   tests/test_secretary_tools.py::test_secretary_tools_schema_declarations PASSED [ 14%]
   tests/test_secretary_tools.py::test_action_proposal_dataclass PASSED     [ 28%]
   tests/test_secretary_tools.py::test_calendar_event_action_proposal_interception PASSED [ 42%]
   tests/test_secretary_tools.py::test_two_step_search_emails_flow PASSED   [ 57%]
   tests/test_secretary_tools.py::test_antihallucination_prompt_content PASSED [ 71%]
   tests/test_secretary_tools.py::test_missing_time_clarification_no_action_proposal PASSED [ 85%]
   tests/test_secretary_tools.py::test_return_flags_backward_compatibility PASSED [100%]
   ========================= 7 passed, 1 warning in 2.03s =========================
   ```

2. **Тесты снимков промптов `test_prompt_snapshot.py`:**
   ```
   ============================== 19 passed in 2.87s ==============================
   ```

3. **Общий Quality Gate (`scripts/gate.py`):**
   ```
   Гейт качества

   Репозиторий     Проверка                               Результат
   chat-app        pytest — тестов: 171                   ✓
   chat-app        import-linter                          ✓
   assistant-core  pytest — тестов: 386                   ✓
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
+ /opt/assistant-core/src/brain/tools_schema.py
+ /opt/assistant-core/tests/test_secretary_tools.py
+ /opt/chat-app/.planning/phases/08-ispolnitelnyy-kontur-tool-calling/08-01-SUMMARY.md
! /opt/assistant-core/config/prompts/secretary_default.jinja2
! /opt/assistant-core/src/brain/secretary_dialog.py
! /opt/assistant-core/tests/fixtures/prompts_snapshot/MANIFEST.json
! /opt/assistant-core/tests/fixtures/prompts_snapshot/secretary.txt
# Статус: Готово к коммиту (Quality Gate: ЗЕЛЁНЫЙ)
```
