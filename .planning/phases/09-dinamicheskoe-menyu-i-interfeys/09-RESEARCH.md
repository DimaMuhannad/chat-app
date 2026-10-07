# Phase 9: Динамическое меню и интерфейс Telegram-бота, декларативные алиасы и аудит эргономики - Research

**Date:** 2026-10-07
**Status:** Completed
**Author:** AI Lead Architect / GSD Planner

---

## 1. Технический анализ Telegram Bot API: Меню команд и ограничения

### 1.1. Ограничения Telegram Bot API на `BotCommand`
В соответствии с официальной документацией Telegram Bot API и спецификацией `aiogram 3.x`:
1. **Синтаксис имени команды:**
   - Поле `command` в объекте `BotCommand` должно содержать от 1 до 32 символов.
   - Допустимы **только** строчные латинские буквы (`a-z`), цифры (`0-9`) и знак подчеркивания (`_`). Регулярное выражение: `^[a-z0-9_]{1,32}$`.
   - **Кириллица в `BotCommand.command` категорически запрещена API Telegram:** вызов `bot.set_my_commands([BotCommand(command="часы", description="...")])` приведет к ошибке `TelegramBadRequest: Bad Request: invalid command name`.
2. **Архитектурное решение для русскоязычных алиасов (KISS):**
   - В официальном системном меню Telegram (`set_my_commands`) регистрируются латинские слаги (например, `timesheet`, `today`, `emails`, `lms`, `methodist`, `evening`, `ticker`, `help`), но с подробными русскоязычными описаниями и эмодзи.
   - Русскоязычные алиасы (например, `/часы`, `/табель`, `/пары`, `/отчеты`, а также свободный ввод текста `часы`, `табель`, `пары`) обрабатываются на уровне приложения:
     * Быстрый роутер `FastIntentRouter` и `bot_handler.py` перехватывают русскоязычные команды до обращения к LLM.
     * Пользователь может настроить и активировать любой латинский алиас для меню (например, `/hours` вместо `/timesheet`), а для текста — любые кириллические псевдонимы.
3. **Области видимости команд (Scopes):**
   - `BotCommandScopeDefault()`: базовое меню для всех диалогов.
   - `BotCommandScopeChat(chat_id=...)`: персональное меню для конкретного чата владельца, позволяющее динамически скрывать/отображать команды персонально.

---

## 2. Анализ текущей реализации в кодовой базе

### 2.1. Регистрация команд (`bot_handler.py:645`)
Сейчас в коде жестко зашит статический список:
```python
async def setup_bot_commands(self) -> None:
    commands = [
        BotCommand(command="ticker", description="⚡ Живое табло в закрепе (HUD)"),
        BotCommand(command="timesheet", description=f"⏱️ Часы и норма {c_name}"),
        BotCommand(command="today", description=f"📅 Расписание пар {u_name}"),
        BotCommand(command="lms", description=f"🎓 Отчеты и задания {lms_name}"),
        BotCommand(command="emails", description="📬 Входящая почта и черновики"),
        BotCommand(command="methodist", description="📚 Вопрос методисту кафедры"),
        BotCommand(command="evening", description="🌙 Вечерний дайджест"),
        BotCommand(command="undo_clear", description="↩️ Восстановить память диалога"),
        BotCommand(command="help", description="❓ Справка по всем возможностям"),
    ]
    await self.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
```
**Проблемы текущей схемы:**
1. Список статичен и не реагирует на включение/отключение коннекторов.
2. Нет разбивки по категориям (Академические, Табель, Почта, Система).
3. Пользователь не может скрыть команду или добавить синоним без правки кода Python.

### 2.2. Роутинг в `bot_handler.py` и `FastIntentRouter`
В `bot_handler.py` обработчики команд привязаны через декораторы:
```python
self.router.message(Command("timesheet", "tydex", "hours"))(self.handle_cmd_timesheet)
self.router.message(Command("today", "schedule"))(self.handle_cmd_today)
```
В `FastIntentRouter` жестко зашиты наборы `timesheet_cmds`, `cal_phrases` и т.д.
При внедрении `CommandRegistry`:
- `CommandRegistry` становится единым источником правды для зарегистрированных команд и синонимов.
- `FastIntentRouter` опрашивает `CommandRegistry` для мгновенного сопоставления алиаса с каноническим действием (< 5 мс).

