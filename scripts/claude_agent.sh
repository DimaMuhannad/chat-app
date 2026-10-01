#!/usr/bin/env bash
set -e

# Claude Code CLI Agent Runner for VPS Environment
# Configured for SpaceCore Ubuntu 24.04 (2GB RAM + 4.5GB Swap)

export NODE_OPTIONS="--max-old-space-size=1536"

# Load ANTHROPIC_API_KEY from .env if present and not already set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    if [ -f "/opt/assistant-core/.env" ]; then
        KEY_VAL=$(grep -E "^ANTHROPIC_API_KEY=" /opt/assistant-core/.env 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        if [ -n "$KEY_VAL" ]; then
            export ANTHROPIC_API_KEY="$KEY_VAL"
        fi
    fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    if [ -f "/opt/chat-app/.env" ]; then
        KEY_VAL=$(grep -E "^ANTHROPIC_API_KEY=" /opt/chat-app/.env 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        if [ -n "$KEY_VAL" ]; then
            export ANTHROPIC_API_KEY="$KEY_VAL"
        fi
    fi
fi

# Load CLAUDE_CODE_OAUTH_TOKEN from .env if present and not already set
if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    if [ -f "/opt/assistant-core/.env" ]; then
        TOKEN_VAL=$(grep -E "^CLAUDE_CODE_OAUTH_TOKEN=" /opt/assistant-core/.env 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        if [ -n "$TOKEN_VAL" ]; then
            export CLAUDE_CODE_OAUTH_TOKEN="$TOKEN_VAL"
        fi
    fi
fi

if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    if [ -f "/opt/chat-app/.env" ]; then
        TOKEN_VAL=$(grep -E "^CLAUDE_CODE_OAUTH_TOKEN=" /opt/chat-app/.env 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        if [ -n "$TOKEN_VAL" ]; then
            export CLAUDE_CODE_OAUTH_TOKEN="$TOKEN_VAL"
        fi
    fi
fi

case "$1" in
    status)
        echo "🔍 Проверка статуса авторизации Claude Code CLI..."
        claude auth status
        ;;
    login)
        echo "🔑 Запуск интерактивной авторизации (OAuth / Claude Subscription)..."
        echo "Если у вас подписка Claude Pro/Max, перейдите по сгенерированной ссылке в браузере,"
        echo "авторизуйтесь и вставьте полученный проверочный код."
        echo "------------------------------------------------------------------"
        claude setup-token
        ;;
    login-console)
        echo "🔑 Авторизация через Anthropic Console..."
        claude auth login --console
        ;;
    review)
        shift
        PROMPT="Проведи ревизию архитектуры текущего проекта согласно указаниям в CLAUDE.md. Составь отчет и план рефакторинга по разделению персональной логики и универсального ядра."
        if [ -n "$*" ]; then
            PROMPT="$*"
        fi
        echo "🚀 Запуск Claude Code в режиме аудита/ревью..."
        claude -p "$PROMPT"
        ;;
    *)
        if [ $# -eq 0 ]; then
            echo "🤖 Claude Code Agent Helper"
            echo "Использование:"
            echo "  $0 status          - проверить статус авторизации"
            echo "  $0 login           - войти по подписке Claude Pro/Max (OAuth)"
            echo "  $0 login-console   - войти через Anthropic Console"
            echo "  $0 review [задача] - запустить пакетный аудит/ревью кодовой базы"
            echo "  $0 [любые опции claude CLI]"
            echo ""
            echo "Текущий статус авторизации:"
            claude auth status
        else
            exec claude "$@"
        fi
        ;;
esac
