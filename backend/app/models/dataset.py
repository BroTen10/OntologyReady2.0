from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    display_name: str
    description: str | None = None


class DatasetUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None


class DatasetResponse(BaseModel):
    dataset_id: str
    display_name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
