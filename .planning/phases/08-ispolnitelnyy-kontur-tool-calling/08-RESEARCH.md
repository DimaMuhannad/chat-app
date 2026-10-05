# Phase 8: Исполнительный инструментальный контур (Tool Calling) - Research & Technical Analysis

**Дата:** 2026-10-05  
**Статус:** Исследование завершено / Готово к планированию  
**Фаза:** 08-ispolnitelnyy-kontur-tool-calling  

---

## 1. Введение и архитектурный контекст

Цель Фазы 8 (`TOOL-ACT`) — полное устранение иллюзии выполнения действий («галлюцинаций») при диалоге с персональным секретарем доцента Попова Д.А. До текущего момента ассистент мог утверждать в тексте ответа, что «событие внесено в календарь» или «напоминание создано», хотя реальных физических записей в окружение не производилось.

Фаза 8 внедряет строгий **исполнительный инструментальный контур** на базе Google GenAI SDK (`types.Tool`, `types.FunctionDeclaration`) с обязательным шлюзом **Human-in-the-Loop (HITL)**:
- Модель не имеет права выполнять деструктивные или изменяющие состояние действия без подтверждения.
- Любой запрос на создание события календаря, локального напоминания или черновика письма трансформируется в интерактивную карточку Telegram с кнопками подтверждения и отмены.
- Физическая запись в Google Calendar API или SQLite происходит исключительно по факту обработки `callback_query`.
- При недоступности Google Calendar API активируется локальный буфер отказоустойчивости (`pending_sync`) с возможностью повторной синхронизации.
- Поиск контекста для планирования (например, даты из переписки с зам. зав. каф. Новиковой Ю.А.) выполняется через двухшаговый Tool Calling.

---

## 2. Технический анализ Google GenAI SDK (`google-genai`)

В проекте используется современный SDK `google-genai` (версия 1.x) и клиент `genai.Client` (`from google import genai; from google.genai import types`).

### 2.1. Объявление декларативных схем инструментов (`types.Tool`)
Инструменты для `SecretaryDialogEngine` описываются через `types.Tool` с перечнем `types.FunctionDeclaration`. Параметры определяются с использованием `types.Schema` и `types.Type`:

```python
from google.genai import types

tool_calendar = types.FunctionDeclaration(
    name="create_calendar_event",
    description="Запланировать событие в Google Calendar владельца. Требует точной даты и времени начала/окончания.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(type=types.Type.STRING, description="Название события или встречи"),
            "date": types.Schema(type=types.Type.STRING, description="Дата в формате YYYY-MM-DD"),
            "start_time": types.Schema(type=types.Type.STRING, description="Время начала в формате HH:MM"),
            "end_time": types.Schema(type=types.Type.STRING, description="Время окончания в формате HH:MM"),
            "description": types.Schema(type=types.Type.STRING, description="Подробное описание или контекст события"),
            "location": types.Schema(type=types.Type.STRING, description="Место проведения или аудитория"),
        },
        required=["title", "date", "start_time", "end_time"],
    ),
)

tool_reminder = types.FunctionDeclaration(
    name="create_reminder",
    description="Создать локальное напоминание или дедлайн в базе данных ассистента.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "text": types.Schema(type=types.Type.STRING, description="Суть напоминания или задачи"),
            "due_date": types.Schema(type=types.Type.STRING, description="Срок выполнения в формате YYYY-MM-DD или YYYY-MM-DD HH:MM"),
            "target": types.Schema(type=types.Type.STRING, description="Связанное лицо, адресат или студент (опционально)"),
            "category": types.Schema(type=types.Type.STRING, description="Категория задачи: academic, corporate, general"),
        },
        required=["text", "due_date"],
    ),
)

tool_draft_reply = types.FunctionDeclaration(
    name="draft_email_reply",
    description="Сформировать проект (черновик) ответа на входящее электронное письмо в почтовой базе.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "email_id": types.Schema(type=types.Type.INTEGER, description="Числовой ID входящего письма в SQLite"),
            "reply_text": types.Schema(type=types.Type.STRING, description="Текст проекта ответа"),
        },
        required=["email_id", "reply_text"],
    ),
)

tool_search_emails = types.FunctionDeclaration(
    name="search_emails",
    description="Найти письма в локальной базе по отправителю, ключевым словам или теме (первый шаг контекстного планирования).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(type=types.Type.STRING, description="Поисковый запрос или ключевые слова"),
            "sender": types.Schema(type=types.Type.STRING, description="Имя или email отправителя (например, 'Новикова')"),
            "limit": types.Schema(type=types.Type.INTEGER, description="Максимальное число возвращаемых писем (по умолчанию 5)"),
        },
        required=["query"],
    ),
)

SECRETARY_TOOLS = [
    types.Tool(function_declarations=[
        tool_calendar,
        tool_reminder,
        tool_draft_reply,
        tool_search_emails,
    ])
]
```

