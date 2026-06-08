from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import settings
from .base import (
    Chunk,
    Document,
    DocumentEngineProvider,
    SearchResult,
)


class OpenSearchDocumentEngine(DocumentEngineProvider):
    """Document engine backed by OpenSearch (full-text + vector + hybrid search)."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or settings.get_provider_config().get("document_engine", {}).get("config", {})
        self.endpoint = cfg.get("endpoint", "http://localhost:9200")
        self.username = cfg.get("username", "admin")
        self.password = cfg.get("password", "admin")
        self.index_name = cfg.get("index_name", "doc_engine_chunks")
        self._client: httpx.AsyncClient | None = None

    def _auth(self) -> tuple[str, str] | None:
        if self.username and self.password:
            return (self.username, self.password)
        return None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.endpoint,
                auth=self._auth(),
                timeout=30,
            )
        return self._client

    async def _ensure_index(self) -> None:
        client = await self._get_client()
        resp = await client.head(f"/{self.index_name}")
        if resp.status_code == 404:
            await client.put(
                f"/{self.index_name}",
                json={
                    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                    "mappings": {
                        "properties": {
                            "chunk_id": {"type": "keyword"},
                            "doc_id": {"type": "keyword"},
                            "kb_id": {"type": "keyword"},
                            "content": {"type": "text", "analyzer": "standard"},
                            "embedding": {"type": "dense_vector", "dims": 1536},
                            "metadata": {"type": "object"},
                        }
                    },
                },
            )
            resp.raise_for_status()

    async def index_document(self, doc: Document, chunks: list[Chunk]) -> None:
        await self._ensure_index()
        client = await self._get_client()
        # Delete existing chunks for this doc
        await client.post(
            f"/{self.index_name}/_delete_by_query",
            json={"query": {"term": {"doc_id": doc.doc_id}}},
        )
        # Bulk index new chunks
        if not chunks:
            return
        bulk_body: list[dict] = []
        for c in chunks:
            bulk_body.append({"index": {"_id": c.chunk_id}})
            bulk_body.append({
                "chunk_id": c.chunk_id,
                "doc_id": doc.doc_id,
                "kb_id": doc.kb_id,
                "content": c.content,
                "metadata": c.metadata or {},
            })
        lines = "\n".join(
            json.dumps(item, ensure_ascii=False) for item in bulk_body
        ) + "\n"
        resp = await client.post(
            "/_bulk",
            content=lines,
            headers={"Content-Type": "application/x-ndjson"},
        )
        resp.raise_for_status()

    async def search_fts(self, query: str, top_n: int = 100) -> list[SearchResult]:
        await self._ensure_index()
        client = await self._get_client()
        resp = await client.post(
            f"/{self.index_name}/_search",
            json={
                "size": top_n,
                "query": {"match": {"content": query}},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                doc_id=h["_source"]["doc_id"],
                chunk_id=h["_source"]["chunk_id"],
                content=h["_source"]["content"],
                score=h["_score"],
            )
            for h in data["hits"]["hits"]
        ]

    async def search_vector(self, embedding: list[float], top_n: int = 100) -> list[SearchResult]:
        await self._ensure_index()
        client = await self._get_client()
        resp = await client.post(
            f"/{self.index_name}/_search",
            json={
                "size": top_n,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": embedding},
                        },
                    }
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                doc_id=h["_source"]["doc_id"],
                chunk_id=h["_source"]["chunk_id"],
                content=h["_source"]["content"],
                score=h["_score"],
            )
            for h in data["hits"]["hits"]
        ]

    async def search_hybrid(
        self,
        query: str,
        embedding: list[float],
        top_n: int = 100,
        fts_weight: float = 0.3,
    ) -> list[SearchResult]:
        await self._ensure_index()
        client = await self._get_client()
        resp = await client.post(
            f"/{self.index_name}/_search",
            json={
                "size": top_n,
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"content": query}},
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                        "params": {"query_vector": embedding},
                                    },
                                }
                            },
                        ]
                    }
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        max_score = max((h["_score"] for h in data["hits"]["hits"]), default=1.0)
        return [
            SearchResult(
                doc_id=h["_source"]["doc_id"],
                chunk_id=h["_source"]["chunk_id"],
                content=h["_source"]["content"],
                score=h["_score"] / max_score if max_score else 0.0,
            )
            for h in data["hits"]["hits"]
        ]
