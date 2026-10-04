# Phase 06: Готовность к мультитенантности - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-04
**Phase:** 6-Готовность к мультитенантности
**Areas discussed:** Изоляция ключей Gemini (ISO-01), NDA Air-Gap для входящей почты (ISO-02), Zero-Trust Scopes коннекторов (ISO-03), Ликвидация остаточного хардкода (FIN-01)

---

## Изоляция ключей Gemini (ISO-01)

| Option | Description | Selected |
|--------|-------------|----------|
| ContextVar + фабрика `get_key_rotator(persona_id)` | Прозрачная изоляция на уровне асинхронного контекста запроса без ломки существующих конструкторов | ✓ |
| Явный Dependency Injection | Обязательный проброс экземпляра `GeminiKeyRotator` в конструкторы `SecretaryDialog`, `IntentRouter`, `Methodist` | |
| Словарь пулов ротаторов внутри синглтона | Хранение пулов по `persona_id` с резолвом через `current_persona()` | |

**User's choice:** ContextVar + фабрика `get_key_rotator(persona_id)`
**Notes:** Полностью удаляется строка `config.GEMINI_API_KEY = active_key`. Запись в `.env` сохраняется только при явной передаче аргумента `env_path` (для совместимости с `test_key_rotator.py`), в боевом рантайме отключена. Пул ключей берется из `persona.gemini_keys` с fallback на системные переменные.

---

## NDA Air-Gap для входящей почты (ISO-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Декларативно через конфигурацию персоны | Сопоставление email-аккаунта (`account_id`) или доменов с `workspace_id` (`clearance=restricted_nda`) | ✓ |
| По домену почтового адреса | Сопоставление только по `@tydex.ru -> restricted_nda` из правил безопасности | |
| Добавить колонку `workspace_id / clearance` в `email_messages` | Заполнять при сборе почты в `EmailCollector` | |

**User's choice:** Декларативно через конфигурацию персоны
**Notes:** Для писем из `restricted_nda` в контекст LLM (`SecretaryDialog`, `Summarizer`) передаются только обезличенные метаданные (Отправитель, Тема, Дата с пометкой `[NDA: тело и вложения скрыты Air-Gap]`), поля `body` и вложения полностью вырезаются. Вызовы автоответа `ReplyGenerator` блокируются с ошибкой `AirGapViolationError`. В тестах используется Mock/Spy клиент с assert на отсутствие утечек.

---

## Zero-Trust Scopes коннекторов (ISO-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Атрибут класса `required_scopes: ClassVar[tuple[str, ...]]` | В базовых портах/коннекторах (`BaseLmsClient`, `BaseTimesheetProvider` и т.д.) | ✓ |
| Декоратор `@requires_scope('...')` | Над методами коннектора с проверкой скоупов перед каждым вызовом | |
| Внешний реестр разрешений в `assistant_shared` | Словарь сопоставления ролей коннекторов и необходимых скоупов | |

**User's choice:** Атрибут класса `required_scopes: ClassVar[tuple[str, ...]]`
**Notes:** Проверка скоупов выполняется в фабрике композиции `src/composition.py`: если `binding.scopes` персоны не покрывают `required_scopes`, выбрасывается `MissingScopeError` (fail-fast). Если привязка отсутствует, коннектор не создается. Изоляция кредов LMS в `chat-app` проверяется тестом `backend/tests/test_credentials_isolation.py`.

---

## Ликвидация остаточного хардкода (FIN-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Динамическая подстановка из `current_persona()` | `ui.texts` для названий организаций/предметов, `workspaces` для проектов, `persona.name` для обращений | ✓ |
| Вынести все текстовые константы в словарь `assistant_shared.i18n` | Глобальный словарь переводов | |

**User's choice:** Динамическая подстановка из `current_persona()`
**Notes:** Скрипты в `scripts/` параметризуются через аргументы CLI (`argparse`) или считывают `current_persona()`. Исторический отчет `reconcile_report.json` перемещается в `docs/baseline/` (или удаляется). Работа разбивается на 2 этапа: ядро `src/` (с контролем сохранения поведения) и `scripts/` (с обнулением `HARDCODE_BASELINE = {}`).

---

## Claude's Discretion

- Точные имена исключений (`AirGapViolationError`, `MissingScopeError`).
- Вспомогательные хелперы маскирования текста письма `mask_nda_email_body()`.
- Конкретная структура тестового шпиона `SpyGenAIClient` в фикстурах pytest.

## Deferred Ideas

Нет (все рассмотренные вопросы вошли в состав Фазы 6).
