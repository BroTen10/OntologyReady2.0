"""RAG evaluation metrics and run engine."""
from __future__ import annotations

import time
from typing import Any

from ..providers.base import RAGProvider
from ..rag import evaluation_store as es


def compute_metrics(
    question: str,
    generated_answer: str,
    reference_answer: str,
    retrieved_chunks: list[dict],
    latency_ms: float,
) -> dict[str, Any]:
    """Compute all evaluation metrics for a single Q&A pair."""

    # 1. Answer accuracy — simple token overlap with reference
    accuracy = _token_overlap(generated_answer, reference_answer) if reference_answer else None

    # 2. Recall — how many chunks contain content from the reference answer
    recall = _recall_score(retrieved_chunks, reference_answer) if reference_answer else None

    # 3. Citation accuracy — how many chunks are actually relevant to the answer
    citation = _citation_relevance(retrieved_chunks, generated_answer)

    return {
        "accuracy": round(accuracy, 4) if accuracy is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "citation_accuracy": round(citation, 4),
        "latency_ms": round(latency_ms, 2),
    }


def aggregate_metrics(results: list[dict]) -> dict[str, Any]:
    """Aggregate per-question metrics into run-level summary."""
    if not results:
        return {"total_questions": 0}

    metric_keys = ["accuracy", "recall", "citation_accuracy", "latency_ms"]
    agg: dict[str, Any] = {"total_questions": len(results)}

    for key in metric_keys:
        values = [r[key] for r in results if r.get(key) is not None]
        if values:
            agg[f"{key}_avg"] = round(sum(values) / len(values), 4)
            agg[f"{key}_min"] = round(min(values), 4)
            agg[f"{key}_max"] = round(max(values), 4)

    # Per-question detail
    agg["questions"] = [
        {
            "question": r["question"],
            "accuracy": r.get("accuracy"),
            "recall": r.get("recall"),
            "citation_accuracy": r.get("citation_accuracy"),
            "latency_ms": r.get("latency_ms"),
        }
        for r in results
    ]
    return agg


async def run_evaluation(
    rag: RAGProvider,
    run_id: str,
    questions: list[dict],
    kb_id: str,
) -> dict[str, Any]:
    """Execute a full evaluation run: ask each question, score, save."""
    await es.update_run_status(run_id, "running")

    results = []
    try:
        for q in questions:
            start = time.perf_counter()

            # Search
            search_results = await rag.search(kb_id, q["question"], top_k=10)

            # Chat / QA
            resp = await rag.chat(kb_id, q["question"])
            latency_ms = (time.perf_counter() - start) * 1000

            retrieved = [
                {"chunk_id": r.chunk_id, "content": r.content, "score": r.score}
                for r in search_results
            ]

            metrics = compute_metrics(
                question=q["question"],
                generated_answer=resp.content,
                reference_answer=q.get("reference_answer", ""),
                retrieved_chunks=retrieved,
                latency_ms=latency_ms,
            )

            result = await es.save_result(
                run_id=run_id,
                question_id=q["question_id"],
                question=q["question"],
                generated_answer=resp.content,
                reference_answer=q.get("reference_answer", ""),
                retrieved_chunks=retrieved,
                metrics=metrics,
                latency_ms=latency_ms,
            )
            results.append({**result, **metrics})

        summary = aggregate_metrics(results)
        await es.update_run_status(run_id, "completed", summary)
        return summary

    except Exception as e:
        summary = aggregate_metrics(results)
        summary["error"] = str(e)
        await es.update_run_status(run_id, "failed", summary)
        return summary


def _token_overlap(text: str, reference: str) -> float:
    """Simple token-overlap accuracy score."""
    ref_tokens = set(reference.lower().split())
    if not ref_tokens:
        return 0.0
    gen_tokens = set(text.lower().split())
    return len(gen_tokens & ref_tokens) / len(ref_tokens)


def _recall_score(chunks: list[dict], reference: str) -> float:
    """How well the retrieved chunks cover the reference answer tokens."""
    ref_tokens = set(reference.lower().split())
    if not ref_tokens or not chunks:
        return 0.0
    chunk_text = " ".join(c.get("content", "") for c in chunks).lower()
    chunk_tokens = set(chunk_text.split())
    return len(ref_tokens & chunk_tokens) / len(ref_tokens)


def _citation_relevance(chunks: list[dict], answer: str) -> float:
    """Fraction of chunks that overlap with the generated answer."""
    if not chunks:
        return 0.0
    answer_tokens = set(answer.lower().split())
    if not answer_tokens:
        return 0.0
    relevant = 0
    for c in chunks:
        chunk_tokens = set(c.get("content", "").lower().split())
        if answer_tokens & chunk_tokens:
            relevant += 1
    return relevant / len(chunks)
