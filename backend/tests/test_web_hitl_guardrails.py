"""Интеграционные тесты HITL-защиты эндпоинтов chat-app (HIT-03, HIT-04, D-01, D-02, D-03, D-05)."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from assistant_shared.hitl import (
    ConfirmationChannel,
    ConfirmationStatus,
    ConfirmationStore,
    confirm_pending_action,
    reject_pending_action,
    resume_action,
)


@pytest.mark.anyio
async def test_delete_returns_409_for_all_entities():
    """Проверяет перехват DELETE на всех 4 ресурсах с возвратом 409 Conflict и созданием PendingConfirmation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. DELETE /projects/1
        res_proj = await client.delete("/api/v1/projects/1")
        assert res_proj.status_code == 409
        data_proj = res_proj.json()["detail"]
        assert data_proj["error"] == "confirmation_required"
        assert data_proj["status"] == "pending"
        assert data_proj["action_type"] == "delete_project"
        assert data_proj["target_id"] == "1"
        assert "confirmation_id" in data_proj

        # 2. DELETE /documents/1
        res_doc = await client.delete("/api/v1/documents/1")
        assert res_doc.status_code == 409
        data_doc = res_doc.json()["detail"]
        assert data_doc["error"] == "confirmation_required"
        assert data_doc["status"] == "pending"
        assert data_doc["action_type"] == "delete_document"
        assert data_doc["target_id"] == "1"

        # 3. DELETE /tasks/1
        res_task = await client.delete("/api/v1/tasks/1")
        assert res_task.status_code == 409
        data_task = res_task.json()["detail"]
        assert data_task["error"] == "confirmation_required"
        assert data_task["status"] == "pending"
        assert data_task["action_type"] == "delete_task"
        assert data_task["target_id"] == "1"

        # 4. DELETE /reminders/1
        res_rem = await client.delete("/api/v1/reminders/1")
        assert res_rem.status_code == 409
        data_rem = res_rem.json()["detail"]
        assert data_rem["error"] == "confirmation_required"
        assert data_rem["status"] == "pending"
        assert data_rem["action_type"] == "delete_reminder"
        assert data_rem["target_id"] == "1"

        # Убеждаемся, что ни одна из сущностей НЕ была удалена из базы
        with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
            cursor = conn.cursor()
            assert cursor.execute("SELECT id FROM projects WHERE id = 1").fetchone() is not None
            assert cursor.execute("SELECT id FROM documents WHERE id = 1").fetchone() is not None
            assert cursor.execute("SELECT id FROM tasks WHERE id = 1").fetchone() is not None
            assert cursor.execute("SELECT id FROM reminders WHERE id = 1").fetchone() is not None

            # Проверяем запись в pending_confirmations
            cursor.execute("SELECT persona_id, channel, status FROM pending_confirmations WHERE id = ?", (data_proj["confirmation_id"],))
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == settings.PERSONA_ID
            assert row[1] == "web"
            assert row[2] == "pending"


@pytest.mark.anyio
async def test_delete_non_existent_returns_404():
    """Проверяет, что DELETE несуществующей сущности возвращает 404 и не создает подтверждение."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/api/v1/projects/999999")
        assert res.status_code == 404

        res = await client.delete("/api/v1/tasks/999999")
        assert res.status_code == 404

        res = await client.delete("/api/v1/documents/999999")
        assert res.status_code == 404

        res = await client.delete("/api/v1/reminders/999999")
        assert res.status_code == 404


@pytest.mark.anyio
async def test_get_confirmation_status_and_metadata():
    """Проверяет чтение статуса и изоляцию payload от утечки данных (T-05-04)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Создаем подтверждение через вызов DELETE
        res = await client.delete("/api/v1/tasks/1")
        assert res.status_code == 409
        conf_id = res.json()["detail"]["confirmation_id"]

        # Запрашиваем статус
        status_res = await client.get(f"/api/v1/confirmations/{conf_id}")
        assert status_res.status_code == 200
        data = status_res.json()
        assert data["id"] == conf_id
        assert data["status"] == "pending"
        assert data["action_type"] == "delete_task"
        assert data["target_id"] == "1"
        assert data["channel"] == "web"
        assert "payload" not in data  # T-05-04: payload не раскрывается через GET эндпоинт

        # Несуществующий запрос возвращает 404
        not_found_res = await client.get("/api/v1/confirmations/non-existent-uuid")
        assert not_found_res.status_code == 404


