from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.core.security import create_access_token


def make_auth_headers(user_id: str = "admin-id") -> dict:
    token = create_access_token({"sub": user_id, "jti": "test-jti"})
    return {"Authorization": f"Bearer {token}"}


async def test_list_datasets_empty(client, mock_store_auth):
    with patch("app.api.datasets.dataset_store.list_datasets", new_callable=AsyncMock) as list_ds:
        list_ds.return_value = ([], 0)
        resp = client.get("/api/datasets", headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []
    assert data["data"]["page_info"]["total"] == 0


async def test_list_datasets_with_items(client, mock_store_auth):
    items = [
        {"dataset_id": "ds-1", "display_name": "Test DS", "description": "desc"},
        {"dataset_id": "ds-2", "display_name": "DS 2", "description": None},
    ]
    with patch("app.api.datasets.dataset_store.list_datasets", new_callable=AsyncMock) as list_ds:
        list_ds.return_value = (items, 2)
        resp = client.get("/api/datasets", headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["items"]) == 2
    assert data["data"]["page_info"]["total"] == 2


async def test_create_dataset(client, mock_store_auth):
    with patch("app.api.datasets.dataset_store.create_dataset", new_callable=AsyncMock) as create_ds:
        create_ds.return_value = {
            "dataset_id": "new-ds", "display_name": "New", "description": "desc",
        }
        resp = client.post("/api/datasets", json={"display_name": "New", "description": "desc"}, headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["display_name"] == "New"


async def test_get_dataset_not_found(client, mock_store_auth):
    with patch("app.api.datasets.dataset_store.get_dataset", new_callable=AsyncMock) as get_ds:
        get_ds.return_value = None
        resp = client.get("/api/datasets/nonexistent", headers=make_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["code"] == 404


async def test_delete_dataset(client, mock_store_auth):
    with patch("app.api.datasets.dataset_store.delete_dataset", new_callable=AsyncMock) as del_ds:
        del_ds.return_value = True
        resp = client.delete("/api/datasets/ds-1", headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


async def test_delete_dataset_not_found(client, mock_store_auth):
    with patch("app.api.datasets.dataset_store.delete_dataset", new_callable=AsyncMock) as del_ds:
        del_ds.return_value = False
        resp = client.delete("/api/datasets/ds-nonexistent", headers=make_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["code"] == 404


async def test_update_dataset(client, mock_store_auth):
    with patch("app.api.datasets.dataset_store.update_dataset", new_callable=AsyncMock) as upd:
        upd.return_value = {"dataset_id": "ds-1", "display_name": "Updated", "description": "new"}
        resp = client.put("/api/datasets/ds-1", json={"display_name": "Updated"}, headers=make_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["data"]["display_name"] == "Updated"
