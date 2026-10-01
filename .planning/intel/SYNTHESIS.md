# Сводка синтеза — SYNTHESIS.md

Единая точка входа для `gsd-roadmapper`. Режим: new. Дата синтеза: 2026-10-01.

## Документы
- Всего: 4 (SPEC: 2, DOC: 2, ADR: 0, PRD: 0, UNKNOWN: 0)
- SPEC: `docs/UNIVERSAL_ARCHITECTURE_BLUEPRINT.md` (precedence 0), `docs/MULTI_PROJECT_ORCHESTRATION_AND_SECURITY.md` (precedence 1)
- DOC: `docs/USER_PROFILE.md` (precedence 2), `docs/TYDEX_COMPANY_PROFILE.md` (precedence 3)
- Граф ссылок: циклов нет.

## Цель проекта (из blueprint и CLAUDE.md)
Универсализация: превратить платформу, заточенную под одного пользователя, в white-label, плагинную платформу (Antigravity Studio + Assistant Core) за 6 фаз миграции. Дефолтная персона `popov-da-default` сохраняет текущее поведение 1:1.

## Решения (decisions.md)
- Locked: 0. ADR в наборе отсутствуют.

## Требования (requirements.md) — 7
- REQ-phase0-safety-net (риск низкий)
- REQ-phase1-ports-extraction (риск средний)
- REQ-phase2-persona-config (риск средний-высокий)
- REQ-phase3-eventbus-db-decoupling (риск самый высокий, зависит от открытого вопроса о стратегии БД)
- REQ-phase4-zero-trust-hitl (риск средний)
- REQ-phase5-multitenancy-readiness (риск средний)
- REQ-default-persona-backward-compat (сквозное)

## Ограничения (constraints.md) — 21
- nfr: 12; schema: 3; api-contract: 3; protocol: 3
- Жёсткие ограничения CLAUDE.md: 100% pytest на каждом шаге; HITL для деструктивных действий; air-gap для корпоративных/NDA workspace; async-first I/O; KISS/YAGNI; пользовательский текст строго на русском.
- Четыре записи из MULTI помечены "частично оспорено" (security shield, security tile, git/SSH-изоляция, Notion).

## Контекст (context.md) — 9 тем
Назначение и персона, учёт времени, учебный процесс/LMS, каналы связи и изоляция NDA-почты, интервьюирование, справка о компании, индустриальные паттерны, открытые вопросы, указатель на CONCERNS.md.

## Конфликты
- Блокирующих: 0
- Конкурирующих вариантов и требующих решения пользователя (WARNINGS): 10
- Информационных (INFO): 8
- Подробности: `/opt/chat-app/.planning/INGEST-CONFLICTS.md`

## Что нужно решить пользователю до маршрутизации
Аккаунты против workspace; 4 проекта против 2 workspace в дефолтной персоне; правила NDA в данных; 2 против 3 уровней допуска; судьба автономного security_shield.py; раскладка каталогов; место Notion-рельсов; источник расписания; стратегия развязки БД (Фаза 3); нужен ли golden-набор промптов (Фаза 2).

## Файлы intel
- `/opt/chat-app/.planning/intel/decisions.md`
- `/opt/chat-app/.planning/intel/requirements.md`
- `/opt/chat-app/.planning/intel/constraints.md`
- `/opt/chat-app/.planning/intel/context.md`
- `/opt/chat-app/.planning/INGEST-CONFLICTS.md`
