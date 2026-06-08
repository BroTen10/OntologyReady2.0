from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from ..database import get_pool


def _to_schema(dataset_id: str) -> str:
    return dataset_id.replace("-", "_")


async def _ensure_staging_table(schema_name: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.staged_changes (
                change_id     TEXT PRIMARY KEY,
                entity_type   TEXT NOT NULL,
                change_type   TEXT NOT NULL,
                entity_name   TEXT NOT NULL,
                data          JSONB DEFAULT '{{}}',
                previous_data JSONB DEFAULT NULL,
                description   TEXT,
                created_at    TIMESTAMPTZ DEFAULT now()
            )
        """)


# ═══════════════════════════════════════════════════════════
# Stage
# ═══════════════════════════════════════════════════════════

async def stage_change(dataset_id: str, data: dict) -> dict:
    schema = _to_schema(dataset_id)
    await _ensure_staging_table(schema)
    pool = await get_pool()
    change_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {schema}.staged_changes (change_id, entity_type, change_type, entity_name, data, previous_data, description, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
            change_id,
            data["entity_type"], data["change_type"], data["entity_name"],
            json.dumps(data.get("data", {}), ensure_ascii=False),
            json.dumps(data.get("previous_data"), ensure_ascii=False) if data.get("previous_data") else None,
            data.get("description"),
            now,
        )
    return _row_to_dict(row)


async def list_staged_changes(dataset_id: str) -> list[dict]:
    schema = _to_schema(dataset_id)
    await _ensure_staging_table(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT * FROM {schema}.staged_changes ORDER BY created_at")
    return [_row_to_dict(r) for r in rows]


async def get_staged_change(dataset_id: str, change_id: str) -> dict | None:
    schema = _to_schema(dataset_id)
    await _ensure_staging_table(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.staged_changes WHERE change_id = $1", change_id)
    return _row_to_dict(row) if row else None


async def delete_staged_change(dataset_id: str, change_id: str) -> bool:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {schema}.staged_changes WHERE change_id = $1", change_id)
    return result == "DELETE 1"


async def clear_staging(dataset_id: str, change_ids: list[str] | None = None) -> int:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        if change_ids:
            count = 0
            for cid in change_ids:
                r = await conn.execute(f"DELETE FROM {schema}.staged_changes WHERE change_id = $1", cid)
                if r == "DELETE 1":
                    count += 1
            return count
        else:
            result = await conn.execute(f"DELETE FROM {schema}.staged_changes")
            # Parse the DELETE count
            try:
                return int(result.split()[-1])
            except (IndexError, ValueError):
                return 0


# ═══════════════════════════════════════════════════════════
# Version Snapshots
# ═══════════════════════════════════════════════════════════

async def _ensure_version_table(schema_name: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.version_snapshots (
                version_id       TEXT PRIMARY KEY,
                version_number   SERIAL,
                commit_message   TEXT NOT NULL DEFAULT '',
                ontology_snapshot JSONB DEFAULT '{{}}',
                changes_summary  JSONB DEFAULT '[]',
                notes            TEXT,
                created_by       TEXT,
                created_at       TIMESTAMPTZ DEFAULT now()
            )
        """)


async def create_version_snapshot(dataset_id: str, data: dict) -> dict:
    schema = _to_schema(dataset_id)
    await _ensure_version_table(schema)
    pool = await get_pool()
    version_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {schema}.version_snapshots (version_id, commit_message, ontology_snapshot, changes_summary, created_by, created_at)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
            version_id,
            data["commit_message"],
            json.dumps(data["ontology_snapshot"], ensure_ascii=False),
            json.dumps(data.get("changes_summary", []), ensure_ascii=False),
            data.get("created_by"),
            now,
        )
    return _row_to_version_dict(row)


async def list_versions(dataset_id: str, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    schema = _to_schema(dataset_id)
    await _ensure_version_table(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT count(*) FROM {schema}.version_snapshots")
        rows = await conn.fetch(
            f"SELECT * FROM {schema}.version_snapshots ORDER BY version_number DESC LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_row_to_version_dict(r) for r in rows], total


async def get_version(dataset_id: str, version_id: str) -> dict | None:
    schema = _to_schema(dataset_id)
    await _ensure_version_table(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.version_snapshots WHERE version_id = $1", version_id)
    return _row_to_version_dict(row) if row else None


async def update_version_notes(dataset_id: str, version_id: str, notes: str) -> dict | None:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE {schema}.version_snapshots SET notes = $1 WHERE version_id = $2 RETURNING *",
            notes, version_id,
        )
    return _row_to_version_dict(row) if row else None


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _row_to_dict(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k in ["data", "previous_data"]:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def _row_to_version_dict(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k in ["ontology_snapshot", "changes_summary"]:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d
