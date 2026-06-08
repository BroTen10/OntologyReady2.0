"""GraphRAG — knowledge graph enhanced retrieval storage."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from ..database import get_pool


async def _ensure_graphrag_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS age")
        await conn.execute("LOAD 'age'")
        await conn.execute('SET search_path = ag_catalog, "$user", public')

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS graphrag_workspaces (
                workspace_id TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                description  TEXT DEFAULT '',
                is_default   BOOLEAN DEFAULT false,
                config       JSONB DEFAULT '{}',
                created_at   TIMESTAMPTZ DEFAULT now(),
                updated_at   TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS graphrag_documents (
                doc_id      TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                filename    TEXT NOT NULL,
                file_size   BIGINT DEFAULT 0,
                file_type   TEXT DEFAULT '',
                status      TEXT DEFAULT 'pending',
                metadata    JSONB DEFAULT '{}',
                created_at  TIMESTAMPTZ DEFAULT now(),
                updated_at  TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS graphrag_model_configs (
                config_id     TEXT PRIMARY KEY,
                workspace_id  TEXT DEFAULT '',
                model_type    TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                model_name    TEXT NOT NULL,
                config        JSONB DEFAULT '{}',
                is_default    BOOLEAN DEFAULT false,
                created_at    TIMESTAMPTZ DEFAULT now(),
                updated_at    TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS graphrag_entities (
                entity_id    TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                name         TEXT NOT NULL,
                entity_type  TEXT NOT NULL DEFAULT 'organization',
                properties   JSONB DEFAULT '{}',
                description  TEXT DEFAULT '',
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS graphrag_relations (
                relation_id  TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                source_id    TEXT NOT NULL,
                target_id    TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties   JSONB DEFAULT '{}',
                description  TEXT DEFAULT '',
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS graphrag_communities (
                community_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                title        TEXT NOT NULL,
                summary      TEXT DEFAULT '',
                entity_ids   JSONB DEFAULT '[]',
                weight       FLOAT DEFAULT 0,
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """)


# ═══════════════════════════════════════════════════════════
# Workspaces
# ═══════════════════════════════════════════════════════════

async def create_workspace(name: str, description: str = "", config: dict | None = None) -> dict:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    ws_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO graphrag_workspaces (workspace_id, name, description, config, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $5) RETURNING *""",
            ws_id, name, description, json.dumps(config or {}, ensure_ascii=False), now,
        )
    return _ws_row(row)


async def list_workspaces() -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM graphrag_workspaces ORDER BY created_at DESC")
    return [_ws_row(r) for r in rows]


async def get_workspace(ws_id: str) -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM graphrag_workspaces WHERE workspace_id = $1", ws_id)
    return _ws_row(row) if row else None


async def update_workspace(ws_id: str, name: str | None = None, description: str | None = None, config: dict | None = None) -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    now = datetime.now(UTC)
    ws = await get_workspace(ws_id)
    if not ws:
        return None
    new_name = name if name is not None else ws["name"]
    new_desc = description if description is not None else ws.get("description", "")
    new_config = config if config is not None else ws.get("config", {})
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE graphrag_workspaces SET name=$1, description=$2, config=$3, updated_at=$4
               WHERE workspace_id=$5 RETURNING *""",
            new_name, new_desc, json.dumps(new_config, ensure_ascii=False), now, ws_id,
        )
    return _ws_row(row) if row else None


async def delete_workspace(ws_id: str) -> bool:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM graphrag_documents WHERE workspace_id = $1", ws_id)
        await conn.execute("DELETE FROM graphrag_entities WHERE workspace_id = $1", ws_id)
        await conn.execute("DELETE FROM graphrag_relations WHERE workspace_id = $1", ws_id)
        await conn.execute("DELETE FROM graphrag_communities WHERE workspace_id = $1", ws_id)
        await conn.execute("DELETE FROM graphrag_model_configs WHERE workspace_id = $1", ws_id)
        result = await conn.execute("DELETE FROM graphrag_workspaces WHERE workspace_id = $1", ws_id)
    return result == "DELETE 1"


async def set_default_workspace(ws_id: str) -> None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE graphrag_workspaces SET is_default = false")
        await conn.execute("UPDATE graphrag_workspaces SET is_default = true WHERE workspace_id = $1", ws_id)


async def get_default_workspace() -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM graphrag_workspaces WHERE is_default = true LIMIT 1")
    return _ws_row(row) if row else None


# ═══════════════════════════════════════════════════════════
# Documents
# ═══════════════════════════════════════════════════════════

