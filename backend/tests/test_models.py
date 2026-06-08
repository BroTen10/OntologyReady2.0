from __future__ import annotations

import pytest


def test_user_model_validation():
    """Test that UserCreate model validates correctly"""
    from app.models.user import UserCreate
    u = UserCreate(username="testuser", password="secret123", email="test@test.com")
    assert u.username == "testuser"
    assert u.email == "test@test.com"
    assert u.roles == ["developer"]  # default


def test_user_update_model():
    from app.models.user import UserUpdate
    u = UserUpdate(email="new@test.com", roles=["viewer"])
    assert u.email == "new@test.com"
    assert u.roles == ["viewer"]
    assert u.full_name is None


def test_role_create_model():
    from app.models.user import RoleCreate
    r = RoleCreate(name="editor", permissions=["read", "write"])
    assert r.name == "editor"
    assert r.permissions == ["read", "write"]


def test_group_create_model():
    from app.models.user import GroupCreate
    g = GroupCreate(name="team-a", parent_group="developers")
    assert g.name == "team-a"
    assert g.parent_group == "developers"


def test_dataset_create_model():
    from app.models.dataset import DatasetCreate
    d = DatasetCreate(display_name="My Dataset", description="Test data")
    assert d.display_name == "My Dataset"
    assert d.description == "Test data"


def test_dataset_update_model():
    from app.models.dataset import DatasetUpdate
    d = DatasetUpdate(display_name="Updated Name")
    assert d.display_name == "Updated Name"
    assert d.description is None


def test_task_request_model():
    from app.models.tasks import TaskRequest
    t = TaskRequest(task_type="analyze_schema", dataset_id="ds-1", params={"table": "users"})
    assert t.task_type == "analyze_schema"
    assert t.params == {"table": "users"}


def test_task_response_model():
    from app.models.tasks import TaskResponse
    t = TaskResponse(task_id="t1", task_type="sync_data", dataset_id="ds-1",
                     status="running", progress=0.75, params={})
    assert t.status == "running"
    assert t.progress == 0.75


def test_refresh_request_model():
    from app.models.user import RefreshRequest
    r = RefreshRequest(refresh_token="some-token")
    assert r.refresh_token == "some-token"


def test_acr_rule_create_model():
    from app.models.acr import AccessRuleCreate
    r = AccessRuleCreate(
        name="owner-rule", resource_type="dataset", field="owner_id",
        operator="eq", value="user:user_id",
    )
    assert r.operator == "eq"
    assert r.field == "owner_id"
