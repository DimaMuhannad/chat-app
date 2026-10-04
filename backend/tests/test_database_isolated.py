"""Интеграционный тест полной изоляции базы данных chat-app от assistant-core (DAT-04, D-10)."""

from pathlib import Path
import pytest

from app.core.config import settings
from app.db import DatabaseService


@pytest.mark.anyio
async def test_database_is_isolated_from_assistant_core():
    """Проверяет, что текущая БД тестов изолирована и не указывает на assistant-core."""
    db_path = Path(settings.SQLITE_DB_PATH).resolve()
    assert "/opt/assistant-core" not in str(db_path), f"БД указывает на assistant-core: {db_path}"
    assert db_path.is_file(), f"Файл тестовой БД не существует: {db_path}"


@pytest.mark.anyio
async def test_isolated_db_has_seeded_entities():
    """Проверяет, что изолированная БД содержит все необходимые сущности без вызова seed-CLI."""
    # 1. Персона
    persona = await DatabaseService.get_persona(settings.PERSONA_ID)
    assert persona is not None
    assert persona["id"] == settings.PERSONA_ID
    assert "workspaces" in persona["config"]
    assert len(persona["config"]["workspaces"]) == 4

    # 2. Рабочие пространства
    workspaces = await DatabaseService.list_workspaces(settings.PERSONA_ID)
    assert len(workspaces) == 4
    clearances = {w["clearance"] for w in workspaces}
    assert "public" in clearances
    assert "restricted_nda" in clearances

    # 3. Базовые прикладные сущности
    projects = await DatabaseService.list_projects()
    assert len(projects) >= 1

    tasks = await DatabaseService.list_tasks()
    assert len(tasks) >= 1

    reminders = await DatabaseService.list_reminders()
    assert len(reminders) >= 1

    documents = await DatabaseService.list_documents()
    assert len(documents) >= 1


@pytest.mark.anyio
async def test_isolated_db_crud_operations():
    """Проверяет работоспособность CRUD-операций в изолированной БД."""
    default_area = await DatabaseService.resolve_default_area()
    assert default_area == "ГУАП"

    # Создание и удаление задачи
    task = await DatabaseService.create_task({
        "title": "Изолированная проверочная задача",
        "area": default_area,
        "priority": "P2",
    })
    assert task["id"] is not None
    assert task["title"] == "Изолированная проверочная задача"

    deleted = await DatabaseService.delete_task(task["id"])
    assert deleted is True
