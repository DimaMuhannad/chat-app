#!/usr/bin/env bash
set -e

export NODE_OPTIONS="--max-old-space-size=1536"
TOKEN_VAL=$(grep -E "^CLAUDE_CODE_OAUTH_TOKEN=" /opt/assistant-core/.env 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
if [ -n "$TOKEN_VAL" ]; then
    export CLAUDE_CODE_OAUTH_TOKEN="$TOKEN_VAL"
fi

WORKTREE_DIR="/opt/chat-app/.claude/worktrees/daedalus"
cd "$WORKTREE_DIR"

PROMPT=$(cat << 'PROMPT_EOF'
Ты — Daedalus, ведущий AI-архитектор реорганизации платформы Antigravity Studio & Assistant Core.

Твоя миссия: провести глубокую ревизию, код-ревью и реорганизацию кодовой базы двух взаимосвязанных репозиториев (/opt/chat-app и /opt/assistant-core), чтобы трансформировать проект из узкоспециализированного персонального ассистента в открытую, универсальную платформу общего назначения (General-Purpose / White-Label AI Agent & Studio Platform), пригодную для любого пользователя.

ЭТАП 1: МЕТА-ПРОМПТ И САМОРАСШИРЕНИЕ
1. Внимательно изучи текущий проект и файл CLAUDE.md.
2. Критически переосмысли и дополни этот промпт: расширь архитектурные критерии, выдели неочевидные риски, примени принципы Hexagonal Architecture (Ports and Adapters), Clean Architecture, Domain-Driven Design (DDD), Event-Driven Architecture и Zero-Trust Security. Зафиксируй расширенное ТЗ в начале своего отчета.

ЭТАП 2: КОД-РЕВЬЮ И АУДИТ ТЕКУЩЕЙ АРХИТЕКТУРЫ
Запусти глубокое ревью обеих кодовых баз (/opt/chat-app и /opt/assistant-core):
- Выяви все точки жесткой привязки (hardcoded coupling) к исходной персоне пользователя, академическим интеграциям (расписание, личный кабинет, LMS) и корпоративным табелям (ААДХк, отчеты).
- Оцени архитектурный долг, связность модулей (coupling) и зацепление (cohesion).
- Проверь безопасность: защита от утечек секретов, изоляция контуров (NDA air-gap), сохранение шлюзов подтверждения деструктивных действий (Human-in-the-Loop).

ЭТАП 3: АНАЛИЗ МИРОВЫХ АНАЛОГОВ И КОНКУРЕНТОВ
Используй интернет-поиск и изучи ведущие открытые и коммерческие агентные платформы:
- OpenHands (All-Hands AI / OpenDevin) — архитектура runtime, sandboxing, event streams.
- AutoGen (Microsoft) и Semantic Kernel — плагины, скиллы, multi-agent conversation patterns.
- CrewAI — ролевая модель, иерархия и делегирование задач.
- LangGraph — state machines, checkpoints, сохранение контекста диалогов и HITL.
- Cursor / Windsurf / Antigravity IDE — паттерны UX для агентных студий, стриминг рассуждений (thinking), diff-viewer и артефакты.
Сравни их подходы с нашей структурой и отбери лучшие практики для универсализации нашего ядра.

ЭТАП 4: ФИНАЛЬНЫЙ АРХИТЕКТУРНЫЙ МАНИФЕСТ И ПЛАН
Создай подробный документ docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md:
1. Архитектурная диаграмма целевого состояния (Core Platform vs Persona Plugins vs Studio UI).
2. Спецификация универсальных интерфейсов (BaseConnector, BaseScheduleProvider, BaseTimesheetProvider, BaseLMSProvider).
3. Спецификация конфигурации персоны (persona.yaml) и схемы хранения настроек в SQLite.
4. Пошаговый план миграции (Roadmap с изолированными этапами, оценкой рисков и критериями приемки Definition of Done).
5. Гарантии обратной совместимости: существующий профиль по умолчанию должен быть оформлен в виде плагина по умолчанию (Default Academic/Industrial Plugin) с сохранением 100% прохождения тестов (pytest).
PROMPT_EOF
)

echo "=== Запуск Daedalus (Claude Sonnet 5, Effort: Max, Mode: Auto) ==="
echo "Рабочая директория: $WORKTREE_DIR"
echo "Лог-файл: /opt/chat-app/logs/daedalus.log"

claude -p "$PROMPT" \
  --effort max \
  --permission-mode auto \
  2>&1 | tee /opt/chat-app/logs/daedalus.log

echo "=== Daedalus завершил работу ==="
