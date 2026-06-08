from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..database import get_pool


async def _ensure_task_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS async_tasks (
                task_id      TEXT PRIMARY KEY,
                task_type    TEXT NOT NULL,
                dataset_id   TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                progress     REAL DEFAULT 0.0,
                params       JSONB DEFAULT '{}',
                result       JSONB DEFAULT NULL,
                error        TEXT,
                started_at   TIMESTAMPTZ,
                finished_at  TIMESTAMPTZ,
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS async_task_logs (
                id           SERIAL PRIMARY KEY,
                task_id      TEXT NOT NULL,
                timestamp    TIMESTAMPTZ DEFAULT now(),
                level        TEXT NOT NULL DEFAULT 'info',
                message      TEXT
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_async_task_logs_task ON async_task_logs (task_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_async_tasks_dataset ON async_tasks (dataset_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_async_tasks_status ON async_tasks (status)")


async def create_task(task_type: str, dataset_id: str, params: dict) -> str:
    await _ensure_task_tables()
    task_id = f"task_{uuid4().hex[:12]}"
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO async_tasks (task_id, task_type, dataset_id, status, params, created_at)
               VALUES ($1, $2, $3, 'pending', $4, $5)""",
            task_id, task_type, dataset_id,
            json.dumps(params, ensure_ascii=False),
            datetime.now(UTC),
        )
    return task_id


async def get_task(task_id: str) -> dict | None:
    await _ensure_task_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM async_tasks WHERE task_id = $1", task_id)
    return _row_to_dict(row) if row else None


async def list_tasks(
    dataset_id: str | None = None,
    status: str | None = None,
    task_type: str | None = None,
    page: int = 1, page_size: int = 20,
) -> tuple[list[dict], int]:
    await _ensure_task_tables()
    pool = await get_pool()
    conditions = []
    params: list[Any] = []
    idx = 1

    if dataset_id:
        conditions.append(f"dataset_id = ${idx}")
        params.append(dataset_id); idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status); idx += 1
    if task_type:
        conditions.append(f"task_type = ${idx}")
        params.append(task_type); idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM async_tasks {where}", *params)

        params.append(page_size)
        params.append((page - 1) * page_size)
        sql = f"SELECT * FROM async_tasks {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        rows = await conn.fetch(sql, *params)
    return [_row_to_dict(r) for r in rows], total


async def update_task_status(
    task_id: str, status: str, *,
    progress: float | None = None,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    await _ensure_task_tables()
    pool = await get_pool()
    setters = ["status = $1"]
    params: list[Any] = [status]
    idx = 2

    if progress is not None:
        setters.append(f"progress = ${idx}")
        params.append(progress); idx += 1
    if result is not None:
        setters.append(f"result = ${idx}")
        params.append(json.dumps(result, ensure_ascii=False)); idx += 1
    if error is not None:
        setters.append(f"error = ${idx}")
        params.append(error); idx += 1

    if status == "running":
        setters.append("started_at = COALESCE(started_at, now())")
    elif status in ("completed", "failed", "cancelled"):
        setters.append("finished_at = now()")

    params.append(task_id)
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE async_tasks SET {', '.join(setters)} WHERE task_id = ${idx}",
            *params,
        )


async def add_task_log(task_id: str, level: str, message: str) -> None:
    await _ensure_task_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO async_task_logs (task_id, level, message) VALUES ($1, $2, $3)",
            task_id, level, message,
        )


async def get_task_logs(task_id: str, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
    await _ensure_task_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM async_task_logs WHERE task_id = $1", task_id)
        rows = await conn.fetch(
            "SELECT * FROM async_task_logs WHERE task_id = $1 ORDER BY timestamp DESC LIMIT $2 OFFSET $3",
            task_id, page_size, (page - 1) * page_size,
        )
        return [_log_to_dict(r) for r in rows], total


def _row_to_dict(row: Any) -> dict:
    if row is None:
        return {}
    return {
        "task_id": row["task_id"],
        "task_type": row["task_type"],
        "dataset_id": row["dataset_id"],
        "status": row["status"],
        "progress": float(row.get("progress", 0) or 0),
        "params": json.loads(row.get("params", "{}") or "{}"),
        "result": json.loads(row.get("result", "null") or "null") if row.get("result") else None,
        "error": row.get("error"),
        "started_at": row["started_at"].isoformat() if row.get("started_at") else None,
        "finished_at": row["finished_at"].isoformat() if row.get("finished_at") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def _log_to_dict(row: Any) -> dict:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "timestamp": row["timestamp"].isoformat() if row.get("timestamp") else None,
        "level": row["level"],
        "message": row["message"],
    }
