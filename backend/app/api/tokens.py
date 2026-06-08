from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from ..core.response import error, ok, paged
from ..models import store
from ..models.user import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreateResponse,
    PersonalTokenCreate,
    PersonalTokenResponse,
    PersonalTokenCreateResponse,
)
from .deps import get_current_admin, get_current_user

router = APIRouter(prefix="/api")

API_KEY_PREFIX = "ak_"
PAT_PREFIX = "pat_"


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _make_api_key() -> tuple[str, str, str]:
    raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
    key_hash = _hash_token(raw)
    key_prefix = raw[:10]  # first 10 chars visible
    return raw, key_hash, key_prefix


def _make_pat() -> tuple[str, str, str]:
    raw = PAT_PREFIX + secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    token_prefix = raw[:10]
    return raw, token_hash, token_prefix


def _expires_at(days: int | None) -> datetime | None:
    if days:
        return datetime.now(UTC) + timedelta(days=days)
    return None


# ── User API Keys ─────────────────────────────────────────

@router.get("/api-keys")
async def list_my_api_keys(user: dict = Depends(get_current_user)):
    keys = await store.list_api_keys(user["id"])
    return ok(keys)


@router.post("/api-keys")
async def create_api_key(body: APIKeyCreate, user: dict = Depends(get_current_user)):
    raw_key, key_hash, key_prefix = _make_api_key()
    expires = _expires_at(body.expires_in_days)
    key = await store.create_api_key(
        user["id"], body.name, key_hash, key_prefix, body.scopes, expires,
    )
    key["api_key"] = raw_key
    return ok(APIKeyCreateResponse(**key).model_dump(mode="json"))


@router.delete("/api-keys/{key_id}")
async def revoke_my_api_key(key_id: str, user: dict = Depends(get_current_user)):
    deleted = await store.revoke_api_key(key_id, user["id"])
    if not deleted:
        return error(404, "API Key 不存在")
    return ok(None, "已撤销")


# ── Admin API Keys ────────────────────────────────────────

@router.get("/admin/api-keys")
async def list_all_api_keys_admin(page: int = 1, page_size: int = 20, _: dict = Depends(get_current_admin)):
    items, total = await store.list_all_api_keys(page, page_size)
    return paged(items, total, page, page_size)


@router.delete("/admin/api-keys/{key_id}")
async def revoke_api_key_admin(key_id: str, _: dict = Depends(get_current_admin)):
    deleted = await store.revoke_api_key(key_id)
    if not deleted:
        return error(404, "API Key 不存在")
    return ok(None, "已撤销")


# ── User Personal Access Tokens ────────────────────────────

@router.get("/personal-tokens")
async def list_my_personal_tokens(user: dict = Depends(get_current_user)):
    tokens = await store.list_personal_tokens(user["id"])
    return ok(tokens)


@router.post("/personal-tokens")
async def create_personal_token(body: PersonalTokenCreate, user: dict = Depends(get_current_user)):
    raw_token, token_hash, token_prefix = _make_pat()
    expires = _expires_at(body.expires_in_days)
    pat = await store.create_personal_token(
        user["id"], body.name, token_hash, token_prefix, body.scopes, expires,
    )
    pat["token"] = raw_token
    return ok(PersonalTokenCreateResponse(**pat).model_dump(mode="json"))


@router.delete("/personal-tokens/{token_id}")
async def revoke_my_personal_token(token_id: str, user: dict = Depends(get_current_user)):
    deleted = await store.revoke_personal_token(token_id, user["id"])
    if not deleted:
        return error(404, "个人令牌不存在")
    return ok(None, "已撤销")


# ── Admin Token Blacklist ──────────────────────────────────

@router.get("/admin/tokens")
async def list_all_tokens_admin(page: int = 1, page_size: int = 20, _: dict = Depends(get_current_admin)):
    items, total = await store.list_all_personal_tokens(page, page_size)
    return paged(items, total, page, page_size)


@router.delete("/admin/tokens/{token_id}")
async def revoke_token_admin(token_id: str, _: dict = Depends(get_current_admin)):
    deleted = await store.revoke_personal_token(token_id)
    if not deleted:
        return error(404, "令牌不存在")
    return ok(None, "已撤销")


@router.post("/admin/tokens/revoke-by-user/{user_id}")
async def revoke_user_tokens_admin(user_id: str, _: dict = Depends(get_current_admin)):
    count = await store.revoke_all_user_tokens(user_id)
    return ok({"revoked_count": count}, f"已撤销 {count} 个令牌")
