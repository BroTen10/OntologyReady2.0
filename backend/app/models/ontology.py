from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Property Definition ──────────────────────────────────

class PropertyDef(BaseModel):
    name: str
    type: str = "string"  # string | number | datetime | boolean
    required: bool = False
    unique: bool = False
    indexed: bool = False
    description: str | None = None
    enum: list[str] | None = None
    format: str | None = None
    metadata: dict[str, Any] | None = None


# ── Object Type ──────────────────────────────────────────

class ObjectTypeCreate(BaseModel):
    type_name: str
    display_name: str
    description: str | None = None
    properties: list[PropertyDef] = Field(default_factory=list)
    fgac_config: dict[str, Any] | None = None
    compute_logic: dict[str, Any] | None = None
    source: dict[str, Any] | None = None


class ObjectTypeUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    properties: list[PropertyDef] | None = None
    fgac_config: dict[str, Any] | None = None
    compute_logic: dict[str, Any] | None = None
    source: dict[str, Any] | None = None


class ObjectTypeResponse(BaseModel):
    type_name: str
    display_name: str
    description: str | None = None
    properties: list[PropertyDef] = Field(default_factory=list)
    fgac_config: dict[str, Any] | None = None
    compute_logic: dict[str, Any] | None = None
    source: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ── Link Type ────────────────────────────────────────────

class LinkTypeCreate(BaseModel):
    link_name: str
    display_name: str
    description: str | None = None
    source_type: str
    target_type: str
    directed: bool = True
    properties: list[PropertyDef] = Field(default_factory=list)


class LinkTypeUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    source_type: str | None = None
    target_type: str | None = None
    directed: bool | None = None
    properties: list[PropertyDef] | None = None


class LinkTypeResponse(BaseModel):
    link_name: str
    display_name: str
    description: str | None = None
    source_type: str
    target_type: str
    directed: bool = True
    properties: list[PropertyDef] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


# ── Action Type ──────────────────────────────────────────

class ActionTypeCreate(BaseModel):
    action_name: str
    display_name: str
    target_type: str
    description: str | None = None
    parameters: list[PropertyDef] = Field(default_factory=list)
    webhook_url: str | None = None
    method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    requires_confirmation: bool = False
    effect_type: str = "side_effect"  # side_effect | transformation | notification


class ActionTypeUpdate(BaseModel):
    display_name: str | None = None
    target_type: str | None = None
    description: str | None = None
    parameters: list[PropertyDef] | None = None
    webhook_url: str | None = None
    method: str | None = None
    headers: dict[str, str] | None = None
    requires_confirmation: bool | None = None
    effect_type: str | None = None


class ActionTypeResponse(BaseModel):
    action_name: str
    display_name: str
    target_type: str
    description: str | None = None
    parameters: list[PropertyDef] = Field(default_factory=list)
    webhook_url: str | None = None
    method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    requires_confirmation: bool = False
    effect_type: str = "side_effect"
    created_at: str | None = None
    updated_at: str | None = None


# ── Batch ────────────────────────────────────────────────

class BatchObjectTypeRequest(BaseModel):
    items: list[ObjectTypeCreate]


class BatchLinkTypeRequest(BaseModel):
    items: list[LinkTypeCreate]


class BatchActionTypeRequest(BaseModel):
    items: list[ActionTypeCreate]
