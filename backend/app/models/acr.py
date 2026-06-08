from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── ACR Rule ─────────────────────────────────────────────

class AccessRuleCreate(BaseModel):
    name: str
    description: str | None = None
    resource_type: str  # dataset, ontology_type, instance, etc.
    field: str  # the column/property to check
    operator: str  # eq, ne, in, not_in, intersects
    value: Any  # static value or user attribute reference like "user:user_id"
    priority: int = 0
    enabled: bool = True


class AccessRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    field: str | None = None
    operator: str | None = None
    value: Any | None = None
    priority: int | None = None
    enabled: bool | None = None


class AccessRuleResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    resource_type: str
    field: str
    operator: str
    value: Any
    priority: int = 0
    enabled: bool = True
    created_at: str | None = None
    updated_at: str | None = None


# ── Rule Group ───────────────────────────────────────────

class RuleGroupCreate(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    rule_ids: list[int] = Field(default_factory=list)
    logic: str = "and"  # and / or


class RuleGroupUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    rule_ids: list[int] | None = None
    logic: str | None = None


class RuleGroupResponse(BaseModel):
    id: int
    name: str
    display_name: str | None = None
    description: str | None = None
    rule_ids: list[int] = Field(default_factory=list)
    logic: str = "and"
    created_at: str | None = None
    updated_at: str | None = None


# ── Rule Group Binding ───────────────────────────────────

class RuleGroupBindingCreate(BaseModel):
    rule_group_id: int
    user_id: str | None = None
    group_name: str | None = None


class RuleGroupBindingResponse(BaseModel):
    id: int
    rule_group_id: int
    user_id: str | None = None
    group_name: str | None = None
    created_at: str | None = None


# ── ACR Config ───────────────────────────────────────────

class ACRConfigUpdate(BaseModel):
    acr_enabled: bool | None = None
    row_level_security: bool | None = None
    property_level_security: bool | None = None
    userid_injection: bool | None = None
    admin_bypass: bool | None = None
    admin_roles: list[str] | None = None
    public_data_allowed: bool | None = None


class ACRConfigResponse(BaseModel):
    acr_enabled: bool = False
    row_level_security: bool = False
    property_level_security: bool = False
    userid_injection: bool = False
    admin_bypass: bool = True
    admin_roles: list[str] = Field(default_factory=lambda: ["admin"])
    public_data_allowed: bool = False
