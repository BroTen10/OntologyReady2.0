from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.response import error, ok, paged
from ..models import ontology_store
from ..models.ontology import (
    ActionTypeCreate,
    ActionTypeUpdate,
    BatchActionTypeRequest,
    BatchLinkTypeRequest,
    BatchObjectTypeRequest,
    LinkTypeCreate,
    LinkTypeUpdate,
    ObjectTypeCreate,
    ObjectTypeUpdate,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/datasets/{dataset_id}/ontology", tags=["ontology"])


# ═══════════════════════════════════════════════════════════
# Object Types
# ═══════════════════════════════════════════════════════════

@router.get("/object-types")
async def list_object_types(dataset_id: str, page: int = 1, page_size: int = 100, _: dict = Depends(get_current_user)):
    items, total = await ontology_store.list_object_types(dataset_id, page, page_size)
    return paged(items, total, page, page_size)


@router.post("/object-types")
async def create_object_type(dataset_id: str, body: ObjectTypeCreate, _: dict = Depends(get_current_user)):
    existing = await ontology_store.get_object_type(dataset_id, body.type_name)
    if existing:
        return error(409, "对象类型已存在")
    result = await ontology_store.create_object_type(dataset_id, body.model_dump())
    return ok(result)


@router.post("/object-types/batch")
async def batch_create_object_types(dataset_id: str, body: BatchObjectTypeRequest, _: dict = Depends(get_current_user)):
    results = await ontology_store.batch_create_object_types(dataset_id, [it.model_dump() for it in body.items])
    return ok(results)


@router.get("/object-types/{type_name}")
async def get_object_type(dataset_id: str, type_name: str, _: dict = Depends(get_current_user)):
    result = await ontology_store.get_object_type(dataset_id, type_name)
    if not result:
        return error(404, "对象类型不存在")
    return ok(result)


@router.put("/object-types/{type_name}")
async def update_object_type(dataset_id: str, type_name: str, body: ObjectTypeUpdate, _: dict = Depends(get_current_user)):
    result = await ontology_store.update_object_type(dataset_id, type_name, body.model_dump(exclude_none=True))
    if not result:
        return error(404, "对象类型不存在")
    return ok(result)


@router.delete("/object-types/{type_name}")
async def delete_object_type(dataset_id: str, type_name: str, _: dict = Depends(get_current_user)):
    deleted = await ontology_store.delete_object_type(dataset_id, type_name)
    if not deleted:
        return error(404, "对象类型不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Link Types
# ═══════════════════════════════════════════════════════════

@router.get("/link-types")
async def list_link_types(dataset_id: str, page: int = 1, page_size: int = 100, _: dict = Depends(get_current_user)):
    items, total = await ontology_store.list_link_types(dataset_id, page, page_size)
    return paged(items, total, page, page_size)


@router.post("/link-types")
async def create_link_type(dataset_id: str, body: LinkTypeCreate, _: dict = Depends(get_current_user)):
    existing = await ontology_store.get_link_type(dataset_id, body.link_name)
    if existing:
        return error(409, "链接类型已存在")
    result = await ontology_store.create_link_type(dataset_id, body.model_dump())
    return ok(result)


@router.post("/link-types/batch")
async def batch_create_link_types(dataset_id: str, body: BatchLinkTypeRequest, _: dict = Depends(get_current_user)):
    results = await ontology_store.batch_create_link_types(dataset_id, [it.model_dump() for it in body.items])
    return ok(results)


@router.get("/link-types/{link_name}")
async def get_link_type(dataset_id: str, link_name: str, _: dict = Depends(get_current_user)):
    result = await ontology_store.get_link_type(dataset_id, link_name)
    if not result:
        return error(404, "链接类型不存在")
    return ok(result)


@router.put("/link-types/{link_name}")
async def update_link_type(dataset_id: str, link_name: str, body: LinkTypeUpdate, _: dict = Depends(get_current_user)):
    result = await ontology_store.update_link_type(dataset_id, link_name, body.model_dump(exclude_none=True))
    if not result:
        return error(404, "链接类型不存在")
    return ok(result)


@router.delete("/link-types/{link_name}")
async def delete_link_type(dataset_id: str, link_name: str, _: dict = Depends(get_current_user)):
    deleted = await ontology_store.delete_link_type(dataset_id, link_name)
    if not deleted:
        return error(404, "链接类型不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Action Types
# ═══════════════════════════════════════════════════════════

@router.get("/action-types")
async def list_action_types(dataset_id: str, page: int = 1, page_size: int = 100, _: dict = Depends(get_current_user)):
    items, total = await ontology_store.list_action_types(dataset_id, page, page_size)
    return paged(items, total, page, page_size)


@router.post("/action-types")
async def create_action_type(dataset_id: str, body: ActionTypeCreate, _: dict = Depends(get_current_user)):
    existing = await ontology_store.get_action_type(dataset_id, body.action_name)
    if existing:
        return error(409, "动作类型已存在")
    result = await ontology_store.create_action_type(dataset_id, body.model_dump())
    return ok(result)


@router.post("/action-types/batch")
async def batch_create_action_types(dataset_id: str, body: BatchActionTypeRequest, _: dict = Depends(get_current_user)):
    results = await ontology_store.batch_create_action_types(dataset_id, [it.model_dump() for it in body.items])
    return ok(results)


@router.get("/action-types/{action_name}")
async def get_action_type(dataset_id: str, action_name: str, _: dict = Depends(get_current_user)):
    result = await ontology_store.get_action_type(dataset_id, action_name)
    if not result:
        return error(404, "动作类型不存在")
    return ok(result)


@router.put("/action-types/{action_name}")
async def update_action_type(dataset_id: str, action_name: str, body: ActionTypeUpdate, _: dict = Depends(get_current_user)):
    result = await ontology_store.update_action_type(dataset_id, action_name, body.model_dump(exclude_none=True))
    if not result:
        return error(404, "动作类型不存在")
    return ok(result)


@router.delete("/action-types/{action_name}")
async def delete_action_type(dataset_id: str, action_name: str, _: dict = Depends(get_current_user)):
    deleted = await ontology_store.delete_action_type(dataset_id, action_name)
    if not deleted:
        return error(404, "动作类型不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Data Sources (mapping between tables and ontology)
# ═══════════════════════════════════════════════════════════

@router.get("/data-sources")
async def list_data_sources(dataset_id: str, _: dict = Depends(get_current_user)):
    """列出已注册本体定义对应的数据源表映射"""
    object_types, _ = await ontology_store.list_object_types(dataset_id, page=1, page_size=10000)
    result = []
    for ot in object_types:
        source = ot.get("source") or {}
        if isinstance(source, dict):
            result.append({
                "table_name": source.get("table", ""),
                "object_type": ot.get("type_name", ""),
                "status": "registered",
            })
    return ok(result)
