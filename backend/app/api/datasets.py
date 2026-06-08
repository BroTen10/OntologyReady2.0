from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.response import error, ok, paged
from ..models import dataset_store
from ..models.dataset import DatasetCreate, DatasetUpdate
from .deps import get_current_user

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("")
async def list_datasets(page: int = 1, page_size: int = 20, _: dict = Depends(get_current_user)):
    items, total = await dataset_store.list_datasets(page, page_size)
    return paged(items, total, page, page_size)


@router.post("")
async def create_dataset(body: DatasetCreate, _: dict = Depends(get_current_user)):
    dataset = await dataset_store.create_dataset(body.display_name, body.description)
    return ok(dataset)


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, _: dict = Depends(get_current_user)):
    ds = await dataset_store.get_dataset(dataset_id)
    if not ds:
        return error(404, "数据集不存在")
    return ok(ds)


@router.put("/{dataset_id}")
async def update_dataset(dataset_id: str, body: DatasetUpdate, _: dict = Depends(get_current_user)):
    ds = await dataset_store.update_dataset(dataset_id, body.display_name, body.description)
    if not ds:
        return error(404, "数据集不存在")
    return ok(ds)


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str, _: dict = Depends(get_current_user)):
    deleted = await dataset_store.delete_dataset(dataset_id)
    if not deleted:
        return error(404, "数据集不存在")
    return ok(None, "已删除")
