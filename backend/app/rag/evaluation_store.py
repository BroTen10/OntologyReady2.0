"""RAG evaluation storage — datasets, runs, results."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from ..database import get_pool


async def _ensure_eval_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_datasets (
                dataset_id  TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                kb_id       TEXT,
                metadata    JSONB DEFAULT '{}',
                created_at  TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_questions (
                question_id TEXT PRIMARY KEY,
                dataset_id  TEXT NOT NULL,
                question    TEXT NOT NULL,
                reference_answer TEXT DEFAULT '',
                metadata    JSONB DEFAULT '{}',
                sort_order  INT DEFAULT 0,
                created_at  TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                run_id      TEXT PRIMARY KEY,
                dataset_id  TEXT NOT NULL,
                kb_id       TEXT NOT NULL,
                name        TEXT DEFAULT '',
                status      TEXT DEFAULT 'pending',
                config      JSONB DEFAULT '{}',
                summary     JSONB DEFAULT '{}',
                started_at  TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                created_at  TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS eval_results (
                result_id   TEXT PRIMARY KEY,
                run_id      TEXT NOT NULL,
                question_id TEXT NOT NULL,
                question    TEXT NOT NULL,
                reference_answer TEXT DEFAULT '',
                generated_answer TEXT DEFAULT '',
                retrieved_chunks JSONB DEFAULT '[]',
                metrics     JSONB DEFAULT '{}',
                latency_ms  FLOAT DEFAULT 0,
                created_at  TIMESTAMPTZ DEFAULT now()
            )
        """)


# ═══════════════════════════════════════════════════════════
# Datasets
# ═══════════════════════════════════════════════════════════

async def create_dataset(name: str, description: str = "", kb_id: str | None = None) -> dict:
    await _ensure_eval_tables()
    pool = await get_pool()
    dataset_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO eval_datasets (dataset_id, name, description, kb_id, created_at)
               VALUES ($1, $2, $3, $4, $5) RETURNING *""",
            dataset_id, name, description, kb_id, now,
        )
    return _dataset_row(row)


async def list_datasets() -> list[dict]:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM eval_datasets ORDER BY created_at DESC")
    return [_dataset_row(r) for r in rows]


async def get_dataset(dataset_id: str) -> dict | None:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM eval_datasets WHERE dataset_id = $1", dataset_id)
    return _dataset_row(row) if row else None


async def delete_dataset(dataset_id: str) -> bool:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM eval_questions WHERE dataset_id = $1", dataset_id)
        await conn.execute("DELETE FROM eval_results WHERE run_id IN (SELECT run_id FROM eval_runs WHERE dataset_id = $1)", dataset_id)
        await conn.execute("DELETE FROM eval_runs WHERE dataset_id = $1", dataset_id)
        result = await conn.execute("DELETE FROM eval_datasets WHERE dataset_id = $1", dataset_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Questions
# ═══════════════════════════════════════════════════════════

async def add_question(dataset_id: str, question: str, reference_answer: str = "", sort_order: int = 0) -> dict:
    await _ensure_eval_tables()
    pool = await get_pool()
    question_id = uuid.uuid4().hex[:12]
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO eval_questions (question_id, dataset_id, question, reference_answer, sort_order)
               VALUES ($1, $2, $3, $4, $5) RETURNING *""",
            question_id, dataset_id, question, reference_answer, sort_order,
        )
    return _question_row(row)


async def add_questions_bulk(dataset_id: str, questions: list[dict]) -> list[dict]:
    await _ensure_eval_tables()
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        for i, q in enumerate(questions):
            question_id = uuid.uuid4().hex[:12]
            row = await conn.fetchrow(
                """INSERT INTO eval_questions (question_id, dataset_id, question, reference_answer, sort_order)
                   VALUES ($1, $2, $3, $4, $5) RETURNING *""",
                question_id, dataset_id, q.get("question", ""),
                q.get("reference_answer", ""), q.get("sort_order", i),
            )
            results.append(_question_row(row))
    return results


async def list_questions(dataset_id: str) -> list[dict]:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM eval_questions WHERE dataset_id = $1 ORDER BY sort_order, created_at",
            dataset_id,
        )
    return [_question_row(r) for r in rows]


