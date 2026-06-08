from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..database import get_pool


async def _ensure_sync_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_tasks (
                task_id      TEXT PRIMARY KEY,
                dataset_id   TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                progress     REAL DEFAULT 0.0,
                total_rows   INTEGER DEFAULT 0,
                synced_rows  INTEGER DEFAULT 0,
                errors       JSONB DEFAULT '[]',
                config       JSONB DEFAULT '{}',
                mappings     JSONB DEFAULT '[]',
                started_at   TIMESTAMPTZ,
                finished_at  TIMESTAMPTZ,
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_logs (
                id           SERIAL PRIMARY KEY,
                task_id      TEXT NOT NULL,
                timestamp    TIMESTAMPTZ DEFAULT now(),
                level        TEXT NOT NULL DEFAULT 'info',
                message      TEXT,
                table_name   TEXT,
                rows_affected INTEGER
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_logs_task ON sync_logs (task_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_tasks_dataset ON sync_tasks (dataset_id)")


async def create_sync_task(dataset_id: str, config: dict, mappings: list[dict]) -> str:
    await _ensure_sync_tables()
    task_id = f"sync_{uuid4().hex[:12]}"
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO sync_tasks (task_id, dataset_id, status, config, mappings, created_at)
               VALUES ($1, $2, 'pending', $3, $4, $5)""",
            task_id, dataset_id,
            json.dumps(config, ensure_ascii=False),
            json.dumps(mappings, ensure_ascii=False),
            datetime.now(UTC),
        )
    return task_id


async def get_sync_task(task_id: str) -> dict | None:
    await _ensure_sync_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM sync_tasks WHERE task_id = $1", task_id)
    return _row_to_dict(row) if row else None


async def list_sync_tasks(
    dataset_id: str | None = None,
    status: str | None = None,
    page: int = 1, page_size: int = 20,
) -> tuple[list[dict], int]:
    await _ensure_sync_tables()
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

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    count_sql = f"SELECT COUNT(*) FROM sync_tasks {where}"
    total = await (await pool.acquire()).fetchval(count_sql, *params)

    params.append(page_size)
    params.append((page - 1) * page_size)
    sql = f"SELECT * FROM sync_tasks {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    rows = await (await pool.acquire()).fetch(sql, *params)
    return [_row_to_dict(r) for r in rows], total


async def update_sync_task_status(
    task_id: str, status: str, progress: float = 0.0,
    synced_rows: int | None = None, total_rows: int | None = None,
    error_msg: str | None = None,
) -> None:
    await _ensure_sync_tables()
    pool = await get_pool()
    extra_sets = []
    params: list[Any] = [status, progress, task_id]
    idx = 4

    if synced_rows is not None:
        extra_sets.append(f"synced_rows = ${idx}")
        params.append(synced_rows); idx += 1
    if total_rows is not None:
        extra_sets.append(f"total_rows = ${idx}")
        params.append(total_rows); idx += 1
    if error_msg is not None:
        extra_sets.append(f"errors = errors || ${idx}::jsonb")
        params.append(json.dumps([error_msg])); idx += 1

    now_field = ""
    if status == "running":
        now_field = ", started_at = COALESCE(started_at, now())"
    elif status in ("completed", "failed", "cancelled"):
        now_field = ", finished_at = now()"

    extra = ", ".join(extra_sets)
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE sync_tasks SET status = $1, progress = $2{', ' + extra if extra else ''}{now_field} WHERE task_id = $3",
            *params,
        )


async def add_sync_log(task_id: str, level: str, message: str, table: str | None = None, rows: int | None = None) -> None:
    await _ensure_sync_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sync_logs (task_id, level, message, table_name, rows_affected) VALUES ($1, $2, $3, $4, $5)",
            task_id, level, message, table, rows,
        )


async def get_sync_logs(task_id: str, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
    await _ensure_sync_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM sync_logs WHERE task_id = $1", task_id)
        rows = await conn.fetch(
            "SELECT * FROM sync_logs WHERE task_id = $1 ORDER BY timestamp DESC LIMIT $2 OFFSET $3",
            task_id, page_size, (page - 1) * page_size,
        )
        return [_log_to_dict(r) for r in rows], total


def _row_to_dict(row: Any) -> dict:
    if row is None:
        return {}
    return {
        "task_id": row["task_id"], "dataset_id": row["dataset_id"],
        "status": row["status"], "progress": float(row.get("progress", 0) or 0),
        "total_rows": row.get("total_rows", 0) or 0, "synced_rows": row.get("synced_rows", 0) or 0,
        "errors": json.loads(row.get("errors", "[]") or "[]"),
        "config": json.loads(row.get("config", "{}") or "{}"),
        "mappings": json.loads(row.get("mappings", "[]") or "[]"),
        "started_at": row["started_at"].isoformat() if row.get("started_at") else None,
        "finished_at": row["finished_at"].isoformat() if row.get("finished_at") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def _log_to_dict(row: Any) -> dict:
    return {
        "id": row["id"], "task_id": row["task_id"],
        "timestamp": row["timestamp"].isoformat() if row.get("timestamp") else None,
        "level": row["level"], "message": row["message"],
        "table": row.get("table_name"), "rows_affected": row.get("rows_affected"),
    }
