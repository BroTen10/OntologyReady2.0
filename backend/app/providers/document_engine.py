from __future__ import annotations

import uuid
from typing import Any

import asyncpg

from ..config import settings
from .base import (
    Chunk,
    Document,
    DocumentEngineProvider,
    SearchResult,
)


class PostgresDocumentEngine(DocumentEngineProvider):
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

    async def _ensure_tables(self) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS doc_engine_chunks (
                    chunk_id   TEXT PRIMARY KEY,
                    doc_id     TEXT NOT NULL,
                    kb_id      TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    embedding  vector(1536),
                    metadata   JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_engine_chunks_fts
                    ON doc_engine_chunks USING GIN (to_tsvector('simple', content))
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_engine_chunks_vector
                    ON doc_engine_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
            """)

    async def index_document(self, doc: Document, chunks: list[Chunk]) -> None:
        await self._ensure_tables()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM doc_engine_chunks WHERE doc_id = $1", doc.doc_id)
            for c in chunks:
                await conn.execute(
                    """INSERT INTO doc_engine_chunks (chunk_id, doc_id, kb_id, content, metadata)
                       VALUES ($1, $2, $3, $4, $5)""",
                    c.chunk_id, doc.doc_id, doc.kb_id, c.content, c.metadata,
                )

    async def search_fts(self, query: str, top_n: int = 100) -> list[SearchResult]:
        await self._ensure_tables()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT doc_id, chunk_id, content,
                          ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', $1)) AS score
                   FROM doc_engine_chunks
                   WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', $1)
                   ORDER BY score DESC LIMIT $2""",
                query, top_n,
            )
        return [SearchResult(doc_id=r["doc_id"], chunk_id=r["chunk_id"], content=r["content"], score=r["score"]) for r in rows]

    async def search_vector(self, embedding: list[float], top_n: int = 100) -> list[SearchResult]:
        await self._ensure_tables()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT doc_id, chunk_id, content,
                          1 - (embedding <=> $1::vector) AS score
                   FROM doc_engine_chunks
                   WHERE embedding IS NOT NULL
                   ORDER BY embedding <=> $1::vector LIMIT $2""",
                str(embedding), top_n,
            )
        return [SearchResult(doc_id=r["doc_id"], chunk_id=r["chunk_id"], content=r["content"], score=r["score"]) for r in rows]

    async def search_hybrid(self, query: str, embedding: list[float], top_n: int = 100, fts_weight: float = 0.3) -> list[SearchResult]:
        fts_results = await self.search_fts(query, top_n * 2)
        vec_results = await self.search_vector(embedding, top_n * 2)

        vec_scores: dict[str, float] = {}
        for r in vec_results:
            vec_scores[r.chunk_id] = r.score

        merged: list[SearchResult] = []
        for r in fts_results:
            vec_score = vec_scores.pop(r.chunk_id, 0.0)
            r.score = fts_weight * r.score + (1 - fts_weight) * vec_score
            merged.append(r)
        for r in vec_results:
            if r.chunk_id in vec_scores:
                r.score = (1 - fts_weight) * vec_scores[r.chunk_id]
                merged.append(r)

        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:top_n]