### 2.2. Механизм извлечения и вызова инструментов
При обращении к модели с переданными `tools` в `types.GenerateContentConfig(tools=SECRETARY_TOOLS)`:
1. Если модель решает вызвать инструмент, в объекте ответа `resp.function_calls` возвращается список вызовов `types.FunctionCall` с атрибутами `.name` и `.args`.
2. Если вызов является информационным поиском (`search_emails`), движок исполняет запрос локально через `Database.search_emails`, формирует структуру результатов и возвращает ее модели через `types.Part.from_function_response(name="search_emails", response={"emails": [...]})`.
3. Модель получает результаты первого шага и вторым шагом формирует вызов действия (`create_reminder` / `create_calendar_event`) либо текстовый ответ с цитированием данных.
4. Если модель возвращает action-инструмент (`create_calendar_event`, `create_reminder`, `draft_email_reply`), цикл не выполняет прямую запись в боевые системы! Вместо этого запрос сериализуется в объект отложенного подтверждения (`PendingActionProposal`), генерируется Telegram HITL-карточка, а пользователю выводится предварительный просмотр параметров.

---

## 3. Анализ архитектуры HITL и хранилища SQLite

### 3.1. Использование существующего примитива `assistant_shared.hitl`
В проекте уже присутствует архитектурно выверенная подсистема `assistant_shared.hitl`:
- `ConfirmationStore`: асинхронное сохранение и атомарная смена статусов (`pending` -> `confirmed` / `rejected` / `expired`) в таблице `pending_confirmations`.
- `PendingConfirmation`: модель данных с полями `id`, `persona_id`, `action_type`, `target_id`, `payload`, `status`, `channel`, `expires_at`.
- `resume_action(confirmation_id, store, confirmed_by)`: атомарное подтверждение с поиском зарегистрированного обработчика в реестре `_ACTION_HANDLERS`.

Для Фазы 8 регистрируются целевые обработчики действий:
1. `action_type = "create_calendar_event"` -> вызов `GoogleCalendarClient.create_event(...)` с записью в `calendar_sync_records`. При сетевом сбое — сохранение со статусом `pending_sync`.
2. `action_type = "create_reminder"` -> вызов `Database.create_reminder(...)`.
3. `action_type = "draft_email_reply"` -> вызов `Database.create_email_draft(...)`.

### 3.2. Буфер отказоустойчивости `pending_sync` (D-04)
При подтверждении карточки создания события в Google Calendar возможны сетевые ошибки, недоступность хоста или истечение OAuth токена.
- В таблице `calendar_sync_records` столбец `status` принимает значения:
  - `'active'` — успешно синхронизировано с Google Calendar (`google_event_id` заполнен).
  - `'pending_sync'` — сохранено локально в SQLite при недоступности Google API. `google_event_id` имеет вид `pending_local_<uuid>`.
  - `'failed'` — ошибка валидации данных.
- Метод `Database.record_calendar_sync(...)` поддерживает сохранение статуса `pending_sync`.
- При возникновении ошибки ассистент отправляет пользователю уведомление:
  «⚠️ Google Calendar временно недоступен. Событие сохранено в локальный буфер ожидания (`pending_sync`).»
  с инлайн-кнопкой `[🔄 Повторить синхронизацию]`, привязанной к callback `cal:retry_sync:<sync_id>`.

---

## 4. Механика взаимодействия в Telegram (`bot_handler.py`)

### 4.1. Визуальный формат HITL-карточки подтверждения (D-01, ACT-03)
Перед физической фиксацией события формируется сообщение с четким отображением параметров:
```markdown
📅 **Подтверждение записи в Google Calendar**

• **Событие:** Консультация по физике (гр. 1632)
• **Дата:** Пятница, 10 октября 2026 г.
• **Время:** 18:30 — 20:00 (Europe/Moscow)
• **Аудитория:** Ауд. 13-05
• **Описание:** Разбор типового расчета по электродинамике

Внести данное событие в ваш Google Calendar?
```
Инлайн-клавиатура:
- `[✅ Записать в Google Calendar]` -> `callback_data="hitl:act:conf:<conf_id>"`
- `[❌ Отмена]` -> `callback_data="hitl:act:rej:<conf_id>"`

Для напоминаний:
```markdown
⏰ **Подтверждение создания напоминания**

• **Суть:** Проверить отчеты Новиковой к ученому совету
• **Дедлайн:** 14 октября 2026 г., 12:00
• **Категория:** `academic`

Зафиксировать напоминание в списке задач?
```
Инлайн-клавиатура:
- `[⏰ Создать напоминание]` -> `callback_data="hitl:act:conf:<conf_id>"`
- `[❌ Отмена]` -> `callback_data="hitl:act:rej:<conf_id>"`

