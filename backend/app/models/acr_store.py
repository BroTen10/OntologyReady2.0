from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..database import get_pool


async def _ensure_acr_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS acr_rules (
                id              SERIAL PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                resource_type   TEXT NOT NULL,
                field           TEXT NOT NULL,
                operator        TEXT NOT NULL DEFAULT 'eq',
                value           JSONB NOT NULL DEFAULT 'null',
                priority        INTEGER DEFAULT 0,
                enabled         BOOLEAN DEFAULT TRUE,
                created_at      TIMESTAMPTZ DEFAULT now(),
                updated_at      TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS acr_rule_groups (
                id              SERIAL PRIMARY KEY,
                name            TEXT UNIQUE NOT NULL,
                display_name    TEXT,
                description     TEXT,
                rule_ids        INTEGER[] DEFAULT '{}',
                logic           TEXT DEFAULT 'and',
                created_at      TIMESTAMPTZ DEFAULT now(),
                updated_at      TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS acr_bindings (
                id              SERIAL PRIMARY KEY,
                rule_group_id   INTEGER NOT NULL REFERENCES acr_rule_groups(id) ON DELETE CASCADE,
                user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
                group_name      TEXT REFERENCES groups(name) ON DELETE CASCADE,
                created_at      TIMESTAMPTZ DEFAULT now(),
                CHECK (user_id IS NOT NULL OR group_name IS NOT NULL)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS acr_config (
                key   TEXT PRIMARY KEY,
                value JSONB NOT NULL DEFAULT 'null'
            )
        """)


# ── ACR Config ───────────────────────────────────────────

_DEFAULT_CONFIG = {
    "acr_enabled": False,
    "row_level_security": False,
    "property_level_security": False,
    "userid_injection": False,
    "admin_bypass": True,
    "admin_roles": ["admin"],
    "public_data_allowed": False,
}


async def get_acr_config() -> dict:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM acr_config")
    cfg = dict(_DEFAULT_CONFIG)
    for row in rows:
        cfg[row["key"]] = row["value"]
    return cfg


async def update_acr_config(data: dict) -> dict:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        for key in _DEFAULT_CONFIG:
            if key in data:
                await conn.execute(
                    """INSERT INTO acr_config (key, value) VALUES ($1, $2)
                       ON CONFLICT (key) DO UPDATE SET value = $2""",
                    key, json.dumps(data[key]),
                )
    return await get_acr_config()


# ── ACR Rules ────────────────────────────────────────────

async def create_rule(data: dict) -> dict:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO acr_rules (name, description, resource_type, field, operator, value, priority, enabled)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
            data["name"], data.get("description"), data["resource_type"],
            data["field"], data.get("operator", "eq"),
            json.dumps(data.get("value")), data.get("priority", 0),
            data.get("enabled", True),
        )
    return _row_to_rule(row)


async def update_rule(rule_id: int, data: dict) -> dict | None:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM acr_rules WHERE id = $1", rule_id)
        if not row:
            return None
        existing = dict(row)
        for field in ("name", "description", "resource_type", "field", "operator", "priority", "enabled"):
            if field in data:
                existing[field] = data[field]
        if "value" in data:
            existing["value"] = json.dumps(data["value"])
        existing["updated_at"] = datetime.now(UTC)
        row = await conn.fetchrow(
            """UPDATE acr_rules SET name=$1, description=$2, resource_type=$3, field=$4,
               operator=$5, value=$6, priority=$7, enabled=$8, updated_at=$9
               WHERE id=$10 RETURNING *""",
            existing["name"], existing.get("description"), existing["resource_type"],
            existing["field"], existing["operator"],
            existing["value"] if isinstance(existing["value"], str) else json.dumps(existing["value"]),
            existing["priority"], existing["enabled"],
            existing["updated_at"], rule_id,
        )
    return _row_to_rule(row)


async def list_rules(resource_type: str | None = None) -> list[dict]:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if resource_type:
            rows = await conn.fetch(
                "SELECT * FROM acr_rules WHERE resource_type = $1 ORDER BY priority DESC, id",
                resource_type,
            )
        else:
            rows = await conn.fetch("SELECT * FROM acr_rules ORDER BY resource_type, priority DESC, id")
    return [_row_to_rule(r) for r in rows]


async def get_rule(rule_id: int) -> dict | None:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM acr_rules WHERE id = $1", rule_id)
    return _row_to_rule(row) if row else None


async def delete_rule(rule_id: int) -> bool:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM acr_rules WHERE id = $1", rule_id)
    return result == "DELETE 1"


# ── Rule Groups ──────────────────────────────────────────

async def create_rule_group(data: dict) -> dict:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO acr_rule_groups (name, display_name, description, rule_ids, logic)
               VALUES ($1, $2, $3, $4, $5) RETURNING *""",
            data["name"], data.get("display_name", ""), data.get("description", ""),
            data.get("rule_ids", []), data.get("logic", "and"),
        )
    return _row_to_group(row)


async def update_rule_group(group_id: int, data: dict) -> dict | None:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM acr_rule_groups WHERE id = $1", group_id)
        if not existing:
            return None
        d = dict(existing)
        for field in ("display_name", "description", "rule_ids", "logic"):
            if field in data:
                d[field] = data[field]
        d["updated_at"] = datetime.now(UTC)
        row = await conn.fetchrow(
            """UPDATE acr_rule_groups SET display_name=$1, description=$2, rule_ids=$3, logic=$4, updated_at=$5
               WHERE id=$6 RETURNING *""",
            d["display_name"], d["description"], d["rule_ids"], d["logic"], d["updated_at"], group_id,
        )
    return _row_to_group(row)


async def list_rule_groups() -> list[dict]:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM acr_rule_groups ORDER BY name")
    return [_row_to_group(r) for r in rows]


async def get_rule_group(group_id: int) -> dict | None:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM acr_rule_groups WHERE id = $1", group_id)
    return _row_to_group(row) if row else None


async def delete_rule_group(group_id: int) -> bool:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM acr_rule_groups WHERE id = $1", group_id)
    return result == "DELETE 1"


# ── Bindings ─────────────────────────────────────────────

async def create_binding(data: dict) -> dict:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO acr_bindings (rule_group_id, user_id, group_name)
               VALUES ($1, $2, $3) RETURNING *""",
            data["rule_group_id"], data.get("user_id"), data.get("group_name"),
        )
    return _row_to_binding(row)


async def list_bindings() -> list[dict]:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM acr_bindings ORDER BY id")
    return [_row_to_binding(r) for r in rows]


async def delete_binding(binding_id: int) -> bool:
    await _ensure_acr_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM acr_bindings WHERE id = $1", binding_id)
    return result == "DELETE 1"


# ── Row helpers ──────────────────────────────────────────

def _row_to_rule(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if isinstance(d.get("value"), str):
        try:
            d["value"] = json.loads(d["value"])
        except (json.JSONDecodeError, TypeError):
            pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d


def _row_to_group(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    return d


def _row_to_binding(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d
