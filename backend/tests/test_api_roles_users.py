from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

from app.core.security import create_access_token

make_auth_headers = lambda uid="admin-id": {"Authorization": f"Bearer {create_access_token({'sub': uid, 'jti': 'jti'})}"}


async def test_list_roles(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.get("/api/roles", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_create_role(client, mock_store_auth):
    mock_store_auth["create_role"].return_value = {"name": "tester", "display_name": "Tester"}
    headers = make_auth_headers()
    resp = client.post("/api/roles", json={"name": "tester", "display_name": "Tester"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "tester"


async def test_delete_role_system_default(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.delete("/api/roles/admin", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 400  # cannot delete system roles


async def test_delete_role_custom(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.delete("/api/roles/custom-role", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_list_groups(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.get("/api/groups", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_create_group(client, mock_store_auth):
    mock_store_auth["create_group"].return_value = {"name": "editors", "display_name": "Editors"}
    headers = make_auth_headers()
    resp = client.post("/api/groups", json={"name": "editors"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "editors"


async def test_delete_group_system_default(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.delete("/api/groups/admins", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 400


async def test_update_user(client, mock_store_auth):
    mock_store_auth["update_user"].return_value = {
        "id": "user-1", "username": "dev", "email": "dev@test.local",
        "is_active": True, "is_superuser": False, "roles": ["developer"],
        "groups": ["developers"],
    }
    headers = make_auth_headers()
    resp = client.put("/api/users/user-1", json={"email": "new@test.local"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_delete_user(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.delete("/api/users/user-1", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_create_user_duplicate(client, mock_store_auth):
    mock_store_auth["get_user_by_username"].return_value = {"id": "existing", "username": "dup"}
    headers = make_auth_headers()
    resp = client.post("/api/users", json={"username": "dup", "password": "pw"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 409
