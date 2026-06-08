from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.response import error, ok, paged
from ..models import acr_store
from ..models.acr import (
    AccessRuleCreate,
    AccessRuleUpdate,
    ACRConfigUpdate,
    RuleGroupBindingCreate,
    RuleGroupCreate,
    RuleGroupUpdate,
)
from .deps import get_current_admin, get_current_user

router = APIRouter(prefix="/api/acr", tags=["acr"])


# ── ACR Config ───────────────────────────────────────────

@router.get("/config")
async def get_config(_: dict = Depends(get_current_admin)):
    cfg = await acr_store.get_acr_config()
    return ok(cfg)


@router.put("/config")
async def update_config(body: ACRConfigUpdate, _: dict = Depends(get_current_admin)):
    cfg = await acr_store.update_acr_config(body.model_dump(exclude_none=True))
    return ok(cfg)


# ── Access Rules ─────────────────────────────────────────

@router.get("/rules")
async def list_rules(resource_type: str | None = None, _: dict = Depends(get_current_admin)):
    rules = await acr_store.list_rules(resource_type)
    return ok(rules)


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: int, _: dict = Depends(get_current_admin)):
    rule = await acr_store.get_rule(rule_id)
    if not rule:
        return error(404, "规则不存在")
    return ok(rule)


@router.post("/rules")
async def create_rule(body: AccessRuleCreate, _: dict = Depends(get_current_admin)):
    rule = await acr_store.create_rule(body.model_dump())
    return ok(rule)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, body: AccessRuleUpdate, _: dict = Depends(get_current_admin)):
    rule = await acr_store.update_rule(rule_id, body.model_dump(exclude_none=True))
    if not rule:
        return error(404, "规则不存在")
    return ok(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, _: dict = Depends(get_current_admin)):
    deleted = await acr_store.delete_rule(rule_id)
    if not deleted:
        return error(404, "规则不存在")
    return ok(None, "已删除")


# ── Rule Groups ──────────────────────────────────────────

@router.get("/rule-groups")
async def list_rule_groups(_: dict = Depends(get_current_admin)):
    groups = await acr_store.list_rule_groups()
    return ok(groups)


@router.get("/rule-groups/{group_id}")
async def get_rule_group(group_id: int, _: dict = Depends(get_current_admin)):
    group = await acr_store.get_rule_group(group_id)
    if not group:
        return error(404, "规则组不存在")
    return ok(group)


@router.post("/rule-groups")
async def create_rule_group(body: RuleGroupCreate, _: dict = Depends(get_current_admin)):
    group = await acr_store.create_rule_group(body.model_dump())
    return ok(group)


@router.put("/rule-groups/{group_id}")
async def update_rule_group(group_id: int, body: RuleGroupUpdate, _: dict = Depends(get_current_admin)):
    group = await acr_store.update_rule_group(group_id, body.model_dump(exclude_none=True))
    if not group:
        return error(404, "规则组不存在")
    return ok(group)


@router.delete("/rule-groups/{group_id}")
async def delete_rule_group(group_id: int, _: dict = Depends(get_current_admin)):
    deleted = await acr_store.delete_rule_group(group_id)
    if not deleted:
        return error(404, "规则组不存在")
    return ok(None, "已删除")


# ── Bindings ─────────────────────────────────────────────

@router.get("/bindings")
async def list_bindings(_: dict = Depends(get_current_admin)):
    bindings = await acr_store.list_bindings()
    return ok(bindings)


@router.post("/bindings")
async def create_binding(body: RuleGroupBindingCreate, _: dict = Depends(get_current_admin)):
    binding = await acr_store.create_binding(body.model_dump())
    return ok(binding)


@router.delete("/bindings/{binding_id}")
async def delete_binding(binding_id: int, _: dict = Depends(get_current_admin)):
    deleted = await acr_store.delete_binding(binding_id)
    if not deleted:
        return error(404, "绑定不存在")
    return ok(None, "已删除")
