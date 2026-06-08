from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from ..core.response import error, ok, paged
from ..core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from ..models import store
from ..models.user import (
    GroupCreate,
    GroupUpdate,
    RefreshRequest,
    RoleCreate,
    RoleUpdate,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from .deps import get_current_admin, get_current_user

router = APIRouter(prefix="/api")


# ── Auth ──────────────────────────────────────────────────

@router.post("/auth/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await store.get_user_by_username(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        return error(401, "用户名或密码错误")
    if not user.get("is_active"):
        return error(403, "账户已被禁用")

    await store.update_last_login(user["id"])
    user["last_login"] = datetime.utcnow().isoformat()

    jti = uuid4().hex
    access_token = create_access_token({"sub": user["id"], "jti": jti})
    refresh_token = create_refresh_token({"sub": user["id"], "jti": uuid4().hex})

    return ok(TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_to_user_response(user),
    ).model_dump(mode="json"))


@router.post("/auth/refresh")
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        return error(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        return error(401, "Invalid token type")
    if await store.is_token_blacklisted(payload.get("jti", "")):
        return error(401, "Token revoked")

    user = await store.get_user_by_id(payload["sub"])
    if not user or not user.get("is_active"):
        return error(401, "User inactive or not found")

    # Blacklist old refresh token
    await store.blacklist_token(payload["jti"], user["id"], datetime.utcfromtimestamp(payload["exp"]))

    jti = uuid4().hex
    access_token = create_access_token({"sub": user["id"], "jti": jti})
    refresh_token = create_refresh_token({"sub": user["id"], "jti": uuid4().hex})

    return ok(TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_to_user_response(user),
    ).model_dump(mode="json"))


@router.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    # In a stateless JWT system, logout is handled client-side (discard tokens).
    # Server-side: client should send the token to be blacklisted if needed.
    return ok(None, "已登出")


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return ok(_to_user_response(user))


# ── Users CRUD ────────────────────────────────────────────

@router.get("/users")
async def list_users_api(page: int = 1, page_size: int = 20, _: dict = Depends(get_current_admin)):
    items, total = await store.list_users(page, page_size)
    users = [_to_user_response(u) for u in items]
    return paged(users, total, page, page_size)


@router.get("/users/{user_id}")
async def get_user_api(user_id: str, _: dict = Depends(get_current_admin)):
    user = await store.get_user_by_id(user_id)
    if not user:
        return error(404, "用户不存在")
    return ok(_to_user_response(user))


@router.post("/users")
async def create_user_api(body: UserCreate, _: dict = Depends(get_current_admin)):
    existing = await store.get_user_by_username(body.username)
    if existing:
        return error(409, "用户名已存在")
    user = await store.create_user(body.model_dump())
    return ok(_to_user_response(user))


@router.put("/users/{user_id}")
async def update_user_api(user_id: str, body: UserUpdate, _: dict = Depends(get_current_admin)):
    user = await store.update_user(user_id, body.model_dump(exclude_none=True))
    if not user:
        return error(404, "用户不存在")
    return ok(_to_user_response(user))


@router.delete("/users/{user_id}")
async def delete_user_api(user_id: str, _: dict = Depends(get_current_admin)):
    deleted = await store.delete_user(user_id)
    if not deleted:
        return error(404, "用户不存在")
    return ok(None, "已删除")


# ── Roles ─────────────────────────────────────────────────

@router.get("/roles")
async def list_roles_api(_: dict = Depends(get_current_admin)):
    roles = await store.list_roles()
    return ok(roles)


@router.post("/roles")
async def create_role_api(body: RoleCreate, _: dict = Depends(get_current_admin)):
    role = await store.create_role(body.name, body.display_name or "", body.description or "", body.permissions)
    return ok(role)


@router.put("/roles/{name}")
async def update_role_api(name: str, body: RoleUpdate, _: dict = Depends(get_current_admin)):
    role = await store.update_role(name, body.model_dump(exclude_none=True))
    if not role:
        return error(404, "角色不存在")
    return ok(role)


@router.delete("/roles/{name}")
async def delete_role_api(name: str, _: dict = Depends(get_current_admin)):
    if name in ("admin", "developer", "viewer"):
        return error(400, "不能删除系统默认角色")
    deleted = await store.delete_role(name)
    if not deleted:
        return error(404, "角色不存在")
    return ok(None, "已删除")


# ── Groups ────────────────────────────────────────────────

@router.get("/groups")
async def list_groups_api(_: dict = Depends(get_current_admin)):
    groups = await store.list_groups()
    return ok(groups)


@router.post("/groups")
async def create_group_api(body: GroupCreate, _: dict = Depends(get_current_admin)):
    group = await store.create_group(body.name, body.display_name or "", body.description or "", body.parent_group)
    return ok(group)


@router.put("/groups/{name}")
async def update_group_api(name: str, body: GroupUpdate, _: dict = Depends(get_current_admin)):
    group = await store.update_group(name, body.model_dump(exclude_none=True))
    if not group:
        return error(404, "用户组不存在")
    return ok(group)


@router.delete("/groups/{name}")
async def delete_group_api(name: str, _: dict = Depends(get_current_admin)):
    if name in ("admins", "developers", "viewers"):
        return error(400, "不能删除系统默认用户组")
    deleted = await store.delete_group(name)
    if not deleted:
        return error(404, "用户组不存在")
    return ok(None, "已删除")


# ── Helper ────────────────────────────────────────────────

def _to_user_response(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "is_active": user.get("is_active", True),
        "is_superuser": user.get("is_superuser", False),
        "roles": user.get("roles", []),
        "groups": user.get("groups", []),
        "custom_attributes": user.get("custom_attributes", {}),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "last_login": user.get("last_login"),
    }
