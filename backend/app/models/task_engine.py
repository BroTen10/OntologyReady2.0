from __future__ import annotations

import asyncio
from typing import Any

from ..models import modeling_store
from ..models import sync_engine
from ..models import task_store as tstore


async def run_task(task_id: str) -> None:
    """Execute a generic async task by dispatching to the right handler."""
    task = await tstore.get_task(task_id)
    if not task:
        return

    task_type = task["task_type"]
    dataset_id = task["dataset_id"]
    params = task["params"]

    try:
        await tstore.update_task_status(task_id, "running")
        await tstore.add_task_log(task_id, "info", f"开始执行任务: {task_type}")

        if task_type == "analyze_schema":
            result = await _run_analyze_schema(task_id, dataset_id, params)
        elif task_type == "sync_data":
            result = await _run_sync_data(task_id, dataset_id, params)
        elif task_type == "quick_model":
            result = await _run_quick_model(task_id, dataset_id, params)
        elif task_type == "detect_changes":
            result = await _run_detect_changes(task_id, dataset_id, params)
        elif task_type in ("document_parse", "graphrag_run", "rag_eval_run"):
            await tstore.add_task_log(task_id, "warn", f"任务类型 {task_type} 暂未集成队列，请直接调用对应接口")
            result = {"success": True, "message": f"Task type {task_type} not yet integrated with queue"}
        else:
            raise ValueError(f"Unknown task type: {task_type}")

        await tstore.update_task_status(task_id, "completed", progress=100.0, result=result)
        await tstore.add_task_log(task_id, "info", "任务完成")

    except Exception as e:
        await tstore.add_task_log(task_id, "error", str(e))
        await tstore.update_task_status(task_id, "failed", error=str(e))


async def _run_analyze_schema(task_id: str, dataset_id: str, params: dict) -> dict:
    await tstore.add_task_log(task_id, "info", "LLM Schema 分析中…")
    result = await modeling_store.analyze_schema(params)
    return result


async def _run_sync_data(task_id: str, dataset_id: str, params: dict) -> dict:
    sync_task_id = params.get("sync_task_id")
    if sync_task_id:
        await sync_engine.run_sync_task(sync_task_id)
        return {"success": True, "sync_task_id": sync_task_id}
    return {"success": False, "error": "Missing sync_task_id in params"}


async def _run_quick_model(task_id: str, dataset_id: str, params: dict) -> dict:
    await tstore.add_task_log(task_id, "info", "快速建模中…")
    result = await modeling_store.quick_model(params)
    return result


async def _run_detect_changes(task_id: str, dataset_id: str, params: dict) -> dict:
    await tstore.add_task_log(task_id, "info", "检测结构变更中…")
    result = await modeling_store.detect_changes(dataset_id, params)
    return result


async def cancel_task(task_id: str) -> bool:
    """取消任务"""
    task = await tstore.get_task(task_id)
    if not task or task["status"] not in ("pending", "running"):
        return False
    await tstore.update_task_status(task_id, "cancelled")
    await tstore.add_task_log(task_id, "info", "任务已取消")
    return True
