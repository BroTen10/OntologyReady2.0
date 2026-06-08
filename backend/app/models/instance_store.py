from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..database import get_pool


def _to_schema(dataset_id: str) -> str:
    return dataset_id.replace("-", "_")


async def _ensure_instance_tables(schema: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.objects (
                object_id   TEXT PRIMARY KEY,
                object_type TEXT NOT NULL,
                properties  JSONB DEFAULT '{{}}',
                created_at  TIMESTAMPTZ DEFAULT now(),
                updated_at  TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema}_objects_type
                ON {schema}.objects (object_type)
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.links (
                link_id    TEXT PRIMARY KEY,
                link_type  TEXT NOT NULL,
                source_id  TEXT NOT NULL,
                target_id  TEXT NOT NULL,
                properties JSONB DEFAULT '{{}}',
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema}_links_type
                ON {schema}.links (link_type)
        """)


# ═══════════════════════════════════════════════════════════
# Object Instances
# ═══════════════════════════════════════════════════════════

async def create_object(dataset_id: str, data: dict) -> dict:
    schema = _to_schema(dataset_id)
    await _ensure_instance_tables(schema)
    pool = await get_pool()
    object_id = data.get("object_id") or f"{data['object_type']}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {schema}.objects (object_id, object_type, properties, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $4)
               ON CONFLICT (object_id) DO UPDATE
               SET properties = $3, updated_at = $4 RETURNING *""",
            object_id, data["object_type"],
            json.dumps(data.get("properties", {}), ensure_ascii=False),
            now,
        )
    return _row_to_instance(row)


async def get_object(dataset_id: str, object_id: str) -> dict | None:
    schema = _to_schema(dataset_id)
    await _ensure_instance_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.objects WHERE object_id = $1", object_id)
    return _row_to_instance(row) if row else None


async def list_objects(dataset_id: str, page: int = 1, page_size: int = 20, object_type: str | None = None) -> tuple[list[dict], int]:
    schema = _to_schema(dataset_id)
    await _ensure_instance_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        if object_type:
            total = await conn.fetchval(f"SELECT count(*) FROM {schema}.objects WHERE object_type = $1", object_type)
            rows = await conn.fetch(
                f"SELECT * FROM {schema}.objects WHERE object_type = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                object_type, page_size, (page - 1) * page_size,
            )
        else:
            total = await conn.fetchval(f"SELECT count(*) FROM {schema}.objects")
            rows = await conn.fetch(
                f"SELECT * FROM {schema}.objects ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                page_size, (page - 1) * page_size,
            )
    return [_row_to_instance(r) for r in rows], total


async def search_objects(dataset_id: str, object_type: str | None = None, query: str | None = None, filters: dict | None = None, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    schema = _to_schema(dataset_id)
    await _ensure_instance_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions: list[str] = []
        params: list[Any] = []
        idx = 1

        if object_type:
            conditions.append(f"object_type = ${idx}")
            params.append(object_type)
            idx += 1

        if query:
            conditions.append(f"properties::text ILIKE ${idx}")
            params.append(f"%{query}%")
            idx += 1

        filters = filters or {}
        for key, value in filters.items():
            conditions.append(f"properties->>'{key}' = ${idx}")
            params.append(str(value))
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = await conn.fetchval(f"SELECT count(*) FROM {schema}.objects {where}", *params)
        rows = await conn.fetch(
            f"SELECT * FROM {schema}.objects {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *params, page_size, (page - 1) * page_size,
        )
    return [_row_to_instance(r) for r in rows], total


async def update_object(dataset_id: str, object_id: str, properties: dict) -> dict | None:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""UPDATE {schema}.objects SET properties = $1, updated_at = $2
               WHERE object_id = $3 RETURNING *""",
            json.dumps(properties, ensure_ascii=False), datetime.now(UTC), object_id,
        )
    return _row_to_instance(row) if row else None


async def delete_object(dataset_id: str, object_id: str) -> bool:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {schema}.objects WHERE object_id = $1", object_id)
    return result == "DELETE 1"


async def batch_create_objects(dataset_id: str, items: list[dict]) -> list[dict]:
    return [await create_object(dataset_id, item) for item in items]


# ═══════════════════════════════════════════════════════════
# Link Instances
# ═══════════════════════════════════════════════════════════

async def create_link(dataset_id: str, data: dict) -> dict:
    schema = _to_schema(dataset_id)
    await _ensure_instance_tables(schema)
    pool = await get_pool()
    link_id = data.get("link_id") or f"{data['link_type']}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {schema}.links (link_id, link_type, source_id, target_id, properties, created_at)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT (link_id) DO UPDATE
               SET properties = $5 RETURNING *""",
            link_id, data["link_type"], data["source_id"], data["target_id"],
            json.dumps(data.get("properties", {}), ensure_ascii=False),
            now,
        )
    return _row_to_instance(row)


