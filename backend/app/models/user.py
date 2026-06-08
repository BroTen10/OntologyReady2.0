from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ── User ──────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    full_name: str | None = None
    is_superuser: bool = False
    roles: list[str] = Field(default_factory=lambda: ["developer"])


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None
    custom_attributes: dict[str, Any] | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    roles: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    last_login: str | None = None


# ── Auth ──────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Role ──────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class RoleResponse(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


# ── Group ─────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    parent_group: str | None = None


class GroupUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    parent_group: str | None = None


class GroupResponse(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    parent_group: str | None = None
    children: list[str] = Field(default_factory=list)


# ── API Key / PAT ─────────────────────────────────────────

class APIKeyCreate(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool = True
    scopes: list[str] = Field(default_factory=list)
    created_by: str
    last_used_at: str | None = None
    expires_at: str | None = None
    created_at: str | None = None


class APIKeyCreateResponse(BaseModel):
    id: str
    name: str
    api_key: str  # raw key — only returned once
    key_prefix: str
    scopes: list[str]
    expires_at: str | None = None


class PersonalTokenCreate(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = None


class PersonalTokenResponse(BaseModel):
    id: str
    name: str
    token_prefix: str
    is_active: bool = True
    scopes: list[str] = Field(default_factory=list)
    user_id: str
    last_used_at: str | None = None
    expires_at: str | None = None
    created_at: str | None = None


class PersonalTokenCreateResponse(BaseModel):
    id: str
    name: str
    token: str  # raw PAT — only returned once
    token_prefix: str
    scopes: list[str]
    expires_at: str | None = None


class TokenBlacklistEntry(BaseModel):
    jti: str | None = None
    token_id: str | None = None
    user_id: str
    reason: str | None = None
    expires_at: str | None = None
    created_at: str | None = None
