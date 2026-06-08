"""RAG Evaluation API endpoints."""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field

from ..core.response import error, ok, paged
from ..providers.factory import get_rag
from ..rag import evaluation as eval_engine
from ..rag import evaluation_store as es
from .deps import get_current_user

router = APIRouter(prefix="/api/rag-evaluation", tags=["rag-evaluation"])


# ── Request / Response Models ─────────────────────────────

class DatasetCreateReq(BaseModel):
    name: str
    description: str = ""
    kb_id: str | None = None


class QuestionAddReq(BaseModel):
    question: str
    reference_answer: str = ""
    sort_order: int = 0


class QuestionsBulkReq(BaseModel):
    questions: list[dict] = Field(default_factory=list)


class RunCreateReq(BaseModel):
    dataset_id: str
    kb_id: str
    name: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class CompareReq(BaseModel):
    run_ids: list[str] = Field(..., min_length=1, max_length=5)


# ═══════════════════════════════════════════════════════════
# Datasets
# ═══════════════════════════════════════════════════════════

@router.get("/datasets")
async def list_datasets(_: dict = Depends(get_current_user)):
    datasets = await es.list_datasets()
    for d in datasets:
        questions = await es.list_questions(d["dataset_id"])
        d["question_count"] = len(questions)
    return ok(datasets)


@router.post("/datasets")
async def create_dataset(body: DatasetCreateReq, _: dict = Depends(get_current_user)):
    ds = await es.create_dataset(body.name, body.description, body.kb_id)
    return ok({"dataset_id": ds["dataset_id"], "name": ds["name"]})


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, _: dict = Depends(get_current_user)):
    ds = await es.get_dataset(dataset_id)
    if not ds:
        return error(404, "评测数据集不存在")
    questions = await es.list_questions(dataset_id)
    ds["questions"] = questions
    ds["question_count"] = len(questions)
    return ok(ds)


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, _: dict = Depends(get_current_user)):
    deleted = await es.delete_dataset(dataset_id)
    if not deleted:
        return error(404, "评测数据集不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Questions
# ═══════════════════════════════════════════════════════════

@router.post("/datasets/{dataset_id}/questions")
async def add_question(dataset_id: str, body: QuestionAddReq, _: dict = Depends(get_current_user)):
    q = await es.add_question(dataset_id, body.question, body.reference_answer, body.sort_order)
    return ok(q)


@router.post("/datasets/{dataset_id}/questions/bulk")
async def add_questions_bulk(dataset_id: str, body: QuestionsBulkReq, _: dict = Depends(get_current_user)):
    questions = await es.add_questions_bulk(dataset_id, body.questions)
    return ok({"added": len(questions)})


@router.post("/datasets/{dataset_id}/questions/upload")
async def upload_questions_csv(
    dataset_id: str,
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    questions = []
    for row in reader:
        questions.append({
            "question": row.get("question", ""),
            "reference_answer": row.get("reference_answer", ""),
            "sort_order": len(questions),
        })
    if not questions:
        return error(400, "CSV 文件中未找到有效问题")
    await es.add_questions_bulk(dataset_id, questions)
    return ok({"added": len(questions)})


@router.delete("/questions/{question_id}")
async def delete_question(question_id: str, _: dict = Depends(get_current_user)):
    deleted = await es.delete_question(question_id)
    if not deleted:
        return error(404, "问题不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Runs
# ═══════════════════════════════════════════════════════════

@router.get("/runs")
async def list_runs(dataset_id: str | None = None, _: dict = Depends(get_current_user)):
    runs = await es.list_runs(dataset_id)
    return ok(runs)


@router.post("/runs")
async def create_run(body: RunCreateReq, _: dict = Depends(get_current_user)):
    # Validate dataset exists
    ds = await es.get_dataset(body.dataset_id)
    if not ds:
        return error(404, "评测数据集不存在")

    run = await es.create_run(body.dataset_id, body.kb_id, body.name, body.config)

    # Collect questions
    questions = await es.list_questions(body.dataset_id)
    if not questions:
        await es.update_run_status(run["run_id"], "failed", {"error": "数据集无问题"})
        return error(400, "数据集不包含任何问题")

    # Run evaluation asynchronously
    rag = get_rag()
    summary = await eval_engine.run_evaluation(rag, run["run_id"], questions, body.kb_id)

    return ok({"run_id": run["run_id"], "status": "completed", "summary": summary})


@router.get("/runs/{run_id}")
async def get_run(run_id: str, _: dict = Depends(get_current_user)):
    run = await es.get_run(run_id)
    if not run:
        return error(404, "评测运行不存在")
    results = await es.list_results(run_id)
    run["results"] = results
    return ok(run)


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str, _: dict = Depends(get_current_user)):
    deleted = await es.delete_run(run_id)
    if not deleted:
        return error(404, "评测运行不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════

@router.get("/runs/{run_id}/results")
async def get_results(run_id: str, _: dict = Depends(get_current_user)):
    run = await es.get_run(run_id)
    if not run:
        return error(404, "评测运行不存在")
    results = await es.list_results(run_id)
    return ok({"run": run, "results": results})


# ═══════════════════════════════════════════════════════════
# Compare
# ═══════════════════════════════════════════════════════════

@router.post("/runs/compare")
async def compare_runs(body: CompareReq, _: dict = Depends(get_current_user)):
    """Compare metrics across multiple evaluation runs."""
    runs_data = []
    for run_id in body.run_ids:
        run = await es.get_run(run_id)
        if not run:
            return error(404, f"评测运行 {run_id} 不存在")
        results = await es.list_results(run_id)
        run["results"] = results
        runs_data.append(run)

    # Build comparison table
    comparison = []
    for run in runs_data:
        summary = run.get("summary", {})
        comparison.append({
            "run_id": run["run_id"],
            "name": run.get("name", ""),
            "status": run["status"],
            "total_questions": summary.get("total_questions", 0),
            "accuracy_avg": summary.get("accuracy_avg"),
            "recall_avg": summary.get("recall_avg"),
            "citation_accuracy_avg": summary.get("citation_accuracy_avg"),
            "latency_ms_avg": summary.get("latency_ms_avg"),
            "created_at": run.get("created_at"),
        })

    return ok({"runs": comparison})
