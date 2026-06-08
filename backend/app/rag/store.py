"""Knowledge base, document, and chunk storage for RAG."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from ..database import get_pool


async def _ensure_rag_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_knowledge_bases (
                kb_id       TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                config      JSONB DEFAULT '{}',
                created_at  TIMESTAMPTZ DEFAULT now(),
                updated_at  TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                doc_id      TEXT PRIMARY KEY,
                kb_id       TEXT NOT NULL,
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
            CREATE TABLE IF NOT EXISTS rag_chunks (
                chunk_id    TEXT PRIMARY KEY,
                doc_id      TEXT NOT NULL,
                kb_id       TEXT NOT NULL,
                content     TEXT NOT NULL,
                embedding   vector(1536),
                metadata    JSONB DEFAULT '{}',
                created_at  TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_fts
                ON rag_chunks USING GIN (to_tsvector('simple', content))
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_vector
                ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_conversations (
                conv_id       TEXT PRIMARY KEY,
                kb_id         TEXT NOT NULL,
                title         TEXT DEFAULT '',
                user_id       TEXT DEFAULT '',
                model_params  JSONB DEFAULT '{}',
                system_prompt TEXT DEFAULT '',
                created_at    TIMESTAMPTZ DEFAULT now(),
                updated_at    TIMESTAMPTZ DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_messages (
                msg_id     TEXT PRIMARY KEY,
                conv_id    TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL DEFAULT '',
                citations  JSONB DEFAULT '[]',
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)


# ═══════════════════════════════════════════════════════════
# Knowledge Bases
# ═══════════════════════════════════════════════════════════

async def create_kb(name: str, description: str = "", config: dict | None = None) -> dict:
    await _ensure_rag_tables()
    pool = await get_pool()
    kb_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO rag_knowledge_bases (kb_id, name, description, config, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $5) RETURNING *""",
            kb_id, name, description, json.dumps(config or {}, ensure_ascii=False), now,
        )
    return _kb_row(row)


async def list_kbs() -> list[dict]:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM rag_knowledge_bases ORDER BY created_at DESC")
    return [_kb_row(r) for r in rows]


async def get_kb(kb_id: str) -> dict | None:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM rag_knowledge_bases WHERE kb_id = $1", kb_id)
    return _kb_row(row) if row else None


