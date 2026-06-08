from __future__ import annotations

from typing import Any

import httpx

from .base import GraphDBProvider, Subgraph, TraversalResult


class Neo4jGraphDB(GraphDBProvider):
    """Graph database backed by Neo4j via HTTP API."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg: dict[str, Any] = config or {}
        self.uri = cfg.get("uri", "http://localhost:7474")
        self.username = cfg.get("username", "neo4j")
        self.password = cfg.get("password", "neo4j")
        self.database = cfg.get("database", "neo4j")
        self._client: httpx.AsyncClient | None = None

    def _auth(self) -> tuple[str, str]:
        return (self.username, self.password)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.uri,
                auth=self._auth(),
                timeout=30,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _execute(self, statement: str, parameters: dict | None = None) -> list[dict]:
        client = await self._get_client()
        resp = await client.post(
            f"/db/{self.database}/tx/commit",
            json={
                "statements": [{"statement": statement, "parameters": parameters or {}}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            raise RuntimeError(f"Neo4j error: {data['errors']}")
        results: list[dict] = []
        for result in data.get("results", []):
            for row in result.get("data", []):
                results.append({"row": row.get("row", []), "meta": row.get("meta", [])})
        return results

    async def create_graph(self, graph_name: str) -> None:
        """No-op in Neo4j — graphs are implicit; constraints can be added if needed."""
        pass

    async def add_node(self, graph_name: str, label: str, properties: dict) -> str:
        node_id = str(properties.get("id") or properties.get("node_id", ""))
        stmt = (
            f"CREATE (n:{label} {{props}}) RETURN n.id AS node_id"
        )
        results = await self._execute(stmt, {"props": properties})
        if results:
            returned = results[0]["row"][0]
            if returned:
                node_id = str(returned)
        return node_id

    async def add_edge(
        self,
        graph_name: str,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: dict | None = None,
    ) -> None:
        props = properties or {}
        stmt = (
            "MATCH (a {id: $source_id}), (b {id: $target_id}) "
            f"CREATE (a)-[r:{edge_type} $props]->(b) "
            "RETURN r"
        )
        await self._execute(stmt, {
            "source_id": source_id,
            "target_id": target_id,
            "props": props,
        })

    async def get_neighbors(self, graph_name: str, node_id: str, depth: int = 1) -> Subgraph:
        stmt = (
            f"MATCH (n {{id: $node_id}})-[r*1..{depth}]-(m) "
            "RETURN n, r, m"
        )
        results = await self._execute(stmt, {"node_id": node_id})
        nodes: list[dict] = []
        edges: list[dict] = []
        seen_nodes: set[str] = set()
        for entry in results:
            row = entry["row"]
            n_data = dict(row[0]) if isinstance(row[0], dict) else {}
            m_data = dict(row[2]) if len(row) > 2 and isinstance(row[2], dict) else {}
            rels = row[1] if len(row) > 1 else []

            n_id = n_data.get("id", "")
            m_id = m_data.get("id", "")
            if n_id not in seen_nodes:
                nodes.append(n_data)
                seen_nodes.add(n_id)
            if m_id not in seen_nodes:
                nodes.append(m_data)
                seen_nodes.add(m_id)

            if isinstance(rels, list):
                for rel in rels:
                    if isinstance(rel, dict):
                        edges.append(rel)

        return Subgraph(nodes=nodes, edges=edges)

    async def traverse(self, graph_name: str, start_node: str, **params) -> TraversalResult:
        depth = params.get("depth", 3)
        limit = params.get("limit", 100)
        stmt = (
            f"MATCH path = (n {{id: $node_id}})-[*1..{depth}]-(m) "
            "RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels "
            f"LIMIT {limit}"
        )
        results = await self._execute(stmt, {"node_id": start_node})
        all_nodes: list[dict] = []
        for entry in results:
            for node_item in entry["row"][0] if entry["row"] else []:
                if isinstance(node_item, dict):
                    all_nodes.append(node_item)
        return TraversalResult(path=all_nodes, metadata={"depth": depth, "limit": limit})
