import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_dashboard_summary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "focus_tasks" in data
        assert "active_reminders" in data
        assert "active_projects_count" in data


@pytest.mark.anyio
async def test_projects_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List projects
        response = await client.get("/api/v1/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 1

        # 2. Create project
        create_res = await client.post("/api/v1/projects", json={
            "name": "Тестовый проект",
            "area": "AI & Dev Projects",
            "status": "active"
        })
        assert create_res.status_code == 201
        created = create_res.json()
        assert created["name"] == "Тестовый проект"

        # 3. Delete project
        del_res = await client.delete(f"/api/v1/projects/{created['id']}")
        assert del_res.status_code == 200


@pytest.mark.anyio
async def test_tasks_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create task
        res = await client.post("/api/v1/tasks", json={
            "title": "Срочная проверка расписания",
            "area": "ГУАП",
            "priority": "P1"
        })
        assert res.status_code == 201
        task = res.json()
        assert task["title"] == "Срочная проверка расписания"
        assert task["priority"] == "P1"

        # 2. Update status
        patch_res = await client.patch(f"/api/v1/tasks/{task['id']}/status", json={"status": "done"})
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "done"

        # 3. Clean up
        await client.delete(f"/api/v1/tasks/{task['id']}")


@pytest.mark.anyio
async def test_reminders_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List reminders
        res = await client.get("/api/v1/reminders")
        assert res.status_code == 200
        reminders = res.json()
        assert len(reminders) >= 1

        # 2. Toggle reminder
        r_id = reminders[0]["id"]
        toggle_res = await client.patch(f"/api/v1/reminders/{r_id}/toggle")
        assert toggle_res.status_code == 200
        # toggle back
        await client.patch(f"/api/v1/reminders/{r_id}/toggle")


@pytest.mark.anyio
async def test_documents_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List documents
        res = await client.get("/api/v1/documents")
        assert res.status_code == 200
        docs = res.json()
        assert len(docs) >= 1

        # 2. Update document
        doc_id = docs[0]["id"]
        up_res = await client.put(f"/api/v1/documents/{doc_id}", json={
            "title": "Обновленный план",
            "content_markdown": "# Тестовый заголовок"
        })
        assert up_res.status_code == 200
        assert up_res.json()["title"] == "Обновленный план"
