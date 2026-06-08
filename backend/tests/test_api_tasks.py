from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.core.security import create_access_token


def make_auth_headers(user_id: str = "admin-id") -> dict:
    token = create_access_token({"sub": user_id, "jti": "test-jti"})
    return {"Authorization": f"Bearer {token}"}


async def test_create_task(client, mock_store_auth):
    with (
        patch("app.api.tasks.tstore.create_task", new_callable=AsyncMock) as create_t,
        patch("app.api.tasks.tstore.get_task", new_callable=AsyncMock) as get_t,
        patch("app.api.tasks.task_engine.run_task", new_callable=AsyncMock) as run_t,
    ):
        create_t.return_value = "task-1"
        get_t.return_value = {
            "task_id": "task-1", "task_type": "analyze_schema", "dataset_id": "ds-1",
            "status": "pending", "progress": 0.0, "params": {}, "result": None,
            "error": None, "started_at": None, "finished_at": None,
        }
        resp = client.post("/api/tasks", json={
            "task_type": "analyze_schema", "dataset_id": "ds-1", "params": {},
        }, headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["task_id"] == "task-1"


async def test_list_tasks(client, mock_store_auth):
    with patch("app.api.tasks.tstore.list_tasks", new_callable=AsyncMock) as list_t:
        list_t.return_value = ([], 0)
        resp = client.get("/api/tasks", headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []


async def test_list_tasks_with_filters(client, mock_store_auth):
    items = [
        {"task_id": "t1", "task_type": "sync_data", "dataset_id": "ds-1",
         "status": "running", "progress": 0.5, "params": {}, "result": None,
         "error": None, "started_at": None, "finished_at": None},
    ]
    with patch("app.api.tasks.tstore.list_tasks", new_callable=AsyncMock) as list_t:
        list_t.return_value = (items, 1)
        resp = client.get("/api/tasks?status=running&task_type=sync_data", headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["page_info"]["total"] == 1


async def test_get_task_not_found(client, mock_store_auth):
    with patch("app.api.tasks.tstore.get_task", new_callable=AsyncMock) as get_t:
        get_t.return_value = None
        resp = client.get("/api/tasks/nonexistent", headers=make_auth_headers())
    assert resp.status_code == 404


async def test_cancel_task(client, mock_store_auth):
    with patch("app.api.tasks.task_engine.cancel_task", new_callable=AsyncMock) as cancel_t:
        cancel_t.return_value = True
        resp = client.post("/api/tasks/task-1/cancel", headers=make_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_cancel_task_bad_state(client, mock_store_auth):
    with patch("app.api.tasks.task_engine.cancel_task", new_callable=AsyncMock) as cancel_t:
        cancel_t.return_value = False
        resp = client.post("/api/tasks/task-1/cancel", headers=make_auth_headers())
    assert resp.status_code == 400
