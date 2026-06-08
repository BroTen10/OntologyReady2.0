from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.core.security import create_access_token


def make_auth_headers(user_id: str = "admin-id") -> dict:
    token = create_access_token({"sub": user_id, "jti": "test-jti"})
    return {"Authorization": f"Bearer {token}"}


async def test_health_endpoint_200(client):
    with patch("app.api.router.get_pool", new_callable=AsyncMock) as get_pool:
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="SELECT 1")
        pool = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.acquire.return_value.__aexit__.return_value = None
        get_pool.return_value = pool

        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "healthy"


async def test_health_endpoint_db_unavailable(client):
    with patch("app.api.router.get_pool", new_callable=AsyncMock) as get_pool:
        get_pool.side_effect = Exception("DB down")
        resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["database"] == "unavailable"


async def test_login_success(client, mock_store_auth):
    from app.core.security import hash_password
    hashed = hash_password("admin123")
    mock_store_auth["get_user_by_username"].return_value = {
        "id": "admin-id", "username": "admin", "password_hash": hashed,
        "is_active": True, "roles": ["admin"], "groups": ["admins"],
    }
    resp = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "access_token" in data["data"]


async def test_login_invalid_password(client, mock_store_auth):
    from app.core.security import hash_password
    hashed = hash_password("admin123")
    mock_store_auth["get_user_by_username"].return_value = {
        "id": "u1", "username": "admin", "password_hash": hashed,
        "is_active": True, "roles": [], "groups": [],
    }
    resp = client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 401


async def test_login_inactive_user(client, mock_store_auth):
    from app.core.security import hash_password
    hashed = hash_password("admin123")
    mock_store_auth["get_user_by_username"].return_value = {
        "id": "u1", "username": "inactive", "password_hash": hashed,
        "is_active": False, "roles": [], "groups": [],
    }
    resp = client.post("/api/auth/login", data={"username": "inactive", "password": "admin123"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 403


async def test_me_endpoint(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["username"] == "admin"


async def test_me_unauthorized(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_users_list(client, mock_store_auth):
    headers = make_auth_headers()
    resp = client.get("/api/users", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


async def test_users_list_forbidden_for_non_admin(client, mock_store_auth):
    mock_store_auth["get_user_by_id"].return_value = {
        "id": "dev-id", "username": "dev", "is_active": True,
        "roles": ["developer"], "groups": [],
    }
    headers = make_auth_headers("dev-id")
    resp = client.get("/api/users", headers=headers)
    assert resp.status_code == 403
