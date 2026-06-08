from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..core.response import error, ok, paged
from ..models import skill_store
from ..models.skill import (
    PresetImportRequest,
    SkillCreate,
    SkillGenerateRequest,
    SkillUpdate,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/skills", tags=["skills"])


# ═══════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════

@router.get("")
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    category: str | None = None,
    search: str | None = None,
    tags: str | None = Query(None, alias="tag"),
    enabled_only: bool = Query(False, alias="enabled"),
    _: dict = Depends(get_current_user),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    items, total = await skill_store.list_skills(
        page=page, page_size=page_size,
        category=category, search=search,
        tags=tag_list, enabled_only=enabled_only,
    )
    return paged(items, total, page, page_size)


@router.post("")
async def create_skill(body: SkillCreate, _: dict = Depends(get_current_user)):
    existing = await skill_store.get_skill_by_name(body.name)
    if existing:
        return error(409, "技能名称已存在")
    result = await skill_store.create_skill(body.model_dump(by_alias=True))
    return ok(result)


@router.get("/{skill_id}")
async def get_skill(skill_id: str, _: dict = Depends(get_current_user)):
    result = await skill_store.get_skill(skill_id)
    if not result:
        return error(404, "技能不存在")
    return ok(result)


@router.put("/{skill_id}")
async def update_skill(skill_id: str, body: SkillUpdate, _: dict = Depends(get_current_user)):
    result = await skill_store.update_skill(skill_id, body.model_dump(by_alias=True, exclude_none=True))
    if not result:
        return error(404, "技能不存在")
    return ok(result)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, _: dict = Depends(get_current_user)):
    deleted = await skill_store.delete_skill(skill_id)
    if not deleted:
        return error(404, "技能不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Actions
# ═══════════════════════════════════════════════════════════

@router.post("/{skill_id}/enable")
async def enable_skill(skill_id: str, _: dict = Depends(get_current_user)):
    result = await skill_store.set_enabled(skill_id, True)
    if not result:
        return error(404, "技能不存在")
    return ok(result, "已启用")


@router.post("/{skill_id}/disable")
async def disable_skill(skill_id: str, _: dict = Depends(get_current_user)):
    result = await skill_store.set_enabled(skill_id, False)
    if not result:
        return error(404, "技能不存在")
    return ok(result, "已禁用")


@router.post("/{skill_id}/clone")
async def clone_skill(
    skill_id: str,
    new_name: str = Query(..., description="New skill name"),
    _: dict = Depends(get_current_user),
):
    existing = await skill_store.get_skill_by_name(new_name)
    if existing:
        return error(409, "目标技能名称已存在")
    result = await skill_store.clone_skill(skill_id, new_name)
    if not result:
        return error(404, "源技能不存在")
    return ok(result, "已克隆")


# ═══════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════

@router.get("/presets/index")
async def list_presets(_: dict = Depends(get_current_user)):
    presets = await skill_store.list_presets()
    return ok(presets)


@router.get("/presets/{name}")
async def get_preset(name: str, _: dict = Depends(get_current_user)):
    preset = await skill_store.get_preset(name)
    if not preset:
        return error(404, "预设技能不存在")
    return ok(preset)


@router.post("/presets/import")
async def import_presets(body: PresetImportRequest, _: dict = Depends(get_current_user)):
    results = await skill_store.import_presets(body.presets)
    return ok(results, f"导入完成: {len([r for r in results if r['status'] == 'created'])} 新建, "
                         f"{len([r for r in results if r['status'] == 'skipped'])} 跳过, "
                         f"{len([r for r in results if r['status'] == 'error'])} 错误")


# ═══════════════════════════════════════════════════════════
# Skill Pack: Upload / Download
# ═══════════════════════════════════════════════════════════

@router.get("/{skill_id}/download")
async def download_skill(skill_id: str, _: dict = Depends(get_current_user)):
    skill = await skill_store.get_skill(skill_id)
    if not skill:
        return error(404, "技能不存在")

    pack = {
        "name": skill["name"],
        "display_name": skill["display_name"],
        "category": skill["category"],
        "description": skill.get("description"),
        "tags": skill.get("tags", []),
        "author": skill.get("author"),
        "version": skill.get("version", "1.0.0"),
        "icon": skill.get("icon"),
        "files": {},
    }
    if skill.get("skill_md"):
        pack["files"]["SKILL.md"] = skill["skill_md"]
    if skill.get("prompt_md"):
        pack["files"]["prompt.md"] = skill["prompt_md"]
    if skill.get("schema"):
        pack["files"]["schema.json"] = skill["schema"]
    for fn, content in (skill.get("scripts") or {}).items():
        pack["files"][f"scripts/{fn}"] = content

    return ok(pack)


@router.post("/upload")
async def upload_skill_pack(
    body: dict,
    _: dict = Depends(get_current_user),
):
    name = body.get("name")
    if not name:
        return error(400, "name is required")

    files = body.get("files", {})
    skill_data = {
        "name": name,
        "display_name": body.get("display_name", name),
        "category": body.get("category", "imported"),
        "description": body.get("description"),
        "tags": body.get("tags", []),
        "author": body.get("author"),
        "version": body.get("version", "1.0.0"),
        "icon": body.get("icon"),
        "skill_md": files.pop("SKILL.md", None),
        "prompt_md": files.pop("prompt.md", None),
        "schema": files.pop("schema.json", None),
    }

    scripts = {}
    for k, v in files.items():
        if k.startswith("scripts/"):
            scripts[k.replace("scripts/", "", 1)] = v
        else:
            scripts[k] = v
    skill_data["scripts"] = scripts

    existing = await skill_store.get_skill_by_name(name)
    if existing:
        result = await skill_store.update_skill(existing["id"], skill_data)
        return ok(result, "已更新")
    result = await skill_store.create_skill(skill_data)
    return ok(result, "已创建")


# ═══════════════════════════════════════════════════════════
# Generate from Action Type
# ═══════════════════════════════════════════════════════════

@router.post("/generate-from-action")
async def generate_from_action(
    dataset_id: str = Query(...),
    body: SkillGenerateRequest = None,
    _: dict = Depends(get_current_user),
):
    if body is None:
        body = SkillGenerateRequest(action_name="")
    result = await skill_store.generate_from_action_type(
        dataset_id=dataset_id,
        action_name=body.action_name,
        category=body.category,
        display_name=body.display_name,
        description=body.description,
    )
    if not result:
        return error(404, f"Action type '{body.action_name}' not found in dataset '{dataset_id}'")
    return ok(result, "技能已生成")


# ═══════════════════════════════════════════════════════════
# Categories
# ═══════════════════════════════════════════════════════════

@router.get("/categories/list")
async def list_categories(_: dict = Depends(get_current_user)):
    cats = await skill_store.list_categories()
    return ok(cats)
