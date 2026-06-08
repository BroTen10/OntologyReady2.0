from __future__ import annotations

from typing import Any

import httpx

from ..config import settings
from .base import (
    ChatResponse,
    Chunk,
    DocInfo,
    KbInfo,
    Message,
    RAGProvider,
    SearchResult,
    TaskInfo,
)


class RAGFlowProvider(RAGProvider):
    """RAG provider backed by external RAGFlow engine via its REST API."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or settings.get_provider_config().get("rag", {}).get("config", {})
        self.base_url = cfg.get("base_url", "http://localhost:9380")
        self.api_key = cfg.get("api_key", "")
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=120,
            )
        return self._client

    # ── Knowledge Base CRUD ──────────────────────────────────

    async def create_knowledge_base(self, name: str, config: dict) -> KbInfo:
        client = await self._get_client()
        resp = await client.post(
            "/api/v1/datasets",
            json={"name": name, "description": config.get("description", ""), **config},
        )
        resp.raise_for_status()
        data = resp.json()
        kb_data = data.get("data", data)
        return KbInfo(
            kb_id=kb_data.get("id", ""),
            name=name,
            config=config,
        )

    async def list_knowledge_bases(self) -> list[KbInfo]:
        client = await self._get_client()
        resp = await client.get("/api/v1/datasets")
        resp.raise_for_status()
        data = resp.json()
        kb_list = data.get("data", [])
        return [
            KbInfo(kb_id=k.get("id", ""), name=k.get("name", ""), config={})
            for k in kb_list
        ]

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        client = await self._get_client()
        resp = await client.delete(f"/api/v1/datasets/{kb_id}")
        resp.raise_for_status()
        return True

    # ── Document Management ──────────────────────────────────

    async def upload_document(self, kb_id: str, file: bytes, filename: str) -> DocInfo:
        client = await self._get_client()
        resp = await client.post(
            f"/api/v1/datasets/{kb_id}/documents",
            files={"file": (filename, file)},
        )
        resp.raise_for_status()
        data = resp.json()
        doc_data = data.get("data", data)
        return DocInfo(
            doc_id=doc_data.get("id", ""),
            kb_id=kb_id,
            filename=filename,
            file_type="",
            status="pending",
        )

    async def list_documents(self, kb_id: str) -> list[DocInfo]:
        client = await self._get_client()
        resp = await client.get(f"/api/v1/datasets/{kb_id}/documents")
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("data", [])
        return [
            DocInfo(
                doc_id=d.get("id", ""),
                kb_id=kb_id,
                filename=d.get("name", ""),
                file_type="",
                status=d.get("status", "pending"),
            )
            for d in docs
        ]

    async def delete_document(self, doc_id: str) -> bool:
        client = await self._get_client()
        resp = await client.delete(f"/api/v1/documents/{doc_id}")
        resp.raise_for_status()
        return True

    # ── Parse / Process ──────────────────────────────────────

    async def parse_document(self, kb_id: str, doc_id: str) -> TaskInfo:
        client = await self._get_client()
        resp = await client.post(f"/api/v1/datasets/{kb_id}/chunks")
        resp.raise_for_status()
        return TaskInfo(task_id=doc_id, status="completed", progress=1.0)

    async def process_document(
        self, kb_id: str, doc_id: str, content: bytes, filename: str
    ) -> TaskInfo:
        return await self.parse_document(kb_id, doc_id)

    # ── Chunks ───────────────────────────────────────────────

    async def list_chunks(self, kb_id: str, doc_id: str) -> list[Chunk]:
        client = await self._get_client()
        resp = await client.get(
            f"/api/v1/datasets/{kb_id}/documents/{doc_id}/chunks"
        )
        resp.raise_for_status()
        data = resp.json()
        chunks = data.get("data", [])
        return [
            Chunk(
                chunk_id=c.get("id", ""),
                doc_id=doc_id,
                content=c.get("content", ""),
                metadata=c.get("metadata", {}),
            )
            for c in chunks
        ]

    # ── Search ───────────────────────────────────────────────

    async def search(
        self, kb_id: str, query: str, top_k: int = 10
    ) -> list[SearchResult]:
        client = await self._get_client()
        resp = await client.post(
            f"/api/v1/retrieval",
            json={
                "question": query,
                "dataset_ids": [kb_id],
                "top_k": top_k,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        records = data.get("data", {}).get("chunks", [])
        return [
            SearchResult(
                doc_id=r.get("document_id", ""),
                chunk_id=r.get("id", ""),
                content=r.get("content", ""),
                score=r.get("similarity", 0.0),
            )
            for r in records
        ]

    # ── Chat / QA ────────────────────────────────────────────

    async def chat(
        self,
        kb_id: str,
        question: str,
        history: list | None = None,
        top_k: int = 5,
    ) -> ChatResponse:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "question": question,
            "dataset_ids": [kb_id],
            "top_k": top_k,
        }
        if history:
            payload["history"] = history
        resp = await client.post("/api/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("data", {}).get("answer", "")
        return ChatResponse(content=answer, model="ragflow", usage=None, finish_reason="stop")

    async def chat_stream(
        self,
        kb_id: str,
        question: str,
        history: list | None = None,
        top_k: int = 5,
    ):
        client = await self._get_client()
        payload: dict[str, Any] = {
            "question": question,
            "dataset_ids": [kb_id],
            "top_k": top_k,
            "stream": True,
        }
        if history:
            payload["history"] = history
        async with client.stream("POST", "/api/v1/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    import json
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("data", {}).get("answer", "")
                    except json.JSONDecodeError:
                        delta = data_str
                    if delta:
                        yield delta
