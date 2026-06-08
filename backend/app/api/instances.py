from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.response import error, ok, paged
from ..models import instance_store
from ..models.instance import (
    BatchLinksRequest,
    BatchObjectsRequest,
    LinkInstanceCreate,
    LinkInstanceUpdate,
    ObjectInstanceCreate,
    ObjectInstanceUpdate,
    ObjectSearchRequest,
    PathRequest,
    TraverseRequest,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/datasets/{dataset_id}/ontology", tags=["instances"])


# ═══════════════════════════════════════════════════════════
# Object Instances
# ═══════════════════════════════════════════════════════════

@router.get("/objects")
async def list_objects(dataset_id: str, page: int = 1, page_size: int = 20,
                       object_type: str | None = None, _: dict = Depends(get_current_user)):
    items, total = await instance_store.list_objects(dataset_id, page, page_size, object_type)
    return paged(items, total, page, page_size)


@router.post("/objects/search")
async def search_objects(dataset_id: str, body: ObjectSearchRequest, _: dict = Depends(get_current_user)):
    items, total = await instance_store.search_objects(
        dataset_id, body.object_type, body.query, body.filters, body.page, body.page_size,
    )
    items = items or []
    return paged(items, total, body.page, body.page_size)


@router.post("/objects")
async def create_object(dataset_id: str, body: ObjectInstanceCreate, _: dict = Depends(get_current_user)):
    result = await instance_store.create_object(dataset_id, body.model_dump())
    return ok(result)


@router.post("/objects/batch")
async def batch_create_objects(dataset_id: str, body: BatchObjectsRequest, _: dict = Depends(get_current_user)):
    results = await instance_store.batch_create_objects(dataset_id, [it.model_dump() for it in body.items])
    return ok(results)


@router.get("/objects/{object_id}")
async def get_object(dataset_id: str, object_id: str, _: dict = Depends(get_current_user)):
    result = await instance_store.get_object(dataset_id, object_id)
    if not result:
        return error(404, "对象不存在")
    return ok(result)


@router.put("/objects/{object_id}")
async def update_object(dataset_id: str, object_id: str, body: ObjectInstanceUpdate, _: dict = Depends(get_current_user)):
    result = await instance_store.update_object(dataset_id, object_id, body.properties or {})
    if not result:
        return error(404, "对象不存在")
    return ok(result)


@router.delete("/objects/{object_id}")
async def delete_object(dataset_id: str, object_id: str, _: dict = Depends(get_current_user)):
    deleted = await instance_store.delete_object(dataset_id, object_id)
    if not deleted:
        return error(404, "对象不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Link Instances
# ═══════════════════════════════════════════════════════════

@router.get("/links")
async def list_links(dataset_id: str, page: int = 1, page_size: int = 20,
                     link_type: str | None = None, source_id: str | None = None,
                     target_id: str | None = None, _: dict = Depends(get_current_user)):
    items, total = await instance_store.list_links(dataset_id, page, page_size, link_type, source_id, target_id)
    return paged(items, total, page, page_size)


@router.post("/links")
async def create_link(dataset_id: str, body: LinkInstanceCreate, _: dict = Depends(get_current_user)):
    result = await instance_store.create_link(dataset_id, body.model_dump())
    return ok(result)


@router.post("/links/batch")
async def batch_create_links(dataset_id: str, body: BatchLinksRequest, _: dict = Depends(get_current_user)):
    results = await instance_store.batch_create_links(dataset_id, [it.model_dump() for it in body.items])
    return ok(results)


@router.get("/links/{link_id}")
async def get_link(dataset_id: str, link_id: str, _: dict = Depends(get_current_user)):
    result = await instance_store.get_link(dataset_id, link_id)
    if not result:
        return error(404, "链接不存在")
    return ok(result)


@router.put("/links/{link_id}")
async def update_link(dataset_id: str, link_id: str, body: LinkInstanceUpdate, _: dict = Depends(get_current_user)):
    result = await instance_store.update_link(dataset_id, link_id, body.properties or {})
    if not result:
        return error(404, "链接不存在")
    return ok(result)


@router.delete("/links/{link_id}")
async def delete_link(dataset_id: str, link_id: str, _: dict = Depends(get_current_user)):
    deleted = await instance_store.delete_link(dataset_id, link_id)
    if not deleted:
        return error(404, "链接不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Graph Operations
# ═══════════════════════════════════════════════════════════

@router.get("/graph/stats")
async def graph_stats(dataset_id: str, _: dict = Depends(get_current_user)):
    stats = await instance_store.get_graph_stats(dataset_id)
    return ok(stats)


@router.get("/graph/neighbors/{object_type}/{object_id}")
async def neighbors(dataset_id: str, object_type: str, object_id: str,
                    depth: int = 1, _: dict = Depends(get_current_user)):
    result = await instance_store.get_neighbors(dataset_id, object_type, object_id, depth)
    return ok(result)


@router.post("/graph/path")
async def find_path(dataset_id: str, body: PathRequest, _: dict = Depends(get_current_user)):
    result = await instance_store.find_path(dataset_id, body.source_id, body.target_id, body.max_depth)
    return ok(result)


@router.post("/graph/traverse")
async def traverse(dataset_id: str, body: TraverseRequest, _: dict = Depends(get_current_user)):
    result = await instance_store.traverse(
        dataset_id, body.start_node, body.direction, body.max_depth,
        body.edge_types, body.node_types,
    )
    return ok(result)
