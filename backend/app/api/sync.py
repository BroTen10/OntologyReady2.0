from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from ..api.deps import get_current_user
from ..core.response import error, ok, paged
from ..models.sync import SyncRequest, SyncTaskResponse, SyncLogEntry
from ..models import sync_store as sstore
from ..models import sync_engine

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/run")
async def run_sync(req: SyncRequest, user: dict = Depends(get_current_user)):
    """发起数据同步"""
    task_id = await sstore.create_sync_task(
        req.dataset_id,
        req.config.model_dump(mode="json"),
        [m.model_dump(mode="json") for m in req.mappings],
    )

    # Run in background
    asyncio.create_task(sync_engine.run_sync_task(task_id))

    task = await sstore.get_sync_task(task_id)
    return ok(SyncTaskResponse(**task).model_dump(mode="json") if task else None)


@router.get("/tasks")
async def list_tasks(
    dataset_id: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user),
):
    """获取同步任务列表"""
    items, total = await sstore.list_sync_tasks(dataset_id, status_filter, page, page_size)
    return paged([SyncTaskResponse(**it).model_dump(mode="json") if it else {} for it in items], total, page, page_size)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, user: dict = Depends(get_current_user)):
    """获取同步任务详情"""
    task = await sstore.get_sync_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return ok(SyncTaskResponse(**task).model_dump(mode="json"))


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(get_current_user),
):
    """获取同步任务日志"""
    logs, total = await sstore.get_sync_logs(task_id, page, page_size)
    return paged(
        [SyncLogEntry(**l).model_dump(mode="json") if l else {} for l in logs],
        total, page, page_size,
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, user: dict = Depends(get_current_user)):
    """取消同步任务"""
    success = await sync_engine.cancel_sync_task(task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel task in current state")
    return ok(None, "Task cancelled")


@router.post("/test-connection")
async def test_connection(req: SyncRequest, user: dict = Depends(get_current_user)):
    """测试数据源连接"""
    from ..providers.datasources import get_datasource
    from ..providers.base import DataSourceConfig

    cfg = DataSourceConfig.from_dict(req.config.model_dump(mode="json"))
    adapter = get_datasource(cfg.source_type)
    result = await adapter.test_connection(cfg)
    return ok(result)


@router.get("/tables")
async def list_source_tables(
    source_type: str,
    host: str,
    port: int = 5432,
    database: str = "",
    username: str = "",
    password: str = "",
    schema_name: str = "public",
    user: dict = Depends(get_current_user),
):
    """列出数据源的所有表"""
    from ..providers.datasources import get_datasource
    from ..providers.base import DataSourceConfig

    config = DataSourceConfig(
        source_type=source_type, host=host, port=port,
        database=database, username=username, password=password,
        schema_name=schema_name,
    )
    adapter = get_datasource(source_type)
    await adapter.connect(config)
    try:
        tables = await adapter.list_tables()
        return ok(tables)
    finally:
        await adapter.disconnect()


@router.get("/table-info")
async def get_table_info(
    source_type: str,
    host: str,
    port: int = 5432,
    database: str = "",
    username: str = "",
    password: str = "",
    schema_name: str = "public",
    table: str = "",
    user: dict = Depends(get_current_user),
):
    """获取数据源表结构信息"""
    from ..providers.datasources import get_datasource
    from ..providers.base import DataSourceConfig

    config = DataSourceConfig(
        source_type=source_type, host=host, port=port,
        database=database, username=username, password=password,
        schema_name=schema_name,
    )
    adapter = get_datasource(source_type)
    await adapter.connect(config)
    try:
        info = await adapter.get_table_info(table)
        return ok(info)
    finally:
        await adapter.disconnect()