async def delete_question(question_id: str) -> bool:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM eval_questions WHERE question_id = $1", question_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Runs
# ═══════════════════════════════════════════════════════════

async def create_run(dataset_id: str, kb_id: str, name: str = "", config: dict | None = None) -> dict:
    await _ensure_eval_tables()
    pool = await get_pool()
    run_id = uuid.uuid4().hex[:12]
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO eval_runs (run_id, dataset_id, kb_id, name, status, config, created_at)
               VALUES ($1, $2, $3, $4, 'pending', $5, $6) RETURNING *""",
            run_id, dataset_id, kb_id, name, json.dumps(config or {}, ensure_ascii=False), now,
        )
    return _run_row(row)


async def update_run_status(run_id: str, status: str, summary: dict | None = None) -> None:
    pool = await get_pool()
    now = datetime.now(UTC)
    extra = ""
    args: list = [status]
    if summary is not None:
        extra += ", summary = $3"
        args.append(json.dumps(summary, ensure_ascii=False))
    if status == "running":
        extra += ", started_at = $" + str(len(args) + 1)
        args.append(now)
    if status in ("completed", "failed"):
        extra += ", finished_at = $" + str(len(args) + 1)
        args.append(now)
    args.append(run_id)
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE eval_runs SET status = $1{extra} WHERE run_id = ${len(args)}",
            *args,
        )


async def list_runs(dataset_id: str | None = None) -> list[dict]:
    await _ensure_eval_tables()
    pool = await get_pool()
    if dataset_id:
        rows = await conn_fetch("SELECT * FROM eval_runs WHERE dataset_id = $1 ORDER BY created_at DESC", dataset_id)
    else:
        rows = await conn_fetch("SELECT * FROM eval_runs ORDER BY created_at DESC")
    return [_run_row(r) for r in rows]


async def get_run(run_id: str) -> dict | None:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM eval_runs WHERE run_id = $1", run_id)
    return _run_row(row) if row else None


async def delete_run(run_id: str) -> bool:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM eval_results WHERE run_id = $1", run_id)
        result = await conn.execute("DELETE FROM eval_runs WHERE run_id = $1", run_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════

async def save_result(
    run_id: str, question_id: str, question: str,
    generated_answer: str, reference_answer: str = "",
    retrieved_chunks: list | None = None, metrics: dict | None = None,
    latency_ms: float = 0,
) -> dict:
    await _ensure_eval_tables()
    pool = await get_pool()
    result_id = uuid.uuid4().hex[:12]
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO eval_results (result_id, run_id, question_id, question,
               reference_answer, generated_answer, retrieved_chunks, metrics, latency_ms)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING *""",
            result_id, run_id, question_id, question,
            reference_answer, generated_answer,
            json.dumps(retrieved_chunks or [], ensure_ascii=False),
            json.dumps(metrics or {}, ensure_ascii=False),
            latency_ms,
        )
    return _result_row(row)


async def list_results(run_id: str) -> list[dict]:
    await _ensure_eval_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM eval_results WHERE run_id = $1 ORDER BY created_at",
            run_id,
        )
    return [_result_row(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

async def conn_fetch(query: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


def _json_field(d: dict, key: str) -> dict:
    if key in d and isinstance(d[key], str):
        try:
            d[key] = json.loads(d[key])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def _iso_dates(d: dict, *fields: str) -> dict:
    for f in fields:
        if d.get(f):
            d[f] = d[f].isoformat()
    return d


def _dataset_row(row) -> dict:
    d = _iso_dates(dict(row), "created_at")
    return _json_field(d, "metadata")


def _question_row(row) -> dict:
    d = _iso_dates(dict(row), "created_at")
    return _json_field(d, "metadata")


def _run_row(row) -> dict:
    d = _iso_dates(dict(row), "started_at", "finished_at", "created_at")
    d = _json_field(d, "config")
    return _json_field(d, "summary")


def _result_row(row) -> dict:
    d = _iso_dates(dict(row), "created_at")
    d = _json_field(d, "retrieved_chunks")
    return _json_field(d, "metrics")
