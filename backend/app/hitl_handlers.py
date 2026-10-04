"""Обработчики подтвержденных деструктивных действий (HITL) для chat-app."""

import logging
from assistant_shared.hitl import PendingConfirmation, register_action_handler
from app.db import DatabaseService

logger = logging.getLogger(__name__)


async def handle_delete_project(confirmation: PendingConfirmation) -> bool:
    target = confirmation.target_id or confirmation.payload.get("project_id")
    if target is None:
        raise ValueError("Target project ID is missing")
    project_id = int(target)
    logger.info("HITL: Выполнение фактического удаления проекта #%s", project_id)
    return await DatabaseService.delete_project(project_id)


async def handle_delete_document(confirmation: PendingConfirmation) -> bool:
    target = confirmation.target_id or confirmation.payload.get("doc_id")
    if target is None:
        raise ValueError("Target document ID is missing")
    doc_id = int(target)
    logger.info("HITL: Выполнение фактического удаления документа #%s", doc_id)
    return await DatabaseService.delete_document(doc_id)


async def handle_delete_task(confirmation: PendingConfirmation) -> bool:
    target = confirmation.target_id or confirmation.payload.get("task_id")
    if target is None:
        raise ValueError("Target task ID is missing")
    task_id = int(target)
    logger.info("HITL: Выполнение фактического удаления задачи #%s", task_id)
    return await DatabaseService.delete_task(task_id)


async def handle_delete_reminder(confirmation: PendingConfirmation) -> bool:
    target = confirmation.target_id or confirmation.payload.get("reminder_id")
    if target is None:
        raise ValueError("Target reminder ID is missing")
    reminder_id = int(target)
    logger.info("HITL: Выполнение фактического удаления напоминания #%s", reminder_id)
    return await DatabaseService.delete_reminder(reminder_id)


def register_chat_app_hitl_handlers() -> None:
    """Регистрирует обработчики деструктивных действий chat-app в assistant_shared.hitl."""
    register_action_handler("delete_project", handle_delete_project)
    register_action_handler("delete_document", handle_delete_document)
    register_action_handler("delete_task", handle_delete_task)
    register_action_handler("delete_reminder", handle_delete_reminder)


# Автоматическая регистрация при импорте модуля
register_chat_app_hitl_handlers()
