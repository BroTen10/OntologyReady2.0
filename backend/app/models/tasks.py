from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

TASK_TYPES = [
    "analyze_schema",
    "sync_data",
    "document_parse",
    "graphrag_run",
    "rag_eval_run",
    "quick_model",
    "detect_changes",
]


class TaskRequest(BaseModel):
    """通用异步任务请求"""
    task_type: str  # analyze_schema | sync_data | document_parse | graphrag_run | rag_eval_run
    dataset_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    task_type: str
    dataset_id: str
    status: str  # pending | running | completed | failed | cancelled
    progress: float = 0.0
    params: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskLogEntry(BaseModel):
    id: int
    task_id: str
    timestamp: str
    level: str  # info | warn | error
    message: str
