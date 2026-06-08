from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from ..api.deps import get_current_user
from ..core.response import error, ok, paged
from ..models.tasks import TaskRequest, TaskResponse, TaskLogEntry
from ..models import task_store as tstore
from ..models import task_engine

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("")
async def create_task(req: TaskRequest, user: dict = Depends(get_current_user)):
    """创建异步任务"""
    task_id = await tstore.create_task(req.task_type, req.dataset_id, req.params)

    # Run in background
    asyncio.create_task(task_engine.run_task(task_id))

    task = await tstore.get_task(task_id)
    return ok(TaskResponse(**task).model_dump(mode="json") if task else None)


@router.get("")
async def list_tasks(
    dataset_id: str | None = None,
    status: str | None = None,
    task_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user),
):
    """获取任务列表"""
    items, total = await tstore.list_tasks(dataset_id, status, task_type, page, page_size)
    return paged(
        [TaskResponse(**it).model_dump(mode="json") if it else {} for it in items],
        total, page, page_size,
    )


@router.get("/{task_id}")
async def get_task(task_id: str, user: dict = Depends(get_current_user)):
    """获取任务详情"""
    task = await tstore.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return ok(TaskResponse(**task).model_dump(mode="json"))


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(get_current_user),
):
    """获取任务日志"""
    logs, total = await tstore.get_task_logs(task_id, page, page_size)
    return paged(
        [TaskLogEntry(**l).model_dump(mode="json") if l else {} for l in logs],
        total, page, page_size,
    )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, user: dict = Depends(get_current_user)):
    """取消任务"""
    success = await task_engine.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel task in current state")
    return ok(None, "Task cancelled")