---

## 3. Проектирование модульного CommandRegistry

### 3.1. Структура `CommandRegistry` (`src/notifier/commands.py`)
```python
@dataclass
class CommandSpec:
    name: str  # Латинский слаг для Telegram (например, "timesheet")
    description: str  # Описание в меню
    category: str  # "academic", "timesheet", "mail", "system"
    connector_id: str | None  # Привязка к коннектору (например, "timesheet")
    default_aliases: list[str]  # ["часы", "табель", "выработка", "hours"]
    is_enabled: bool = True
    handler_action: str = ""  # Имя действия для роутера
```

### 3.2. Схема хранения переопределений в SQLite
Для персистентности настроек пользователя создаются таблицы:
```sql
CREATE TABLE IF NOT EXISTS bot_command_settings (
    command_name TEXT PRIMARY KEY,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    custom_description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_custom_aliases (
    alias TEXT PRIMARY KEY,
    canonical_command TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Контекстно-ориентированные Reply-клавиатуры (Quick Replies)

### 4.1. Telegram `ReplyKeyboardMarkup`
В `aiogram 3.x`:
```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def build_context_reply_keyboard(hour_msk: int) -> ReplyKeyboardMarkup:
    # 07:00 - 12:00: Утро
    # 12:00 - 19:00: День / Работа
    # 19:00 - 23:00: Вечер
```
- Кнопка `[⌨️ Скрыть]` отправляет сообщение, по которому бот вызывает `ReplyKeyboardRemove()`.
- Команда `/menu` восстанавливает клавиатуру текущего временного слота.
- Текст на кнопках (например, `[📅 Расписание пар]`) перехватывается `FastIntentRouter` и мапится на соответствующий интент без обращения к LLM.

---

## 5. Системный аудит эргономики и Edge Caching

### 5.1. Кэширование с ультранизкой латентностью (< 250 мс)
- **Сегодняшнее расписание:** данные меняются редко в течение дня. Кэширование на 15 минут в памяти процесса с инвалидацией при ручном обновлении дает отклик < 50 мс вместо повторного запроса к БД/парсеру.
- **Табель:** расчет баланса часов кэшируется на 30 минут (< 50 мс).

### 5.2. Сбор обратной связи (👍 / 👎)
Под подробными ответами секретаря прикрепляется инлайн-клавиатура:
```python
InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="👍 Полезно", callback_data=f"fb:up:{msg_id}"),
    InlineKeyboardButton(text="👎 Неточно", callback_data=f"fb:down:{msg_id}")
]])
```
Таблица в SQLite:
```sql
CREATE TABLE IF NOT EXISTS dialog_feedback_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    feedback_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.3. Проактивные алерты
При сетевых сбоях IMAP или истечении куки LMS отправляется компактная карточка с кнопкой `[🔄 Проверить подключение]`, предотвращая тихие сбои.

---

## 6. План декомпозиции на атомарные задачи (MECE Decomposition)

1. **План 09-01 (Wave 1):** Модульный `CommandRegistry`, таблицы настроек в SQLite и динамическая регистрация `bot.set_my_commands()`.
2. **План 09-02 (Wave 2):** Декларативные алиасы, быстрый перехват в `FastIntentRouter` и диалоговое управление меню из чата.
3. **План 09-03 (Wave 3):** Контекстно-ориентированные Reply-клавиатуры по времени суток (MSK) и управление режимом отображения (`/menu`, скрытие).
4. **План 09-04 (Wave 4):** Edge Caching (< 250 мс), телеметрия обратной связи (👍/👎), проактивные алерты коннекторов и сквозные интеграционные тесты Quality Gate.