async def get_link(dataset_id: str, link_id: str) -> dict | None:
    schema = _to_schema(dataset_id)
    await _ensure_instance_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.links WHERE link_id = $1", link_id)
    return _row_to_instance(row) if row else None


async def list_links(dataset_id: str, page: int = 1, page_size: int = 20, link_type: str | None = None,
                     source_id: str | None = None, target_id: str | None = None) -> tuple[list[dict], int]:
    schema = _to_schema(dataset_id)
    await _ensure_instance_tables(schema)
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions: list[str] = []
        params: list[Any] = []
        idx = 1
        if link_type:
            conditions.append(f"link_type = ${idx}"); params.append(link_type); idx += 1
        if source_id:
            conditions.append(f"source_id = ${idx}"); params.append(source_id); idx += 1
        if target_id:
            conditions.append(f"target_id = ${idx}"); params.append(target_id); idx += 1
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = await conn.fetchval(f"SELECT count(*) FROM {schema}.links {where}", *params)
        rows = await conn.fetch(
            f"SELECT * FROM {schema}.links {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *params, page_size, (page - 1) * page_size,
        )
    return [_row_to_instance(r) for r in rows], total


async def update_link(dataset_id: str, link_id: str, properties: dict) -> dict | None:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE {schema}.links SET properties = $1 WHERE link_id = $2 RETURNING *",
            json.dumps(properties, ensure_ascii=False), link_id,
        )
    return _row_to_instance(row) if row else None


async def delete_link(dataset_id: str, link_id: str) -> bool:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {schema}.links WHERE link_id = $1", link_id)
    return result == "DELETE 1"


async def batch_create_links(dataset_id: str, items: list[dict]) -> list[dict]:
    return [await create_link(dataset_id, item) for item in items]


# ═══════════════════════════════════════════════════════════
# Graph operations
# ═══════════════════════════════════════════════════════════

async def get_neighbors(dataset_id: str, object_type: str, object_id: str, depth: int = 1) -> dict:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        obj = await conn.fetchrow(
            f"SELECT * FROM {schema}.objects WHERE object_id = $1", object_id,
        )
        if not obj:
            return {"nodes": [], "edges": []}

        nodes: list[dict] = [_row_to_instance(obj)]
        edges: list[dict] = []
        seen_nodes: set[str] = {object_id}

        current_ids = {object_id}
        for _ in range(depth):
            if not current_ids:
                break
            link_rows = await conn.fetch(
                f"""SELECT * FROM {schema}.links
                    WHERE source_id = ANY($1) OR target_id = ANY($1)""",
                list(current_ids),
            )
            next_ids: set[str] = set()
            for link in link_rows:
                edge = _row_to_instance(link)
                edges.append(edge)
                for nid in (link["source_id"], link["target_id"]):
                    if nid not in seen_nodes:
                        seen_nodes.add(nid)
                        next_ids.add(nid)
            if next_ids:
                obj_rows = await conn.fetch(
                    f"SELECT * FROM {schema}.objects WHERE object_id = ANY($1)",
                    list(next_ids),
                )
                for r in obj_rows:
                    nodes.append(_row_to_instance(r))
            current_ids = next_ids
        return {"nodes": nodes, "edges": edges}


