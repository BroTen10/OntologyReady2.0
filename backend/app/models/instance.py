from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ObjectInstanceCreate(BaseModel):
    object_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class ObjectInstanceUpdate(BaseModel):
    properties: dict[str, Any] | None = None


class ObjectInstanceResponse(BaseModel):
    object_id: str
    object_type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class LinkInstanceCreate(BaseModel):
    link_type: str
    source_id: str
    target_id: str
    properties: dict[str, Any] = Field(default_factory=dict)


class LinkInstanceUpdate(BaseModel):
    properties: dict[str, Any] | None = None


class LinkInstanceResponse(BaseModel):
    link_id: str
    link_type: str
    source_id: str
    target_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ObjectSearchRequest(BaseModel):
    object_type: str | None = None
    query: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    page: int = 1
    page_size: int = 20


class BatchObjectsRequest(BaseModel):
    items: list[ObjectInstanceCreate]


class BatchLinksRequest(BaseModel):
    items: list[LinkInstanceCreate]


class PathRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = 5


class TraverseRequest(BaseModel):
    start_node: str
    direction: str = "both"  # outgoing | incoming | both
    max_depth: int = 3
    edge_types: list[str] | None = None
    node_types: list[str] | None = None
