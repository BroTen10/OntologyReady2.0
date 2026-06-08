from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SyncConfig(BaseModel):
    """数据同步配置"""
    source_type: str = "postgresql"  # postgresql | mysql | hive | hbase | lindorm
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    schema_name: str = "public"
    extra_params: dict[str, Any] = Field(default_factory=dict)


class TableMapping(BaseModel):
    """源表到目标 ObjectType 的映射"""
    source_table: str
    target_object_type: str
    column_mapping: dict[str, str] = Field(default_factory=dict)  # source_col -> target_prop
    id_column: str = "id"  # 用于 UPSERT 的 ID 列
    filter_condition: str | None = None  # WHERE 条件过滤


class SyncRequest(BaseModel):
    """发起同步请求"""
    dataset_id: str
    config: SyncConfig
    mappings: list[TableMapping] = Field(default_factory=list)
    sync_mode: str = "full"  # full | incremental
    batch_size: int = 1000
    auto_create_types: bool = False  # 自动根据源表创建 ObjectType


class SyncTaskResponse(BaseModel):
    """同步任务响应"""
    task_id: str
    dataset_id: str
    status: str  # pending | running | completed | failed | cancelled
    progress: float = 0.0
    total_rows: int = 0
    synced_rows: int = 0
    errors: list[str] = Field(default_factory=list)
    config: SyncConfig | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SyncLogEntry(BaseModel):
    """同步日志条目"""
    timestamp: str
    level: str  # info | warn | error
    message: str
    table: str | None = None
    rows_affected: int | None = None