async def find_path(dataset_id: str, source_id: str, target_id: str, max_depth: int = 5) -> dict:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        # BFS on links table
        visited: set[str] = set()
        queue: list[tuple[str, list[dict]]] = [(source_id, [])]

        while queue:
            current, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
            if current in visited:
                continue
            visited.add(current)

            links = await conn.fetch(
                f"SELECT * FROM {schema}.links WHERE source_id = $1 OR target_id = $1",
                current,
            )
            for link in links:
                edge = _row_to_instance(link)
                neighbor = link["target_id"] if link["source_id"] == current else link["source_id"]
                new_path = path + [edge]
                if neighbor == target_id:
                    # Build nodes from path
                    node_ids = {source_id, target_id}
                    for e in new_path:
                        node_ids.add(e.get("source_id", "")); node_ids.add(e.get("target_id", ""))
                    nodes = []
                    for nid in node_ids:
                        r = await conn.fetchrow(f"SELECT * FROM {schema}.objects WHERE object_id = $1", nid)
                        if r:
                            nodes.append(_row_to_instance(r))
                    return {"path": new_path, "nodes": nodes, "edges": new_path}
                queue.append((neighbor, new_path))
        return {"path": [], "nodes": [], "edges": []}


async def traverse(dataset_id: str, start_node: str, direction: str = "both", max_depth: int = 3,
                   edge_types: list[str] | None = None, node_types: list[str] | None = None) -> dict:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        nodes: list[dict] = []
        edges: list[dict] = []
        seen_nodes: set[str] = set()
        seen_edges: set[str] = set()

        current_ids = {start_node}
        for _ in range(max_depth):
            if not current_ids:
                break
            conditions = []
            params: list[Any] = []
            idx = 1

            if direction == "outgoing":
                conditions.append(f"source_id = ANY(${idx})"); params.append(list(current_ids)); idx += 1
            elif direction == "incoming":
                conditions.append(f"target_id = ANY(${idx})"); params.append(list(current_ids)); idx += 1
            else:
                conditions.append(f"(source_id = ANY(${idx}) OR target_id = ANY(${idx}))"); params.append(list(current_ids)); idx += 1

            if edge_types:
                conditions.append(f"link_type = ANY(${idx})"); params.append(edge_types); idx += 1

            rows = await conn.fetch(
                f"SELECT * FROM {schema}.links WHERE {' AND '.join(conditions)}", *params,
            )
            next_ids: set[str] = set()
            for link in rows:
                edge = _row_to_instance(link)
                if link["link_id"] not in seen_edges:
                    edges.append(edge); seen_edges.add(link["link_id"])
                for nid in (link["source_id"], link["target_id"]):
                    if nid not in seen_nodes:
                        next_ids.add(nid)

            if next_ids:
                node_conditions: list[str] = []
                node_params: list[Any] = []
                n_idx = 1
                node_conditions.append(f"object_id = ANY(${n_idx})"); node_params.append(list(next_ids)); n_idx += 1
                if node_types:
                    node_conditions.append(f"object_type = ANY(${n_idx})"); node_params.append(node_types); n_idx += 1

                obj_rows = await conn.fetch(
                    f"SELECT * FROM {schema}.objects WHERE {' AND '.join(node_conditions)}", *node_params,
                )
                for r in obj_rows:
                    nid = r["object_id"]
                    if nid not in seen_nodes:
                        nodes.append(_row_to_instance(r)); seen_nodes.add(nid)
            current_ids = next_ids

        return {"nodes": nodes, "edges": edges, "traversal_metadata": {"max_depth": max_depth, "direction": direction}}


async def get_graph_stats(dataset_id: str) -> dict:
    schema = _to_schema(dataset_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        node_count = await conn.fetchval(f"SELECT count(*) FROM {schema}.objects")
        edge_count = await conn.fetchval(f"SELECT count(*) FROM {schema}.links")
        obj_types = await conn.fetch(f"SELECT object_type, count(*) as cnt FROM {schema}.objects GROUP BY object_type")
        link_types = await conn.fetch(f"SELECT link_type, count(*) as cnt FROM {schema}.links GROUP BY link_type")
    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "object_types": [{"object_type": r["object_type"], "count": r["cnt"]} for r in obj_types],
        "link_types": [{"link_type": r["link_type"], "count": r["cnt"]} for r in link_types],
    }


# ═══════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════

def _row_to_instance(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if "properties" in d and isinstance(d["properties"], str):
        try:
            d["properties"] = json.loads(d["properties"])
        except (json.JSONDecodeError, TypeError):
            pass
    for ts in ("created_at", "updated_at"):
        if d.get(ts):
            d[ts] = d[ts].isoformat()
    return d
