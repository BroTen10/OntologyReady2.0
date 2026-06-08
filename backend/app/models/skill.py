from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Skill Schema (I/O definition) ──────────────────────

class SkillSchemaField(BaseModel):
    name: str
    type: str = "string"  # string | number | boolean | object | array
    required: bool = False
    description: str | None = None
    default: Any = None
    enum: list[str] | None = None


class SkillSchema(BaseModel):
    inputs: list[SkillSchemaField] = Field(default_factory=list)
    outputs: list[SkillSchemaField] = Field(default_factory=list)


# ── Skill Create ───────────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9_-]+$")
    display_name: str
    category: str = "general"
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    author: str | None = None
    version: str = "1.0.0"
    metadata_md: str | None = Field(None, alias="skill_md")  # SKILL.md content
    prompt_md: str | None = None  # prompt.md content
    schema_: SkillSchema | None = Field(None, alias="schema")  # schema.json
    scripts: dict[str, str] = Field(default_factory=dict)  # filename → content
    enabled: bool = True
    icon: str | None = None

    class Config:
        populate_by_name = True


# ── Skill Update ───────────────────────────────────────

class SkillUpdate(BaseModel):
    display_name: str | None = None
    category: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    author: str | None = None
    version: str | None = None
    metadata_md: str | None = Field(None, alias="skill_md")
    prompt_md: str | None = None
    schema_: SkillSchema | None = Field(None, alias="schema")
    scripts: dict[str, str] | None = None
    enabled: bool | None = None
    icon: str | None = None

    class Config:
        populate_by_name = True


# ── Skill Response ─────────────────────────────────────

class SkillResponse(BaseModel):
    id: str
    name: str
    display_name: str
    category: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    author: str | None = None
    version: str = "1.0.0"
    metadata_md: str | None = Field(None, alias="skill_md")
    prompt_md: str | None = None
    schema_: SkillSchema | None = Field(None, alias="schema")
    scripts: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    icon: str | None = None
    is_preset: bool = False
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        populate_by_name = True


# ── Preset Skill Package ───────────────────────────────

class PresetSkillInfo(BaseModel):
    name: str
    display_name: str
    category: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    author: str | None = None
    icon: str | None = None


class PresetImportRequest(BaseModel):
    presets: list[str]  # preset skill names to import


# ── Skill Pack Upload/Download ─────────────────────────

class SkillPackManifest(BaseModel):
    name: str
    display_name: str
    category: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    author: str | None = None
    version: str = "1.0.0"
    icon: str | None = None
    files: dict[str, str] = Field(default_factory=dict)  # filename → content


# ── Generate from Action Type ──────────────────────────

class SkillGenerateRequest(BaseModel):
    action_name: str  # the action type to generate skill from
    category: str = "generated"
    display_name: str | None = None
    description: str | None = None