@pytest.mark.anyio
async def test_web_api_cannot_confirm_directly():
    """Проверяет запрет подтверждения действий через Web API (HIT-03, HIT-04)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/api/v1/tasks/1")
        conf_id = res.json()["detail"]["confirmation_id"]

        # Прямые вызовы POST/PUT для подтверждения недопустимы в Web API
        post_res = await client.post(f"/api/v1/confirmations/{conf_id}/confirm")
        assert post_res.status_code in (404, 405)

        put_res = await client.put(f"/api/v1/confirmations/{conf_id}")
        assert put_res.status_code in (404, 405)


@pytest.mark.anyio
async def test_two_step_execution_flow():
    """Проверяет полный двухшаговый цикл: вызов DELETE -> 409 -> подтверждение владельцем -> физическое удаление."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Создаем новую временную задачу
        create_res = await client.post("/api/v1/tasks", json={
            "title": "Задача для двухшагового удаления",
            "area": "ГУАП",
            "priority": "P2",
        })
        assert create_res.status_code == 201
        task_id = create_res.json()["id"]

        # 2. Шаг 1: вызов DELETE -> получаем 409 и confirmation_id
        del_res = await client.delete(f"/api/v1/tasks/{task_id}")
        assert del_res.status_code == 409
        conf_id = del_res.json()["detail"]["confirmation_id"]

        # Проверяем, что задача все еще на месте
        check_res = await client.get(f"/api/v1/tasks/{task_id}")
        assert check_res.status_code == 200

        # 3. Шаг 2: подтверждение через тестовый хелпер confirm_pending_action (канал Telegram владельца)
        store = ConfirmationStore(settings.SQLITE_DB_PATH)
        exec_res = await confirm_pending_action(conf_id, store, user_id="123456789")
        assert exec_res is True

        # 4. Проверяем, что задача физически удалена
        after_del = await client.get(f"/api/v1/tasks/{task_id}")
        assert after_del.status_code == 404

        # 5. Проверяем, что статус запроса в API стал confirmed
        status_res = await client.get(f"/api/v1/confirmations/{conf_id}")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "confirmed"
        assert status_res.json()["confirmed_by"] == "123456789"


@pytest.mark.anyio
async def test_resume_action_idempotency_and_atomic_lock():
    """Проверяет защиту от повторного выполнения действия (атомарный лок)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/v1/projects", json={
            "name": "Проект для проверки идемпотентности",
            "area": "ГУАП",
        })
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        del_res = await client.delete(f"/api/v1/projects/{project_id}")
        assert del_res.status_code == 409
        conf_id = del_res.json()["detail"]["confirmation_id"]

        store = ConfirmationStore(settings.SQLITE_DB_PATH)
        # Первое подтверждение проходит успешно
        first_run = await resume_action(conf_id, store, confirmed_by="owner")
        assert first_run is True

        # Повторное подтверждение отклоняется с ошибкой
        with pytest.raises(ValueError, match="cannot be resumed"):
            await resume_action(conf_id, store, confirmed_by="owner")


@pytest.mark.anyio
async def test_expired_confirmation_blocks_deletion():
    """Проверяет отказ в выполнении и переход в expired при истекшем сроке жизни (D-03)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/v1/reminders", json={
            "what": "Напоминание с истечением срока",
            "check_date": "2026-10-10",
        })
        assert create_res.status_code == 201
        rem_id = create_res.json()["id"]

        del_res = await client.delete(f"/api/v1/reminders/{rem_id}")
        assert del_res.status_code == 409
        conf_id = del_res.json()["detail"]["confirmation_id"]

        # Искусственно переводим expires_at в прошлое
        expired_iso = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
            conn.execute("UPDATE pending_confirmations SET expires_at = ? WHERE id = ?", (expired_iso, conf_id))

        # При запросе статус переводится в expired
        status_res = await client.get(f"/api/v1/confirmations/{conf_id}")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "expired"

        # Попытка возобновления блокируется
        store = ConfirmationStore(settings.SQLITE_DB_PATH)
        with pytest.raises(ValueError, match="cannot be resumed"):
            await resume_action(conf_id, store, confirmed_by="owner")

        # Сущность НЕ удалена
        get_res = await client.get(f"/api/v1/reminders/{rem_id}")
        assert get_res.status_code == 200