async def create_document(workspace_id: str, filename: str, file_content: bytes) -> dict:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    doc_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO graphrag_documents (doc_id, workspace_id, filename, file_size, file_type, status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, 'pending', $6, $6) RETURNING *""",
            doc_id, workspace_id, filename, len(file_content), file_type, now,
        )
    return _doc_row(row)


async def list_documents(workspace_id: str) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM graphrag_documents WHERE workspace_id = $1 ORDER BY created_at DESC",
            workspace_id,
        )
    return [_doc_row(r) for r in rows]


async def get_document(doc_id: str) -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM graphrag_documents WHERE doc_id = $1", doc_id)
    return _doc_row(row) if row else None


async def update_document_status(doc_id: str, status: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE graphrag_documents SET status = $1, updated_at = $2 WHERE doc_id = $3",
            status, datetime.now(UTC), doc_id,
        )


async def delete_document(doc_id: str) -> bool:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM graphrag_documents WHERE doc_id = $1", doc_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Entities
# ═══════════════════════════════════════════════════════════

async def save_entities(workspace_id: str, entities: list[dict]) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        for e in entities:
            entity_id = e.get("entity_id") or uuid.uuid4().hex[:12]
            await conn.execute(
                """INSERT INTO graphrag_entities (entity_id, workspace_id, name, entity_type, properties, description)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (entity_id) DO UPDATE SET name=$3, entity_type=$4, properties=$5, description=$6""",
                entity_id, workspace_id, e["name"], e.get("entity_type", "organization"),
                json.dumps(e.get("properties", {}), ensure_ascii=False),
                e.get("description", ""),
            )
            results.append({"entity_id": entity_id, **e})
    return results


async def list_entities(workspace_id: str, entity_type: str | None = None) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if entity_type:
            rows = await conn.fetch(
                "SELECT * FROM graphrag_entities WHERE workspace_id = $1 AND entity_type = $2 ORDER BY created_at DESC",
                workspace_id, entity_type,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM graphrag_entities WHERE workspace_id = $1 ORDER BY created_at DESC",
                workspace_id,
            )
    return [_entity_row(r) for r in rows]


async def get_entity(entity_id: str) -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM graphrag_entities WHERE entity_id = $1", entity_id)
    return _entity_row(row) if row else None


async def delete_entities_by_workspace(workspace_id: str) -> None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM graphrag_entities WHERE workspace_id = $1", workspace_id)


# ═══════════════════════════════════════════════════════════
# Relations
# ═══════════════════════════════════════════════════════════

async def save_relations(workspace_id: str, relations: list[dict]) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        for r in relations:
            rel_id = r.get("relation_id") or uuid.uuid4().hex[:12]
            await conn.execute(
                """INSERT INTO graphrag_relations (relation_id, workspace_id, source_id, target_id, relation_type, properties, description)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   ON CONFLICT (relation_id) DO UPDATE SET source_id=$3, target_id=$4, relation_type=$5, properties=$6, description=$7""",
                rel_id, workspace_id, r["source_id"], r["target_id"], r["relation_type"],
                json.dumps(r.get("properties", {}), ensure_ascii=False),
                r.get("description", ""),
            )
            results.append({"relation_id": rel_id, **r})
    return results


async def list_relations(workspace_id: str, relation_type: str | None = None) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if relation_type:
            rows = await conn.fetch(
                "SELECT * FROM graphrag_relations WHERE workspace_id = $1 AND relation_type = $2 ORDER BY created_at DESC",
                workspace_id, relation_type,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM graphrag_relations WHERE workspace_id = $1 ORDER BY created_at DESC",
                workspace_id,
            )
    return [_relation_row(r) for r in rows]


async def get_entity_relations(workspace_id: str, entity_id: str) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM graphrag_relations WHERE workspace_id = $1 AND (source_id = $2 OR target_id = $2)",
            workspace_id, entity_id,
        )
    return [_relation_row(r) for r in rows]


async def delete_relations_by_workspace(workspace_id: str) -> None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM graphrag_relations WHERE workspace_id = $1", workspace_id)


# ═══════════════════════════════════════════════════════════
# Communities
# ═══════════════════════════════════════════════════════════

async def save_communities(workspace_id: str, communities: list[dict]) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM graphrag_communities WHERE workspace_id = $1", workspace_id)
        for c in communities:
            cid = c.get("community_id") or uuid.uuid4().hex[:12]
            await conn.execute(
                """INSERT INTO graphrag_communities (community_id, workspace_id, title, summary, entity_ids, weight)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                cid, workspace_id, c["title"], c.get("summary", ""),
                json.dumps(c.get("entity_ids", []), ensure_ascii=False),
                c.get("weight", 0),
            )
            results.append({"community_id": cid, **c})
    return results


