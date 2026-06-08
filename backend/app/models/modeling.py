from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SchemaAnalyzeRequest(BaseModel):
    """Step 1: 发送 Schema 给 LLM 分析"""
    connection_type: str = "parameters"  # parameters | dsn | default
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    dsn: str | None = None
    schema_name: str = "public"
    business_context: str | None = None  # 业务背景描述
    output_language: str = "zh"  # zh | en
    exclude_tables: list[str] = Field(default_factory=list)
    include_tables: list[str] = Field(default_factory=list)
    custom_llm_config: dict[str, Any] | None = None
    extract_wide_table_entities: bool = False
    timeout_seconds: int = 300


class TestConnectionRequest(BaseModel):
    connection_type: str = "parameters"
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    dsn: str | None = None


class CompileRequest(BaseModel):
    """Step 2: 编译/修复 LLM 分析结果"""
    analysis_result: dict[str, Any]  # LLM 返回的原生结果


class RegisterRequest(BaseModel):
    """Step 3: 注册编译后的本体定义"""
    compiled_ontology: dict[str, Any]


class QuickModelRequest(BaseModel):
    """快速建模 — 直接从数据库表结构生成，不用 LLM"""
    connection_type: str = "parameters"
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    dsn: str | None = None
    schema_name: str = "public"
    exclude_tables: list[str] = Field(default_factory=list)
    include_tables: list[str] = Field(default_factory=list)


class ModelingTaskStatus(BaseModel):
    task_id: str
    status: str  # pending | running | completed | failed
    progress: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None


class DetectChangesRequest(BaseModel):
    """结构变更检测 — 对比数据库 Schema 与已注册 Ontology"""
    connection_type: str = "parameters"
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    dsn: str | None = None
    schema_name: str = "public"
    exclude_tables: list[str] = Field(default_factory=list)
    include_tables: list[str] = Field(default_factory=list)