@pytest.mark.anyio
async def test_reject_action_blocks_deletion():
    """Проверяет отклонение действия (reject) и сохранение целостности данных."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/v1/documents", json={
            "title": "Документ для отклонения",
            "category": "general",
            "content_markdown": "Важный документ",
        })
        assert create_res.status_code == 201
        doc_id = create_res.json()["id"]

        del_res = await client.delete(f"/api/v1/documents/{doc_id}")
        assert del_res.status_code == 409
        conf_id = del_res.json()["detail"]["confirmation_id"]

        store = ConfirmationStore(settings.SQLITE_DB_PATH)
        rejected = await reject_pending_action(conf_id, store, user_id="owner")
        assert rejected is not None
        assert rejected.status == ConfirmationStatus.REJECTED

        status_res = await client.get(f"/api/v1/confirmations/{conf_id}")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "rejected"

        # Возобновление невозможно
        with pytest.raises(ValueError, match="cannot be resumed"):
            await resume_action(conf_id, store, confirmed_by="owner")

        # Документ остался в базе
        get_res = await client.get(f"/api/v1/documents/{doc_id}")
        assert get_res.status_code == 200


@pytest.mark.anyio
async def test_ui_polling_contract():
    """Проверяет контракт клиентского поллинга статуса подтверждения (D-02, HIT-04)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Создаем задачу
        create_res = await client.post("/api/v1/tasks", json={
            "title": "Задача для теста поллинга",
            "area": "ГУАП",
            "priority": "P3",
        })
        assert create_res.status_code == 201
        task_id = create_res.json()["id"]

        # 2. Вызов DELETE возвращает 409 с confirmation_id
        del_res = await client.delete(f"/api/v1/tasks/{task_id}")
        assert del_res.status_code == 409
        conf_id = del_res.json()["detail"]["confirmation_id"]

        # 3. Эмуляция первого цикла поллинга (pending)
        poll_res_1 = await client.get(f"/api/v1/confirmations/{conf_id}")
        assert poll_res_1.status_code == 200
        assert poll_res_1.json()["status"] == "pending"

        # 4. Владелец подтверждает действие в Telegram
        store = ConfirmationStore(settings.SQLITE_DB_PATH)
        await confirm_pending_action(conf_id, store, user_id="123456789")

        # 5. Эмуляция второго цикла поллинга (confirmed)
        poll_res_2 = await client.get(f"/api/v1/confirmations/{conf_id}")
        assert poll_res_2.status_code == 200
        assert poll_res_2.json()["status"] == "confirmed"

        # 6. Проверяем, что в static/index.html внедрена клиентская логика pollConfirmation и перехвата 409
        index_html_path = Path(__file__).resolve().parent.parent / "app" / "static" / "index.html"
        assert index_html_path.exists(), "index.html должен существовать"
        html_content = index_html_path.read_text(encoding="utf-8")

        assert "pollConfirmation" in html_content
        assert "showToast" in html_content
        assert "409" in html_content
        assert "Запрос на удаление отправлен в Telegram" in html_content
