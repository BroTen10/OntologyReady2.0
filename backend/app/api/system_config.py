from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..core.response import error, ok
from ..models import store
from .deps import get_current_admin

router = APIRouter(prefix="/api/admin")


class SystemConfigPayload(BaseModel):
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    document_engine_type: str | None = None
    storage_type: str | None = None
    storage_endpoint: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_bucket: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    default_page_size: int | None = None
    session_timeout_minutes: int | None = None
    access_token_expire_minutes: int | None = None
    refresh_token_expire_days: int | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


class SystemConfigItemPayload(BaseModel):
    value: Any


@router.get("/system-config")
async def get_all_config(_admin: dict = Depends(get_current_admin)):
    data = await store.get_all_system_config()
    return ok(data)


@router.post("/system-config")
async def set_config(payload: SystemConfigPayload, _admin: dict = Depends(get_current_admin)):
    items = {k: v for k, v in payload.model_dump().items() if v is not None}
    data = await store.set_system_config_items(items)
    return ok(data)


@router.get("/system-config/{key}")
async def get_config_item(key: str, _admin: dict = Depends(get_current_admin)):
    item = await store.get_system_config_item(key)
    if item is None:
        return error(404, f"配置项 '{key}' 不存在")
    return ok(item)


@router.put("/system-config/{key}")
async def update_config_item(key: str, payload: SystemConfigItemPayload, _admin: dict = Depends(get_current_admin)):
    item = await store.update_system_config_item(key, payload.value)
    if item is None:
        return error(404, f"配置项 '{key}' 不存在")
    return ok(item)


@router.delete("/system-config/{key}")
async def delete_config_item(key: str, _admin: dict = Depends(get_current_admin)):
    deleted = await store.delete_system_config_item(key)
    if not deleted:
        return error(404, f"配置项 '{key}' 不存在")
    return ok(None, "已删除")
