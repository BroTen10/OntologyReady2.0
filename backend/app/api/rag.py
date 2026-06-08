"""RAG API endpoints — knowledge base, documents, search, chat, conversations."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

from ..core.response import error, ok, paged
from ..providers.factory import get_rag
from ..rag import store as rag_store
from .deps import get_current_user

router = APIRouter(prefix="/api/rag", tags=["rag"])

rag = get_rag()


# ── Request/Response Models ──────────────────────────────

class KBCreateReq(BaseModel):
    name: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class KBResponse(BaseModel):
    kb_id: str
    name: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class SearchReq(BaseModel):
    kb_id: str
    query: str
    top_k: int = 10


class ChatReq(BaseModel):
    kb_id: str
    question: str
    history: list[dict] = Field(default_factory=list)


class ChatStreamReq(BaseModel):
    kb_id: str
    question: str
    history: list[dict] = Field(default_factory=list)


class ConvCreateReq(BaseModel):
    kb_id: str
    title: str = ""
    model_params: dict[str, Any] = Field(default_factory=dict)
    system_prompt: str = ""


class ConvChatReq(BaseModel):
    question: str


# ═══════════════════════════════════════════════════════════
# Knowledge Bases
# ═══════════════════════════════════════════════════════════

@router.get("/knowledge-bases")
async def list_kbs(_: dict = Depends(get_current_user)):
    kbs = await rag.list_knowledge_bases()
    return ok([{"kb_id": k.kb_id, "name": k.name, "config": k.config} for k in kbs])


@router.post("/knowledge-bases")
async def create_kb(body: KBCreateReq, _: dict = Depends(get_current_user)):
    kb = await rag.create_knowledge_base(body.name, {"description": body.description, **body.config})
    return ok({"kb_id": kb.kb_id, "name": kb.name})


@router.get("/knowledge-bases/{kb_id}")
async def get_kb(kb_id: str, _: dict = Depends(get_current_user)):
    kb = await rag_store.get_kb(kb_id)
    if not kb:
        return error(404, "知识库不存在")
    return ok(kb)


@router.delete("/knowledge-bases/{kb_id}")
async def delete_kb(kb_id: str, _: dict = Depends(get_current_user)):
    deleted = await rag.delete_knowledge_base(kb_id)
    if not deleted:
        return error(404, "知识库不存在")
    return ok(None, "已删除")


@router.get("/knowledge-bases/{kb_id}/stats")
async def kb_stats(kb_id: str, _: dict = Depends(get_current_user)):
    docs = await rag.list_documents(kb_id)
    chunk_count = await rag_store.count_chunks(kb_id)
    return ok({
        "document_count": len(docs),
        "chunk_count": chunk_count,
        "documents": [{"doc_id": d.doc_id, "filename": d.filename, "status": d.status} for d in docs],
    })


# ═══════════════════════════════════════════════════════════
# Documents
# ═══════════════════════════════════════════════════════════

@router.get("/knowledge-bases/{kb_id}/documents")
async def list_docs(kb_id: str, _: dict = Depends(get_current_user)):
    docs = await rag.list_documents(kb_id)
    return ok([{"doc_id": d.doc_id, "filename": d.filename, "status": d.status,
                 "file_type": d.file_type} for d in docs])


@router.post("/knowledge-bases/{kb_id}/documents")
async def upload_doc(kb_id: str, file: UploadFile = File(...), _: dict = Depends(get_current_user)):
    content = await file.read()
    doc = await rag.upload_document(kb_id, content, file.filename or "unnamed")

    # Process immediately — parse, chunk, embed
    task = await rag.process_document(kb_id, doc.doc_id, content, file.filename or "unnamed")
    return ok({"doc_id": doc.doc_id, "filename": doc.filename, "status": task.status})


@router.delete("/documents/{doc_id}")
async def delete_doc(doc_id: str, _: dict = Depends(get_current_user)):
    deleted = await rag.delete_document(doc_id)
    if not deleted:
        return error(404, "文档不存在")
    return ok(None, "已删除")


@router.get("/documents/{doc_id}/chunks")
async def list_chunks(doc_id: str, kb_id: str, _: dict = Depends(get_current_user)):
    chunks = await rag.list_chunks(kb_id, doc_id)
    return ok([{"chunk_id": c.chunk_id, "content": c.content, "metadata": c.metadata} for c in chunks])


# ═══════════════════════════════════════════════════════════
# Search
# ═══════════════════════════════════════════════════════════

@router.post("/search")
async def search(body: SearchReq, _: dict = Depends(get_current_user)):
    results = await rag.search(body.kb_id, body.query, body.top_k)
    return ok([{"doc_id": r.doc_id, "chunk_id": r.chunk_id, "content": r.content, "score": r.score, "metadata": r.metadata} for r in results])


# ═══════════════════════════════════════════════════════════
# Chat / QA
# ═══════════════════════════════════════════════════════════

@router.post("/chat")
async def chat(body: ChatReq, _: dict = Depends(get_current_user)):
    resp = await rag.chat(body.kb_id, body.question, body.history)
    return ok({"content": resp.content, "model": resp.model, "usage": resp.usage})


@router.post("/chat/stream")
async def chat_sse(body: ChatStreamReq, _: dict = Depends(get_current_user)):
    async def event_stream():
        async for token in rag.chat_stream(body.kb_id, body.question, body.history):
            if isinstance(token, str):
                yield f"data: {token}\n\n"
            elif isinstance(token, list):
                yield f"data: {json.dumps({'sources': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ═══════════════════════════════════════════════════════════
# Conversations
# ═══════════════════════════════════════════════════════════

@router.get("/conversations")
async def list_convs(_: dict = Depends(get_current_user)):
    user_id = _.get("user_id", "")
    convs = await rag_store.list_conversations(user_id)
    return ok(convs)


@router.post("/conversations")
async def create_conv(body: ConvCreateReq, _: dict = Depends(get_current_user)):
    user_id = _.get("user_id", "")
    conv = await rag_store.create_conversation(
        kb_id=body.kb_id, title=body.title or "新对话", user_id=user_id,
        model_params=body.model_params, system_prompt=body.system_prompt,
    )
    return ok(conv)


@router.get("/conversations/{conv_id}")
async def get_conv(conv_id: str, _: dict = Depends(get_current_user)):
    conv = await rag_store.get_conversation(conv_id)
    if not conv:
        return error(404, "对话不存在")
    messages = await rag_store.get_messages_by_conversation(conv_id)
    return ok({"conversation": conv, "messages": messages})


@router.delete("/conversations/{conv_id}")
async def delete_conv(conv_id: str, _: dict = Depends(get_current_user)):
    deleted = await rag_store.delete_conversation(conv_id)
    if not deleted:
        return error(404, "对话不存在")
    return ok(None, "已删除")


@router.post("/conversations/{conv_id}/chat/stream")
async def conv_chat_sse(conv_id: str, body: ConvChatReq, _: dict = Depends(get_current_user)):
    conv = await rag_store.get_conversation(conv_id)
    if not conv:
        return error(404, "对话不存在")

    # Build history from previous messages
    prev = await rag_store.get_messages_by_conversation(conv_id)
    history = [{"role": m["role"], "content": m["content"]} for m in prev]

    # Save user message
    await rag_store.save_message(conv_id, "user", body.question)

    kb_id = conv["kb_id"]
    mp = conv.get("model_params", {})
    top_k = mp.get("top_n", 6)

    async def event_stream():
        full_answer = ""
        sources = []

        async for token in rag.chat_stream(kb_id, body.question, history, top_k=top_k):
            if isinstance(token, str):
                full_answer += token
                yield f"data: {token}\n\n"
            elif isinstance(token, list):
                sources = token
                yield f"data: {json.dumps({'sources': sources})}\n\n"

        # Save assistant message
        await rag_store.save_message(conv_id, "assistant", full_answer, citations=sources)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
