from __future__ import annotations

from datetime import UTC, datetime

from ..database import get_pool


async def _ensure_dataset_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id   TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                description  TEXT,
                created_at   TIMESTAMPTZ DEFAULT now(),
                updated_at   TIMESTAMPTZ DEFAULT now()
            )
        """)


async def create_dataset(display_name: str, description: str | None = None) -> dict:
    await _ensure_dataset_table()
    pool = await get_pool()
    dataset_id = f"_ontology_{display_name.lower().replace(' ', '_')}"
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        # Create the dataset entry
        row = await conn.fetchrow(
            """INSERT INTO datasets (dataset_id, display_name, description, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $4) RETURNING *""",
            dataset_id, display_name, description, now,
        )
        # Create independent schema for this dataset
        safe_id = dataset_id.replace("-", "_")
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {safe_id}")
        # Create independent graph space via AGE
        try:
            await conn.execute(f"SELECT create_graph('{safe_id}_graph')")
        except Exception:
            pass  # graph may already exist or AGE not available
    return _row_to_dataset(row)


async def get_dataset(dataset_id: str) -> dict | None:
    await _ensure_dataset_table()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM datasets WHERE dataset_id = $1", dataset_id)
    return _row_to_dataset(row) if row else None


async def list_datasets(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    await _ensure_dataset_table()
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM datasets")
        rows = await conn.fetch(
            "SELECT * FROM datasets ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_row_to_dataset(r) for r in rows], total


async def update_dataset(dataset_id: str, display_name: str | None = None, description: str | None = None) -> dict | None:
    await _ensure_dataset_table()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if display_name is None and description is None:
            row = await conn.fetchrow("SELECT * FROM datasets WHERE dataset_id = $1", dataset_id)
            return _row_to_dataset(row) if row else None
        row = await conn.fetchrow(
            """UPDATE datasets SET
                 display_name = COALESCE($2, display_name),
                 description = COALESCE($3, description),
                 updated_at = now()
               WHERE dataset_id = $1 RETURNING *""",
            dataset_id, display_name, description,
        )
    return _row_to_dataset(row) if row else None


async def delete_dataset(dataset_id: str) -> bool:
    await _ensure_dataset_table()
    pool = await get_pool()
    safe_id = dataset_id.replace("-", "_")
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM datasets WHERE dataset_id = $1", dataset_id)
        # Drop schema and graph
        try:
            await conn.execute(f"DROP SCHEMA IF EXISTS {safe_id} CASCADE")
        except Exception:
            pass
        try:
            await conn.execute(f"SELECT drop_graph('{safe_id}_graph', true)")
        except Exception:
            pass
    return result == "DELETE 1"


def _row_to_dataset(row) -> dict:
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d