### 4.2. Защита от повторных нажатий (Idempotency Guard)
- По нажатию кнопки бот проверяет статус в `ConfirmationStore`. Если статус уже `confirmed` или `rejected`, бот отправляет `callback.answer("Действие уже выполнено", show_alert=False)`.
- Сообщение немедленно редактируется: удаляется клавиатура, а в заголовок подставляется статус:
  «✅ **Событие успешно добавлено в Google Calendar**» или «❌ **Создание события отменено**».

---

## 5. Обработка неполных данных и двухшаговый Tool Calling (D-02, D-03)

### 5.1. Уточняющий диалог при отсутствии точного времени (D-03)
Если пользователь пишет: *«Запланируй встречу с зав. каф. в четверг»*, время не указано.
- Запрещено выставлять дефолт (например, 09:00 или 00:00).
- Схема `create_calendar_event` требует обязательных полей `start_time` и `end_time`.
- Модель, руководствуясь антигаллюцинационным системным промптом, возвращает пользователю естественный вопрос:
  *«В какое время запланировать встречу в четверг?»*.
- Диалог сохраняется в `bot_dialog_history`, и следующий ответ пользователя (*«В 14:30 на час»*) объединяется с контекстом для вызова инструмента.

### 5.2. Сценарий «из письма Новиковой» (D-02)
Пример запроса: *«Поставь напоминание о дедлайне из последнего письма Новиковой»*.
1. Шаг 1: `SecretaryDialogEngine` распознает необходимость поиска и вызывает `search_emails(query="дедлайн", sender="Новикова")`.
2. Движок выполняет `Database.search_emails`, находит письмо (например, от `novikova@guap.ru`, тема *«Сроки сдачи отчетов по эффективному контракту до 15.10 18:00»*).
3. Движок отдает результат в модель в формате `function_response`.
4. Шаг 2: Модель читает текст письма, извлекает точную дату (15.10.2026, 18:00) и формирует вызов `create_reminder(text="Сдача отчетов по эффективному контракту", due_date="2026-10-15 18:00", category="academic")`.
5. Движок перехватывает action-вызов и формирует Telegram HITL-карточку для подтверждения пользователем.

---

## 6. Маршрутизация интентов планирования (`FastIntentRouter`, ACT-04)

В `src/brain/intent_router.py`:
- Расширение множества `VALID_ACTIONS`:
  `{"timesheet", "evening", "emails", "lms_tasks", "lms_reports", "methodist", "clear_dialog", "ticker", "secretary", "calendar_schedule", "create_reminder", "draft_reply"}`
- Обновление системного промпта `config/prompts/intent_router_default.jinja2` с четкими примерами для каждого нового интента:
  - `calendar_schedule`: «запиши в календарь на пятницу в 15:00 пару», «добавь в расписание встречу с деканом завтра в 11».
  - `create_reminder`: «напомни мне в понедельник позвонить в отдел кадров», «поставь дедлайн по статье на 20 октября».
  - `draft_reply`: «ответь на письмо Новиковой что отчет готов», «составь черновик ответа старосте».
- В `bot_handler.py`: при определении этих интентов управление передается в целевые обработчики с извлечением параметров через инструментальный контур `SecretaryDialogEngine`.

---

## 7. Антигаллюцинационный системный промпт (D-05, ACT-02)

В системный промпт `config/prompts/secretary_default.jinja2` внедряется жесткая нормативная директива:

```jinja2
СТРОЖАЙШИЙ ЗАПРЕТ ГАЛЛЮЦИНАЦИЙ И ПРАВИЛО ИСПОЛНИТЕЛЬНОГО КОНТУРА:
1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО утверждать, заявлять или создавать иллюзию, что событие внесено в календарь, создано напоминание или подготовлен черновик, если в текущем диалоге не был вызван соответствующий инструмент и не сформирована карточка подтверждения!
2. Никогда не пиши: «Я записал встречу в календарь» или «Напоминание установлено». Пиши: «Я подготовил карточку для внесения в календарь. Пожалуйста, подтвердите действие кнопкой ниже».
3. Если пользователь не указал конкретное время события (например, сказал только «в пятницу» или «завтра»), КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО придумывать время или подставлять произвольные часы. Задай короткий уточняющий вопрос: «В какое время запланировать встречу?».
4. Если пользователь просит взять данные из письма или переписки («из письма Новиковой»), обязательно сначала воспользуйся инструментом search_emails для получения фактического текста письма, и только после этого формулируй параметры действия.
```

---

## 8. Архитектурный комплаенс и Quality Gate

Все компоненты фазы подчиняются строгим правилам:
- `scripts/gate.py`: 100% pass обоих наборов тестов (`chat-app` и `assistant-core`), 0 broken imports в `import-linter`, чистый статус `security_shield.py` (GREEN).
- Неизменность боевой `assistant.db` во время прогона тестов (использование изолированных временных копий или `:memory:`).
- Соблюдение Memory Budget на VPS (2 GB RAM, Node 20 `NODE_OPTIONS="--max-old-space-size=1536"`).
- Все пользовательские сообщения и системные плашки формируются строго на русском языке.
