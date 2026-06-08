from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.response import error, ok, paged
from ..models import ontology_store, versioning_store
from ..models.versioning import (
    CommitStagingRequest,
    DiffEntry,
    DiffResponse,
    StagedChangeCreate,
    StagedChangeRef,
    StagedChangeResponse,
    UndoStagedChangesRequest,
    UpdateVersionNotesRequest,
    VersionSnapshotResponse,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/datasets/{dataset_id}", tags=["versioning"])


# ═══════════════════════════════════════════════════════════
# Staging
# ═══════════════════════════════════════════════════════════

@router.get("/staging")
async def list_staged_changes(dataset_id: str, _: dict = Depends(get_current_user)):
    items = await versioning_store.list_staged_changes(dataset_id)
    return ok(items)


@router.post("/staging")
async def stage_change(dataset_id: str, body: StagedChangeCreate, _: dict = Depends(get_current_user)):
    result = await versioning_store.stage_change(dataset_id, body.model_dump())
    return ok(result)


@router.get("/staging/{change_id}")
async def get_staged_change(dataset_id: str, change_id: str, _: dict = Depends(get_current_user)):
    result = await versioning_store.get_staged_change(dataset_id, change_id)
    if not result:
        return error(404, "暂存变更不存在")
    return ok(result)


@router.delete("/staging/{change_id}")
async def discard_staged_change(dataset_id: str, change_id: str, _: dict = Depends(get_current_user)):
    deleted = await versioning_store.delete_staged_change(dataset_id, change_id)
    if not deleted:
        return error(404, "暂存变更不存在")
    return ok(None, "已撤销暂存变更")


@router.post("/staging/undo")
async def undo_staged_changes(dataset_id: str, body: UndoStagedChangesRequest, _: dict = Depends(get_current_user)):
    count = await versioning_store.clear_staging(dataset_id, body.change_ids)
    return ok({"cleared": count}, f"已清除 {count} 条暂存变更")


async def _snapshot_current_ontology(dataset_id: str) -> dict:
    """Collect current ontology state for versioning."""
    obj_types, _ = await ontology_store.list_object_types(dataset_id, page=1, page_size=10000)
    link_types, _ = await ontology_store.list_link_types(dataset_id, page=1, page_size=10000)
    action_types, _ = await ontology_store.list_action_types(dataset_id, page=1, page_size=10000)
    return {
        "object_types": obj_types,
        "link_types": link_types,
        "action_types": action_types,
    }


@router.post("/staging/commit")
async def commit_staging(dataset_id: str, body: CommitStagingRequest, user: dict = Depends(get_current_user)):
    staged = await versioning_store.list_staged_changes(dataset_id)
    if not staged:
        return error(400, "没有待提交的暂存变更")

    if body.commit_changes:
        staged = [s for s in staged if s["change_id"] in body.commit_changes]
        if not staged:
            return error(400, "指定的暂存变更不存在")

    # Apply staged changes to ontology
    for change in staged:
        entity_type = change["entity_type"]
        change_type = change["change_type"]
        entity_name = change["entity_name"]
        data = change["data"]

        if entity_type == "object_type":
            if change_type == "create":
                await ontology_store.create_object_type(dataset_id, data)
            elif change_type == "update":
                await ontology_store.update_object_type(dataset_id, entity_name, data)
            elif change_type == "delete":
                await ontology_store.delete_object_type(dataset_id, entity_name)

        elif entity_type == "link_type":
            if change_type == "create":
                await ontology_store.create_link_type(dataset_id, data)
            elif change_type == "update":
                await ontology_store.update_link_type(dataset_id, entity_name, data)
            elif change_type == "delete":
                await ontology_store.delete_link_type(dataset_id, entity_name)

        elif entity_type == "action_type":
            if change_type == "create":
                await ontology_store.create_action_type(dataset_id, data)
            elif change_type == "update":
                await ontology_store.update_action_type(dataset_id, entity_name, data)
            elif change_type == "delete":
                await ontology_store.delete_action_type(dataset_id, entity_name)

    # Take snapshot
    snapshot = await _snapshot_current_ontology(dataset_id)
    version = await versioning_store.create_version_snapshot(dataset_id, {
        "commit_message": body.message,
        "ontology_snapshot": snapshot,
        "changes_summary": [
            {
                "change_id": s["change_id"],
                "entity_type": s["entity_type"],
                "change_type": s["change_type"],
                "entity_name": s["entity_name"],
                "description": s.get("description"),
            }
            for s in staged
        ],
        "created_by": user.get("username") if user else None,
    })

    # Clear committed changes
    await versioning_store.clear_staging(dataset_id, [s["change_id"] for s in staged])

    return ok(version, f"已提交 {len(staged)} 条变更")


# ═══════════════════════════════════════════════════════════
# Versions
# ═══════════════════════════════════════════════════════════

@router.get("/versions")
async def list_versions(dataset_id: str, page: int = 1, page_size: int = 20, _: dict = Depends(get_current_user)):
    items, total = await versioning_store.list_versions(dataset_id, page, page_size)
    return paged(items, total, page, page_size)


@router.get("/versions/diff")
async def diff_versions(dataset_id: str, a: str, b: str, _: dict = Depends(get_current_user)):
    version_a = await versioning_store.get_version(dataset_id, a)
    version_b = await versioning_store.get_version(dataset_id, b)
    if not version_a or not version_b:
        return error(404, "版本不存在")

    diffs: list[dict] = []
    for category in ["object_types", "link_types", "action_types"]:
        items_a = version_a.get("ontology_snapshot", {}).get(category, [])
        items_b = version_b.get("ontology_snapshot", {}).get(category, [])

        key_field = {
            "object_types": "type_name",
            "link_types": "link_name",
            "action_types": "action_name",
        }[category]

        names_a = {it.get(key_field) for it in items_a}
        names_b = {it.get(key_field) for it in items_b}
        entity_type = category.rstrip("s")

        for name in names_b - names_a:
            item = next(it for it in items_b if it.get(key_field) == name)
            diffs.append({
                "entity_type": entity_type,
                "entity_name": name,
                "field": "__all__",
                "old_value": None,
                "new_value": item,
            })

        for name in names_a - names_b:
            item = next(it for it in items_a if it.get(key_field) == name)
            diffs.append({
                "entity_type": entity_type,
                "entity_name": name,
                "field": "__all__",
                "old_value": item,
                "new_value": None,
            })

        for name in names_a & names_b:
            item_a = next(it for it in items_a if it.get(key_field) == name)
            item_b = next(it for it in items_b if it.get(key_field) == name)
            all_keys = set(item_a.keys()) | set(item_b.keys())
            for k in all_keys:
                if item_a.get(k) != item_b.get(k):
                    diffs.append({
                        "entity_type": entity_type,
                        "entity_name": name,
                        "field": k,
                        "old_value": item_a.get(k),
                        "new_value": item_b.get(k),
                    })

    return ok({"version_a": a, "version_b": b, "diffs": diffs})


@router.get("/versions/{version_id}")
async def get_version(dataset_id: str, version_id: str, _: dict = Depends(get_current_user)):
    result = await versioning_store.get_version(dataset_id, version_id)
    if not result:
        return error(404, "版本不存在")
    return ok(result)


@router.put("/versions/{version_id}/notes")
async def update_version_notes(dataset_id: str, version_id: str, body: UpdateVersionNotesRequest, _: dict = Depends(get_current_user)):
    result = await versioning_store.update_version_notes(dataset_id, version_id, body.notes)
    if not result:
        return error(404, "版本不存在")
    return ok(result)


@router.post("/versions/{version_id}/rollback")
async def rollback_version(dataset_id: str, version_id: str, _: dict = Depends(get_current_user)):
    version = await versioning_store.get_version(dataset_id, version_id)
    if not version:
        return error(404, "版本不存在")

    snapshot = version.get("ontology_snapshot", {})

    # Delete current ontology
    obj_types, _ = await ontology_store.list_object_types(dataset_id, page=1, page_size=10000)
    link_types, _ = await ontology_store.list_link_types(dataset_id, page=1, page_size=10000)
    action_types, _ = await ontology_store.list_action_types(dataset_id, page=1, page_size=10000)

    for item in action_types:
        await ontology_store.delete_action_type(dataset_id, item["action_name"])
    for item in link_types:
        await ontology_store.delete_link_type(dataset_id, item["link_name"])
    for item in obj_types:
        await ontology_store.delete_object_type(dataset_id, item["type_name"])

    # Restore from snapshot
    for item in snapshot.get("object_types", []):
        await ontology_store.create_object_type(dataset_id, item)
    for item in snapshot.get("link_types", []):
        await ontology_store.create_link_type(dataset_id, item)
    for item in snapshot.get("action_types", []):
        await ontology_store.create_action_type(dataset_id, item)

    return ok(None, f"已回滚到版本 {version['version_number']}")
