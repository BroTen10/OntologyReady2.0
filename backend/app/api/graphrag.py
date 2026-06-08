"""GraphRAG API endpoints — workspace, documents, graph, QA, model configs."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..core.response import error, ok, paged
from ..graphrag.provider import get_graphrag
from ..graphrag import store as graphrag_store
from .deps import get_current_user

router = APIRouter(prefix="/api/graphrag", tags=["graphrag"])

graphrag = get_graphrag()


# ── Request/Response Models ──────────────────────────────

class WorkspaceCreateReq(BaseModel):
    name: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class SearchReq(BaseModel):
    workspace_id: str
    query: str
    top_k: int = 10


class ChatReq(BaseModel):
    workspace_id: str
    question: str
    history: list[dict] = Field(default_factory=list)
    mode: str = "hybrid"


class ModelConfigReq(BaseModel):
    workspace_id: str = ""
    model_type: str
    provider_name: str
    model_name: str
    config: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class ModelConfigUpdateReq(BaseModel):
    provider_name: str | None = None
    model_name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool | None = None


# ═══════════════════════════════════════════════════════════
# Workspaces
# ═══════════════════════════════════════════════════════════

@router.get("/workspaces")
async def list_workspaces(_: dict = Depends(get_current_user)):
    ws_list = await graphrag.list_workspaces()
    return ok(ws_list)


@router.post("/workspaces")
async def create_workspace(body: WorkspaceCreateReq, _: dict = Depends(get_current_user)):
    ws = await graphrag.create_workspace(body.name, body.description, body.config)
    return ok(ws)


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str, _: dict = Depends(get_current_user)):
    ws = await graphrag.get_workspace(workspace_id)
    if not ws:
        return error(404, "工作空间不存在")
    return ok(ws)


@router.put("/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, body: WorkspaceCreateReq, _: dict = Depends(get_current_user)):
    ws = await graphrag.update_workspace(
        workspace_id, name=body.name, description=body.description, config=body.config,
    )
    if not ws:
        return error(404, "工作空间不存在")
    return ok(ws)


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, _: dict = Depends(get_current_user)):
    deleted = await graphrag.delete_workspace(workspace_id)
    if not deleted:
        return error(404, "工作空间不存在")
    return ok(None, "已删除")


@router.post("/workspaces/{workspace_id}/default")
async def set_default_workspace(workspace_id: str, _: dict = Depends(get_current_user)):
    await graphrag.set_default_workspace(workspace_id)
    return ok(None, "已设为默认")


@router.get("/workspaces/default")
async def get_default_workspace(_: dict = Depends(get_current_user)):
    ws = await graphrag.get_default_workspace()
    if not ws:
        return error(404, "未找到默认工作空间")
    return ok(ws)


# ═══════════════════════════════════════════════════════════
# Documents
# ═══════════════════════════════════════════════════════════

@router.get("/workspaces/{workspace_id}/documents")
async def list_documents(workspace_id: str, _: dict = Depends(get_current_user)):
    docs = await graphrag.list_documents(workspace_id)
    return ok(docs)


@router.post("/workspaces/{workspace_id}/documents")
async def upload_document(workspace_id: str, file: UploadFile = File(...), _: dict = Depends(get_current_user)):
    content = await file.read()
    doc = await graphrag.upload_document(workspace_id, content, file.filename or "unnamed")
    return ok(doc)


@router.post("/workspaces/{workspace_id}/documents/{doc_id}/process")
async def process_document(workspace_id: str, doc_id: str, _: dict = Depends(get_current_user)):
    doc = await graphrag.get_document(doc_id)
    if not doc:
        return error(404, "文档不存在")

    from ..providers.factory import get_file_storage
    file_storage = get_file_storage()
    file_key = f"graphrag/{workspace_id}/{doc_id}/{doc['filename']}"
    content_bytes = await file_storage.download(file_key)

    result = await graphrag.process_document(workspace_id, doc_id, content_bytes, doc["filename"])
    return ok(result)


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, _: dict = Depends(get_current_user)):
    deleted = await graphrag.delete_document(doc_id)
    if not deleted:
        return error(404, "文档不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Graph
# ═══════════════════════════════════════════════════════════

@router.get("/workspaces/{workspace_id}/graph")
async def get_graph(workspace_id: str, _: dict = Depends(get_current_user)):
    data = await graphrag.get_graph_data(workspace_id)
    return ok(data)


@router.get("/workspaces/{workspace_id}/graph/stats")
async def get_graph_stats(workspace_id: str, _: dict = Depends(get_current_user)):
    stats = await graphrag.get_graph_stats(workspace_id)
    return ok(stats)


@router.get("/workspaces/{workspace_id}/graph/neighbors/{entity_id}")
async def get_neighbors(workspace_id: str, entity_id: str, depth: int = 1, _: dict = Depends(get_current_user)):
    data = await graphrag.get_neighbors(workspace_id, entity_id, depth)
    return ok(data)


@router.get("/workspaces/{workspace_id}/entities")
async def search_entities(workspace_id: str, query: str = "", entity_type: str | None = None,
                          _: dict = Depends(get_current_user)):
    entities = await graphrag.search_entities(workspace_id, query, entity_type)
    return ok(entities)


# ═══════════════════════════════════════════════════════════
# Communities
# ═══════════════════════════════════════════════════════════

@router.get("/workspaces/{workspace_id}/communities")
async def get_communities(workspace_id: str, _: dict = Depends(get_current_user)):
    communities = await graphrag.get_communities(workspace_id)
    return ok(communities)


# ═══════════════════════════════════════════════════════════
# Chat / QA
# ═══════════════════════════════════════════════════════════

@router.post("/chat")
async def chat(body: ChatReq, _: dict = Depends(get_current_user)):
    resp = await graphrag.chat(body.workspace_id, body.question, body.history, body.mode)
    return ok({"content": resp.content, "model": resp.model, "usage": resp.usage})


@router.post("/chat/stream")
async def chat_stream(body: ChatReq, _: dict = Depends(get_current_user)):
    async def event_stream():
        async for token in graphrag.chat_stream(body.workspace_id, body.question, body.history, body.mode):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ═══════════════════════════════════════════════════════════
# Model Configs
# ═══════════════════════════════════════════════════════════

@router.get("/model-configs")
async def list_model_configs(workspace_id: str = "", model_type: str | None = None,
                             _: dict = Depends(get_current_user)):
    configs = await graphrag.list_model_configs(workspace_id, model_type)
    return ok(configs)


@router.post("/model-configs")
async def create_model_config(body: ModelConfigReq, _: dict = Depends(get_current_user)):
    config = await graphrag.create_model_config(
        body.workspace_id, body.model_type, body.provider_name,
        body.model_name, body.config, body.is_default,
    )
    return ok(config)


@router.get("/model-configs/{config_id}")
async def get_model_config(config_id: str, _: dict = Depends(get_current_user)):
    config = await graphrag.get_model_config(config_id)
    if not config:
        return error(404, "模型配置不存在")
    return ok(config)


@router.put("/model-configs/{config_id}")
async def update_model_config(config_id: str, body: ModelConfigUpdateReq, _: dict = Depends(get_current_user)):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    config = await graphrag.update_model_config(config_id, **kwargs)
    if not config:
        return error(404, "模型配置不存在")
    return ok(config)


@router.delete("/model-configs/{config_id}")
async def delete_model_config(config_id: str, _: dict = Depends(get_current_user)):
    deleted = await graphrag.delete_model_config(config_id)
    if not deleted:
        return error(404, "模型配置不存在")
    return ok(None, "已删除")


# ═══════════════════════════════════════════════════════════
# Upload + Process combined (one-step)
# ═══════════════════════════════════════════════════════════

@router.post("/workspaces/{workspace_id}/upload-and-process")
async def upload_and_process(workspace_id: str, file: UploadFile = File(...), _: dict = Depends(get_current_user)):
    content = await file.read()
    doc = await graphrag.upload_document(workspace_id, content, file.filename or "unnamed")

    from ..providers.factory import get_file_storage
    file_storage = get_file_storage()
    file_key = f"graphrag/{workspace_id}/{doc['doc_id']}/{doc['filename']}"
    await file_storage.upload(file_key, content)

    result = await graphrag.process_document(workspace_id, doc["doc_id"], content, file.filename or "unnamed")
    return ok(result)
