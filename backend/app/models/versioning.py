from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Staged Change ──────────────────────────────────────────────

class StagedChangeCreate(BaseModel):
    entity_type: Literal["object_type", "link_type", "action_type"]
    change_type: Literal["create", "update", "delete"]
    entity_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    previous_data: dict[str, Any] | None = None
    description: str | None = None


class StagedChangeRef(BaseModel):
    change_id: str


class StagedChangeResponse(BaseModel):
    change_id: str
    entity_type: str
    change_type: str
    entity_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    previous_data: dict[str, Any] | None = None
    description: str | None = None
    created_at: str | None = None


class CommitStagingRequest(BaseModel):
    message: str
    commit_changes: list[str] | None = None  # specific change_ids to commit; None = all


class UndoStagedChangesRequest(BaseModel):
    change_ids: list[str] | None = None  # None = undo all


# ── Version Snapshot ───────────────────────────────────────────

class VersionSnapshot(BaseModel):
    version_id: str | None = None
    dataset_id: str
    version_number: int | None = None
    commit_message: str
    ontology_snapshot: dict[str, Any] = Field(default_factory=dict)
    changes_summary: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str | None = None
    created_at: str | None = None


class VersionSnapshotResponse(BaseModel):
    version_id: str
    dataset_id: str
    version_number: int
    commit_message: str
    ontology_snapshot: dict[str, Any] = Field(default_factory=dict)
    changes_summary: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str | None = None
    created_at: str | None = None
    notes: str | None = None


class UpdateVersionNotesRequest(BaseModel):
    notes: str


class DiffEntry(BaseModel):
    entity_type: str
    entity_name: str
    field: str
    old_value: Any
    new_value: Any


class DiffResponse(BaseModel):
    version_a: str
    version_b: str
    diffs: list[DiffEntry]