async def delete_kb(kb_id: str) -> bool:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM rag_chunks WHERE kb_id = $1", kb_id)
        await conn.execute("DELETE FROM rag_documents WHERE kb_id = $1", kb_id)
        result = await conn.execute("DELETE FROM rag_knowledge_bases WHERE kb_id = $1", kb_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Documents
# ═══════════════════════════════════════════════════════════

async def create_document(kb_id: str, filename: str, content: bytes) -> dict:
    await _ensure_rag_tables()
    pool = await get_pool()
    doc_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO rag_documents (doc_id, kb_id, filename, file_size, file_type, status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, 'pending', $6, $6) RETURNING *""",
            doc_id, kb_id, filename, len(content), file_type, now,
        )
    return _doc_row(row)


async def update_document_status(doc_id: str, status: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE rag_documents SET status = $1, updated_at = $2 WHERE doc_id = $3",
            status, datetime.now(UTC), doc_id,
        )


async def list_documents(kb_id: str) -> list[dict]:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM rag_documents WHERE kb_id = $1 ORDER BY created_at DESC", kb_id)
    return [_doc_row(r) for r in rows]


async def get_document(doc_id: str) -> dict | None:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM rag_documents WHERE doc_id = $1", doc_id)
    return _doc_row(row) if row else None


async def delete_document(doc_id: str) -> bool:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM rag_chunks WHERE doc_id = $1", doc_id)
        result = await conn.execute("DELETE FROM rag_documents WHERE doc_id = $1", doc_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Chunks
# ═══════════════════════════════════════════════════════════

async def save_chunks(kb_id: str, doc_id: str, chunks: list[dict]) -> list[dict]:
    await _ensure_rag_tables()
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM rag_chunks WHERE doc_id = $1", doc_id)
        for c in chunks:
            chunk_id = uuid.uuid4().hex[:12]
            await conn.execute(
                """INSERT INTO rag_chunks (chunk_id, doc_id, kb_id, content, metadata)
                   VALUES ($1, $2, $3, $4, $5)""",
                chunk_id, doc_id, kb_id, c["content"],
                json.dumps(c.get("metadata", {}), ensure_ascii=False),
            )
            results.append({"chunk_id": chunk_id, "doc_id": doc_id, "kb_id": kb_id, "content": c["content"]})
    return results


async def update_chunk_embedding(chunk_id: str, embedding: list[float]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE rag_chunks SET embedding = $1::vector WHERE chunk_id = $2",
            str(embedding), chunk_id,
        )


async def search_fts(query: str, kb_id: str | None = None, top_k: int = 10) -> list[dict]:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if kb_id:
            rows = await conn.fetch(
                """SELECT chunk_id, doc_id, kb_id, content, metadata,
                          ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', $1)) AS score
                   FROM rag_chunks WHERE kb_id = $2
                     AND to_tsvector('simple', content) @@ plainto_tsquery('simple', $1)
                   ORDER BY score DESC LIMIT $3""",
                query, kb_id, top_k,
            )
        else:
            rows = await conn.fetch(
                """SELECT chunk_id, doc_id, kb_id, content, metadata,
                          ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', $1)) AS score
                   FROM rag_chunks
                   WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', $1)
                   ORDER BY score DESC LIMIT $2""",
                query, top_k,
            )
    return [_chunk_row(r) for r in rows]


async def search_vector(embedding: list[float], kb_id: str | None = None, top_k: int = 10) -> list[dict]:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if kb_id:
            rows = await conn.fetch(
                """SELECT chunk_id, doc_id, kb_id, content, metadata,
                          1 - (embedding <=> $1::vector) AS score
                   FROM rag_chunks WHERE kb_id = $2 AND embedding IS NOT NULL
                   ORDER BY embedding <=> $1::vector LIMIT $3""",
                str(embedding), kb_id, top_k,
            )
        else:
            rows = await conn.fetch(
                """SELECT chunk_id, doc_id, kb_id, content, metadata,
                          1 - (embedding <=> $1::vector) AS score
                   FROM rag_chunks WHERE embedding IS NOT NULL
                   ORDER BY embedding <=> $1::vector LIMIT $2""",
                str(embedding), top_k,
            )
    return [_chunk_row(r) for r in rows]


async def get_chunks_by_doc(doc_id: str) -> list[dict]:
    """Get all chunks for a specific document."""
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM rag_chunks WHERE doc_id = $1 ORDER BY created_at",
            doc_id,
        )
    return [_chunk_row(r) for r in rows]


async def count_chunks(kb_id: str) -> int:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT count(*) FROM rag_chunks WHERE kb_id = $1", kb_id)


# ═══════════════════════════════════════════════════════════
# Conversations
# ═══════════════════════════════════════════════════════════

async def create_conversation(kb_id: str, title: str = "", user_id: str = "",
                              model_params: dict | None = None, system_prompt: str = "") -> dict:
    await _ensure_rag_tables()
    pool = await get_pool()
    conv_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO rag_conversations (conv_id, kb_id, title, user_id, model_params, system_prompt, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $7) RETURNING *""",
            conv_id, kb_id, title, user_id,
            json.dumps(model_params or {}, ensure_ascii=False), system_prompt, now,
        )
    return _conv_row(row)


async def list_conversations(user_id: str = "") -> list[dict]:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            rows = await conn.fetch(
                "SELECT * FROM rag_conversations WHERE user_id = $1 ORDER BY updated_at DESC", user_id)
        else:
            rows = await conn.fetch("SELECT * FROM rag_conversations ORDER BY updated_at DESC")
    return [_conv_row(r) for r in rows]


async def get_conversation(conv_id: str) -> dict | None:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM rag_conversations WHERE conv_id = $1", conv_id)
    return _conv_row(row) if row else None


async def delete_conversation(conv_id: str) -> bool:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM rag_messages WHERE conv_id = $1", conv_id)
        result = await conn.execute("DELETE FROM rag_conversations WHERE conv_id = $1", conv_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Messages
# ═══════════════════════════════════════════════════════════

async def save_message(conv_id: str, role: str, content: str,
                       citations: list[dict] | None = None) -> dict:
    await _ensure_rag_tables()
    pool = await get_pool()
    msg_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO rag_messages (msg_id, conv_id, role, content, citations, created_at)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
            msg_id, conv_id, role, content,
            json.dumps(citations or [], ensure_ascii=False), now,
        )
        await conn.execute(
            "UPDATE rag_conversations SET updated_at = $1 WHERE conv_id = $2", now, conv_id)
    return _msg_row(row)


async def get_messages_by_conversation(conv_id: str) -> list[dict]:
    await _ensure_rag_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM rag_messages WHERE conv_id = $1 ORDER BY created_at", conv_id)
    return [_msg_row(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _kb_row(row) -> dict:
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


def _chunk_row(row) -> dict:
    d = dict(row)
    for k in ("metadata",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def _conv_row(row) -> dict:
    d = dict(row)
    for k in ("model_params",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    for ts in ("created_at", "updated_at"):
        if d.get(ts):
            d[ts] = d[ts].isoformat()
    return d


def _msg_row(row) -> dict:
    d = dict(row)
    for k in ("citations",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d
