from __future__ import annotations

from typing import Any

import asyncpg

from ..config import settings
from .base import GraphDBProvider, Subgraph, TraversalResult


class AGEGraphDB(GraphDBProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=2,
                max_size=settings.database_max_connections,
            )
        return self._pool

    async def _ensure_extensions(self) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS age")
            await conn.execute('LOAD \'age\'')
            await conn.execute('SET search_path = ag_catalog, "$user", public')

    async def _ensure_graph(self, graph_name: str) -> None:
        await self._ensure_extensions()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT count(*) FROM ag_catalog.ag_graph WHERE name = $1", graph_name
            )
            if not exists:
                await conn.execute(f"SELECT create_graph('{graph_name}')")

    async def create_graph(self, graph_name: str) -> None:
        await self._ensure_graph(graph_name)

    async def add_node(self, graph_name: str, label: str, properties: dict) -> str:
        await self._ensure_graph(graph_name)
        node_id = str(properties.get("id") or properties.get("node_id", ""))
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            props_json = _props_to_json(properties)
            cursor = await conn.fetchval(
                f"SELECT * FROM cypher('{graph_name}', $$ CREATE (n:{label} {{props}}) RETURN n $$) AS (n agtype)",
                props_json=props_json,
            )
        return node_id

    async def add_edge(self, graph_name: str, source_id: str, target_id: str, edge_type: str, properties: dict | None = None) -> None:
        await self._ensure_graph(graph_name)
        props = properties or {}
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            props_json = _props_to_json(props)
            await conn.execute(
                f"""SELECT * FROM cypher('{graph_name}', $$
                    MATCH (a), (b)
                    WHERE a.id = $source_id AND b.id = $target_id
                    CREATE (a)-[r:{edge_type} {{props}}]->(b)
                    RETURN r
                $$) AS (r agtype)""",
                source_id=source_id, target_id=target_id, props=props_json,
            )

    async def get_neighbors(self, graph_name: str, node_id: str, depth: int = 1) -> Subgraph:
        await self._ensure_graph(graph_name)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""SELECT * FROM cypher('{graph_name}', $$
                    MATCH (n)-[r*1..{depth}]-(m)
                    WHERE n.id = $node_id
                    RETURN n, r, m
                $$) AS (n agtype, r agtype, m agtype)""",
                node_id=node_id,
            )
        nodes: list[dict] = []
        edges: list[dict] = []
        seen_nodes: set[str] = set()
        for row in rows:
            n_data = _agtype_to_dict(row["n"])
            m_data = _agtype_to_dict(row["m"])
            if n_data.get("id") not in seen_nodes:
                nodes.append(n_data)
                seen_nodes.add(n_data.get("id", ""))
            if m_data.get("id") not in seen_nodes:
                nodes.append(m_data)
                seen_nodes.add(m_data.get("id", ""))
            edges.append(_agtype_to_dict(row["r"]))
        return Subgraph(nodes=nodes, edges=edges)

    async def traverse(self, graph_name: str, start_node: str, **params) -> TraversalResult:
        depth = params.get("depth", 3)
        subgraph = await self.get_neighbors(graph_name, start_node, depth=depth)
        return TraversalResult(path=subgraph.nodes, metadata={"depth": depth})


def _props_to_json(props: dict) -> str:
    import json
    return json.dumps(props)


def _agtype_to_dict(agtype: str) -> dict:
    import json
    try:
        return json.loads(agtype)
    except (json.JSONDecodeError, TypeError):
        return {"value": str(agtype)}
