from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..database import get_pool


async def _ensure_ontology_tables(schema_name: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.object_types (
                type_name    TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                description  TEXT,
                properties   JSONB DEFAULT '[]',
                fgac_config   JSONB DEFAULT NULL,
                compute_logic JSONB DEFAULT NULL,
                source       JSONB DEFAULT NULL,
                created_at   TIMESTAMPTZ DEFAULT now(),
                updated_at   TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.link_types (
                link_name    TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                description  TEXT,
                source_type  TEXT NOT NULL,
                target_type  TEXT NOT NULL,
                directed     BOOLEAN DEFAULT TRUE,
                properties   JSONB DEFAULT '[]',
                created_at   TIMESTAMPTZ DEFAULT now(),
                updated_at   TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.action_types (
                action_name  TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                target_type  TEXT NOT NULL,
                description  TEXT,
                parameters   JSONB DEFAULT '[]',
                webhook_url  TEXT,
                method       TEXT DEFAULT 'POST',
                headers      JSONB DEFAULT '{{}}',
                requires_confirmation BOOLEAN DEFAULT FALSE,
                effect_type  TEXT DEFAULT 'side_effect',
                created_at   TIMESTAMPTZ DEFAULT now(),
                updated_at   TIMESTAMPTZ DEFAULT now()
            )
        """)


def _to_schema(dataset_id: str) -> str:
    return dataset_id.replace("-", "_")


# ═══════════════════════════════════════════════════════════
# Object Types
# ═══════════════════════════════════════════════════════════

async def create_object_type(dataset_id: str, data: dict) -> dict:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {schema}.object_types (type_name, display_name, description, properties,
                 fgac_config, compute_logic, source, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8) RETURNING *""",
            data["type_name"], data["display_name"], data.get("description"),
            json.dumps(data.get("properties", []), ensure_ascii=False),
            json.dumps(data.get("fgac_config"), ensure_ascii=False) if data.get("fgac_config") else None,
            json.dumps(data.get("compute_logic"), ensure_ascii=False) if data.get("compute_logic") else None,
            json.dumps(data.get("source"), ensure_ascii=False) if data.get("source") else None,
            now,
        )
    return _row_to_typed(row)


async def get_object_type(dataset_id: str, type_name: str) -> dict | None:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.object_types WHERE type_name = $1", type_name)
    return _row_to_typed(row) if row else None


async def list_object_types(dataset_id: str, page: int = 1, page_size: int = 100) -> tuple[list[dict], int]:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT count(*) FROM {schema}.object_types")
        rows = await conn.fetch(
            f"SELECT * FROM {schema}.object_types ORDER BY type_name LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_row_to_typed(r) for r in rows], total


async def update_object_type(dataset_id: str, type_name: str, data: dict) -> dict | None:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        setters: list[str] = []
        vals: list[Any] = []
        idx = 1
        for py_key, col in [("display_name", "display_name"), ("description", "description")]:
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(data[py_key])
                idx += 1
        for py_key, col in [("properties", "properties"), ("fgac_config", "fgac_config"),
                            ("compute_logic", "compute_logic"), ("source", "source")]:
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(json.dumps(data[py_key], ensure_ascii=False))
                idx += 1
        if not setters:
            return await get_object_type(dataset_id, type_name)
        setters.append(f"updated_at = ${idx}")
        vals.append(datetime.now(UTC))
        idx += 1
        vals.append(type_name)
        sql = f"UPDATE {schema}.object_types SET {', '.join(setters)} WHERE type_name = ${idx} RETURNING *"
        row = await conn.fetchrow(sql, *vals)
    return _row_to_typed(row) if row else None


async def delete_object_type(dataset_id: str, type_name: str) -> bool:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {schema}.object_types WHERE type_name = $1", type_name)
    return result == "DELETE 1"


async def batch_create_object_types(dataset_id: str, items: list[dict]) -> list[dict]:
    results = []
    for item in items:
        results.append(await create_object_type(dataset_id, item))
    return results


# ═══════════════════════════════════════════════════════════
# Link Types
# ═══════════════════════════════════════════════════════════

async def create_link_type(dataset_id: str, data: dict) -> dict:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {schema}.link_types (link_name, display_name, description,
                 source_type, target_type, directed, properties, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8) RETURNING *""",
            data["link_name"], data["display_name"], data.get("description"),
            data["source_type"], data["target_type"], data.get("directed", True),
            json.dumps(data.get("properties", []), ensure_ascii=False),
            now,
        )
    return _row_to_typed(row)


async def get_link_type(dataset_id: str, link_name: str) -> dict | None:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.link_types WHERE link_name = $1", link_name)
    return _row_to_typed(row) if row else None


async def list_link_types(dataset_id: str, page: int = 1, page_size: int = 100) -> tuple[list[dict], int]:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT count(*) FROM {schema}.link_types")
        rows = await conn.fetch(
            f"SELECT * FROM {schema}.link_types ORDER BY link_name LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_row_to_typed(r) for r in rows], total


async def update_link_type(dataset_id: str, link_name: str, data: dict) -> dict | None:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        setters: list[str] = []
        vals: list[Any] = []
        idx = 1
        for py_key, col in [
            ("display_name", "display_name"), ("description", "description"),
            ("source_type", "source_type"), ("target_type", "target_type"), ("directed", "directed"),
        ]:
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(data[py_key])
                idx += 1
        if "properties" in data:
            setters.append(f"properties = ${idx}")
            vals.append(json.dumps(data["properties"], ensure_ascii=False))
            idx += 1
        if not setters:
            return await get_link_type(dataset_id, link_name)
        setters.append(f"updated_at = ${idx}")
        vals.append(datetime.now(UTC))
        idx += 1
        vals.append(link_name)
        sql = f"UPDATE {schema}.link_types SET {', '.join(setters)} WHERE link_name = ${idx} RETURNING *"
        row = await conn.fetchrow(sql, *vals)
    return _row_to_typed(row) if row else None


async def delete_link_type(dataset_id: str, link_name: str) -> bool:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {schema}.link_types WHERE link_name = $1", link_name)
    return result == "DELETE 1"


async def batch_create_link_types(dataset_id: str, items: list[dict]) -> list[dict]:
    results = []
    for item in items:
        results.append(await create_link_type(dataset_id, item))
    return results


# ═══════════════════════════════════════════════════════════
# Action Types
# ═══════════════════════════════════════════════════════════

async def create_action_type(dataset_id: str, data: dict) -> dict:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {schema}.action_types (action_name, display_name, target_type, description,
                 parameters, webhook_url, method, headers, requires_confirmation, effect_type,
                 created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $11) RETURNING *""",
            data["action_name"], data["display_name"], data["target_type"], data.get("description"),
            json.dumps(data.get("parameters", []), ensure_ascii=False),
            data.get("webhook_url"), data.get("method", "POST"),
            json.dumps(data.get("headers", {}), ensure_ascii=False),
            data.get("requires_confirmation", False),
            data.get("effect_type", "side_effect"),
            now,
        )
    return _row_to_typed(row)


async def get_action_type(dataset_id: str, action_name: str) -> dict | None:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.action_types WHERE action_name = $1", action_name)
    return _row_to_typed(row) if row else None


async def list_action_types(dataset_id: str, page: int = 1, page_size: int = 100) -> tuple[list[dict], int]:
    schema = _to_schema(dataset_id)
    await _ensure_ontology_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT count(*) FROM {schema}.action_types")
        rows = await conn.fetch(
            f"SELECT * FROM {schema}.action_types ORDER BY action_name LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_row_to_typed(r) for r in rows], total


async def update_action_type(dataset_id: str, action_name: str, data: dict) -> dict | None:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        setters: list[str] = []
        vals: list[Any] = []
        idx = 1
        for py_key, col in [
            ("display_name", "display_name"), ("target_type", "target_type"), ("description", "description"),
            ("webhook_url", "webhook_url"), ("method", "method"),
            ("requires_confirmation", "requires_confirmation"), ("effect_type", "effect_type"),
        ]:
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(data[py_key])
                idx += 1
        for py_key, col in [("parameters", "parameters"), ("headers", "headers")]:
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(json.dumps(data[py_key], ensure_ascii=False))
                idx += 1
        if not setters:
            return await get_action_type(dataset_id, action_name)
        setters.append(f"updated_at = ${idx}")
        vals.append(datetime.now(UTC))
        idx += 1
        vals.append(action_name)
        sql = f"UPDATE {schema}.action_types SET {', '.join(setters)} WHERE action_name = ${idx} RETURNING *"
        row = await conn.fetchrow(sql, *vals)
    return _row_to_typed(row) if row else None


async def delete_action_type(dataset_id: str, action_name: str) -> bool:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {schema}.action_types WHERE action_name = $1", action_name)
    return result == "DELETE 1"


async def batch_create_action_types(dataset_id: str, items: list[dict]) -> list[dict]:
    results = []
    for item in items:
        results.append(await create_action_type(dataset_id, item))
    return results


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _row_to_typed(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    json_fields = ["properties", "parameters", "headers", "fgac_config", "compute_logic", "source"]
    for k in json_fields:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    for ts_field in ["created_at", "updated_at"]:
        if d.get(ts_field):
            d[ts_field] = d[ts_field].isoformat()
    return d