async def list_communities(workspace_id: str) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM graphrag_communities WHERE workspace_id = $1 ORDER BY weight DESC",
            workspace_id,
        )
    return [_community_row(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# Model Configs
# ═══════════════════════════════════════════════════════════

MODEL_TYPES = ["llm", "embedding", "rerank", "vlm"]


async def create_model_config(workspace_id: str, model_type: str, provider_name: str, model_name: str, config: dict | None = None, is_default: bool = False) -> dict:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    config_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    if is_default:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE graphrag_model_configs SET is_default = false WHERE workspace_id = $1 AND model_type = $2",
                workspace_id, model_type,
            )
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO graphrag_model_configs (config_id, workspace_id, model_type, provider_name, model_name, config, is_default, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8) RETURNING *""",
            config_id, workspace_id, model_type, provider_name, model_name,
            json.dumps(config or {}, ensure_ascii=False), is_default, now,
        )
    return _config_row(row)


async def list_model_configs(workspace_id: str = "", model_type: str | None = None) -> list[dict]:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if workspace_id and model_type:
            rows = await conn.fetch(
                "SELECT * FROM graphrag_model_configs WHERE workspace_id = $1 AND model_type = $2 ORDER BY created_at DESC",
                workspace_id, model_type,
            )
        elif workspace_id:
            rows = await conn.fetch(
                "SELECT * FROM graphrag_model_configs WHERE workspace_id = $1 ORDER BY model_type, created_at DESC",
                workspace_id,
            )
        elif model_type:
            rows = await conn.fetch(
                "SELECT * FROM graphrag_model_configs WHERE model_type = $1 ORDER BY created_at DESC",
                model_type,
            )
        else:
            rows = await conn.fetch("SELECT * FROM graphrag_model_configs ORDER BY model_type, created_at DESC")
    return [_config_row(r) for r in rows]


async def get_model_config(config_id: str) -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM graphrag_model_configs WHERE config_id = $1", config_id)
    return _config_row(row) if row else None


async def get_default_model_config(workspace_id: str, model_type: str) -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM graphrag_model_configs WHERE workspace_id = $1 AND model_type = $2 AND is_default = true LIMIT 1",
            workspace_id, model_type,
        )
        if not row:
            row = await conn.fetchrow(
                "SELECT * FROM graphrag_model_configs WHERE model_type = $2 LIMIT 1",
                workspace_id, model_type,
            )
    return _config_row(row) if row else None


async def update_model_config(config_id: str, **kwargs) -> dict | None:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    now = datetime.now(UTC)
    existing = await get_model_config(config_id)
    if not existing:
        return None

    fields = {
        "provider_name": kwargs.get("provider_name", existing["provider_name"]),
        "model_name": kwargs.get("model_name", existing["model_name"]),
        "config": json.dumps(kwargs.get("config", existing.get("config", {})), ensure_ascii=False),
        "is_default": kwargs.get("is_default", existing.get("is_default", False)),
    }

    if fields["is_default"]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE graphrag_model_configs SET is_default = false WHERE workspace_id = $1 AND model_type = $2",
                existing["workspace_id"], existing["model_type"],
            )

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE graphrag_model_configs SET provider_name=$1, model_name=$2, config=$3, is_default=$4, updated_at=$5
               WHERE config_id=$6 RETURNING *""",
            fields["provider_name"], fields["model_name"], fields["config"], fields["is_default"], now, config_id,
        )
    return _config_row(row) if row else None


async def delete_model_config(config_id: str) -> bool:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM graphrag_model_configs WHERE config_id = $1", config_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Graph Stats
# ═══════════════════════════════════════════════════════════

async def get_graph_stats(workspace_id: str) -> dict:
    await _ensure_graphrag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        entity_count = await conn.fetchval("SELECT count(*) FROM graphrag_entities WHERE workspace_id = $1", workspace_id)
        relation_count = await conn.fetchval("SELECT count(*) FROM graphrag_relations WHERE workspace_id = $1", workspace_id)
        community_count = await conn.fetchval("SELECT count(*) FROM graphrag_communities WHERE workspace_id = $1", workspace_id)
        doc_count = await conn.fetchval("SELECT count(*) FROM graphrag_documents WHERE workspace_id = $1", workspace_id)

        type_counts = await conn.fetch(
            "SELECT entity_type, count(*) as cnt FROM graphrag_entities WHERE workspace_id = $1 GROUP BY entity_type",
            workspace_id,
        )
    return {
        "entity_count": entity_count,
        "relation_count": relation_count,
        "community_count": community_count,
        "document_count": doc_count,
        "entity_types": {r["entity_type"]: r["cnt"] for r in type_counts},
    }


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _ws_row(row) -> dict:
    d = dict(row)
    for k in ("config",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    for ts in ("created_at", "updated_at"):
        if d.get(ts):
            d[ts] = d[ts].isoformat()
    return d


def _doc_row(row) -> dict:
    d = dict(row)
    for k in ("metadata",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    for ts in ("created_at", "updated_at"):
        if d.get(ts):
            d[ts] = d[ts].isoformat()
    return d


def _entity_row(row) -> dict:
    d = dict(row)
    for k in ("properties",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def _relation_row(row) -> dict:
    d = dict(row)
    for k in ("properties",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def _community_row(row) -> dict:
    d = dict(row)
    for k in ("entity_ids",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def _config_row(row) -> dict:
    d = dict(row)
    for k in ("config",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    for ts in ("created_at", "updated_at"):
        if d.get(ts):
            d[ts] = d[ts].isoformat()
    return d
