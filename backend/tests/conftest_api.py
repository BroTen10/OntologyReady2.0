from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_store_auth():
    """Mocks store functions used by auth deps so tests can run without DB."""
    with (
        patch("app.models.store.get_user_by_id", new_callable=AsyncMock) as get_user,
        patch("app.models.store.get_user_by_username", new_callable=AsyncMock) as get_user_by_name,
        patch("app.models.store.is_token_blacklisted", new_callable=AsyncMock) as is_blacklisted,
        patch("app.models.store.list_users", new_callable=AsyncMock) as list_u,
        patch("app.models.store.create_user", new_callable=AsyncMock) as create_u,
        patch("app.models.store.update_user", new_callable=AsyncMock) as update_u,
        patch("app.models.store.delete_user", new_callable=AsyncMock) as delete_u,
        patch("app.models.store.update_last_login", new_callable=AsyncMock) as update_login,
        patch("app.models.store.list_roles", new_callable=AsyncMock) as list_r,
        patch("app.models.store.create_role", new_callable=AsyncMock) as create_r,
        patch("app.models.store.update_role", new_callable=AsyncMock) as update_r,
        patch("app.models.store.delete_role", new_callable=AsyncMock) as delete_r,
        patch("app.models.store.list_groups", new_callable=AsyncMock) as list_g,
        patch("app.models.store.create_group", new_callable=AsyncMock) as create_g,
        patch("app.models.store.update_group", new_callable=AsyncMock) as update_g,
        patch("app.models.store.delete_group", new_callable=AsyncMock) as delete_g,
    ):
        # Default: user is authenticated admin
        admin_user = {
            "id": "admin-id",
            "username": "admin",
            "email": "admin@test.local",
            "full_name": "Admin",
            "is_active": True,
            "is_superuser": True,
            "roles": ["admin"],
            "groups": ["admins"],
        }
        get_user.return_value = admin_user
        is_blacklisted.return_value = False
        get_user_by_name.return_value = admin_user

        # list defaults
        list_u.return_value = ([admin_user], 1)
        list_r.return_value = [{"name": "admin", "display_name": "Administrator"}]
        list_g.return_value = [{"name": "admins", "display_name": "Admins"}]

        # delete defaults
        delete_u.return_value = True
        delete_r.return_value = True
        delete_g.return_value = True

        yield {
            "get_user_by_id": get_user,
            "get_user_by_username": get_user_by_name,
            "is_token_blacklisted": is_blacklisted,
            "list_users": list_u,
            "create_user": create_u,
            "update_user": update_u,
            "delete_user": delete_u,
            "list_roles": list_r,
            "create_role": create_r,
            "update_role": update_r,
            "delete_role": delete_r,
            "list_groups": list_g,
            "create_group": create_g,
            "update_group": update_g,
            "delete_group": delete_g,
        }
