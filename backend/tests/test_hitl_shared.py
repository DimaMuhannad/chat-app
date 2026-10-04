"""Тесты общего примитива assistant_shared.hitl и миграции 0002 (HIT-01)."""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

from assistant_shared.db.migrator import run_migrations
from assistant_shared.hitl import (
    ConfirmationChannel,
    ConfirmationStatus,
    ConfirmationStore,
    PendingConfirmation,
    register_action_handler,
    resume_action,
    confirm_pending_action,
    reject_pending_action,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> str:
    db_file = str(tmp_path / "test_hitl.db")
    # Применяем миграции 0001 и 0002
    run_migrations(db_file)
    return db_file


def test_migration_0002(temp_db: str):
    """Проверяет корректность создания таблицы pending_confirmations миграцией 0002."""
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_confirmations'")
        assert cursor.fetchone() is not None

        # Проверяем колонки
        cursor.execute("PRAGMA table_info(pending_confirmations)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "id", "persona_id", "action_type", "target_id", "payload",
            "status", "channel", "created_at", "expires_at", "confirmed_by", "confirmed_at"
        }
        assert expected.issubset(columns)

        # Проверяем индексы
        cursor.execute("PRAGMA index_list(pending_confirmations)")
        indexes = {row[1] for row in cursor.fetchall()}
        assert "idx_pending_confirmations_persona" in indexes
        assert "idx_pending_confirmations_status" in indexes
        assert "idx_pending_confirmations_expires" in indexes


@pytest.mark.anyio
async def test_confirmation_store_crud(temp_db: str):
    """Проверяет создание, чтение и листинг запросов в ConfirmationStore."""
    store = ConfirmationStore(temp_db)
    item = await store.create_confirmation(
        persona_id="default_academic",
        action_type="delete_task",
        target_id="101",
        payload={"title": "Тестовая задача", "project_id": 5},
        channel=ConfirmationChannel.WEB,
        ttl_minutes=10,
    )

    assert item.id is not None
    assert item.status == ConfirmationStatus.PENDING
    assert item.channel == ConfirmationChannel.WEB
    assert item.target_id == "101"
    assert item.payload["title"] == "Тестовая задача"

    # Получение по id
    fetched = await store.get_confirmation(item.id)
    assert fetched is not None
    assert fetched.id == item.id
    assert fetched.status == ConfirmationStatus.PENDING

    # Листинг pending
    pending_list = await store.list_pending("default_academic")
    assert len(pending_list) == 1
    assert pending_list[0].id == item.id


@pytest.mark.anyio
async def test_confirmation_ttl_expiration(temp_db: str):
    """Проверяет логику истечения времени жизни запроса (TTL)."""
    store = ConfirmationStore(temp_db)
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(minutes=5)).isoformat()

    # Вручную создаем просроченный запрос
    item = await store.create_confirmation(
        persona_id="default_academic",
        action_type="delete_project",
        target_id="1",
        ttl_minutes=10,
    )
    with sqlite3.connect(temp_db) as conn:
        conn.execute("UPDATE pending_confirmations SET expires_at = ? WHERE id = ?", (expired_time, item.id))

    # При чтении статус должен автоматически перейти в expired
    fetched = await store.get_confirmation(item.id)
    assert fetched is not None
    assert fetched.status == ConfirmationStatus.EXPIRED

    # Попытка подтверждения просроченного запроса возвращает None
    confirmed = await store.confirm_action(item.id, confirmed_by="owner")
    assert confirmed is None


@pytest.mark.anyio
async def test_resume_action_atomic_and_idempotent(temp_db: str):
    """Проверяет атомарное и ровно однократное выполнение действия через resume_action."""
    store = ConfirmationStore(temp_db)
    executed_count = 0

    async def mock_delete_handler(conf: PendingConfirmation):
        nonlocal executed_count
        executed_count += 1
        return {"deleted_id": conf.target_id, "count": executed_count}

    register_action_handler("test_action_delete", mock_delete_handler)

    item = await store.create_confirmation(
        persona_id="default_academic",
        action_type="test_action_delete",
        target_id="42",
        channel=ConfirmationChannel.TELEGRAM,
    )

    # Первое подтверждение должно успешно вызвать обработчик
    result = await resume_action(item.id, store, confirmed_by="1234567")
    assert result == {"deleted_id": "42", "count": 1}
    assert executed_count == 1

    # Проверяем состояние в БД
    updated = await store.get_confirmation(item.id)
    assert updated.status == ConfirmationStatus.CONFIRMED
    assert updated.confirmed_by == "1234567"
    assert updated.confirmed_at is not None

    # Повторная попытка возобновления должна выбросить ошибку и НЕ вызывать обработчик повторно
    with pytest.raises(ValueError, match="cannot be resumed"):
        await resume_action(item.id, store, confirmed_by="1234567")

    assert executed_count == 1


@pytest.mark.anyio
async def test_reject_action(temp_db: str):
    """Проверяет корректность отклонения действия."""
    store = ConfirmationStore(temp_db)
    item = await store.create_confirmation(
        persona_id="default_academic",
        action_type="delete_document",
        target_id="77",
    )

    rejected = await reject_pending_action(item.id, store, user_id="owner")
    assert rejected is not None
    assert rejected.status == ConfirmationStatus.REJECTED

    # Попытка подтвердить отклоненное действие невозможна
    with pytest.raises(ValueError, match="cannot be resumed"):
        await resume_action(item.id, store, confirmed_by="owner")
