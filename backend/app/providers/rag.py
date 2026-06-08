"""Builtin RAG Provider — full implementation.

Composed from DocumentEngine + Embedding + LLM providers + FileStorage.
Handles: KB CRUD, document upload/parse/chunk, search (fts/vector/hybrid), QA chat.
"""
from __future__ import annotations

from typing import Any

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
from .document_engine import PostgresDocumentEngine
from .embedding import DeepSeekEmbedding
from .file_storage import LocalFileStorage
from .llm import DeepSeekProvider
from ..rag.parsers import BaseParser
from ..rag.chunkers import (
    BaseChunker,
    FixedSizeChunker,
    HeadingChunker,
    ParagraphChunker,
    SemanticChunker,
)
from ..rag import store as rag_store

CHUNKER_REGISTRY: dict[str, type[BaseChunker]] = {
    "fixed_size": FixedSizeChunker,
    "paragraph": ParagraphChunker,
    "heading": HeadingChunker,
    "semantic": SemanticChunker,
}


def _make_chunker(config: dict[str, Any]) -> BaseChunker:
    chunker_type = config.get("chunker", "fixed_size")
    chunker_kwargs = config.get("chunker_kwargs", {})
    cls = CHUNKER_REGISTRY.get(chunker_type, FixedSizeChunker)
    return cls(**chunker_kwargs)


class BuiltinRAGProvider(RAGProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._doc_engine = PostgresDocumentEngine()
        self._embedding = DeepSeekEmbedding()
        self._llm = DeepSeekProvider()
        self._chunker = _make_chunker(self._config)
        self._embed_batch_size = self._config.get("embed_batch_size", 16)

    # ═══════════════════════════════════════════════════════
    # Knowledge Base CRUD
    # ═══════════════════════════════════════════════════════

    async def create_knowledge_base(self, name: str, config: dict) -> KbInfo:
        kb = await rag_store.create_kb(name, config.get("description", ""), config)
        return KbInfo(kb_id=kb["kb_id"], name=kb["name"], config=kb.get("config", {}))

    async def list_knowledge_bases(self) -> list[KbInfo]:
        kbs = await rag_store.list_kbs()
        return [KbInfo(kb_id=k["kb_id"], name=k["name"], config=k.get("config", {})) for k in kbs]

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        return await rag_store.delete_kb(kb_id)

    # ═══════════════════════════════════════════════════════
    # Document Upload & Processing
    # ═══════════════════════════════════════════════════════

    async def upload_document(self, kb_id: str, file: bytes, filename: str) -> DocInfo:
        doc = await rag_store.create_document(kb_id, filename, file)
        # Persist file content via FileStorage so it can be re-processed
        from .factory import get_file_storage
        file_storage = get_file_storage()
        file_key = f"rag/{kb_id}/{doc['doc_id']}/{filename}"
        await file_storage.upload(file_key, file)
        file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return DocInfo(
            doc_id=doc["doc_id"], kb_id=kb_id, filename=filename,
            file_type=file_type, status=doc["status"],
        )

    async def list_documents(self, kb_id: str) -> list[DocInfo]:
        docs = await rag_store.list_documents(kb_id)
        return [
            DocInfo(
                doc_id=d["doc_id"], kb_id=d["kb_id"], filename=d["filename"],
                file_type=d.get("file_type", ""), status=d["status"],
            )
            for d in docs
        ]

    async def delete_document(self, doc_id: str) -> bool:
        return await rag_store.delete_document(doc_id)

    # ═══════════════════════════════════════════════════════
    # Parse & Chunk
    # ═══════════════════════════════════════════════════════

    async def parse_document(self, kb_id: str, doc_id: str) -> TaskInfo:
        """Parse already-uploaded document content."""
        doc = await rag_store.get_document(doc_id)
        if not doc:
            return TaskInfo(task_id=doc_id, status="failed")

        await rag_store.update_document_status(doc_id, "processing")

        try:
            from .factory import get_file_storage
            file_storage = get_file_storage()
            file_key = f"rag/{kb_id}/{doc_id}/{doc['filename']}"
            content = await file_storage.download(file_key)
            parser = BaseParser.for_filename(doc["filename"])
            text = parser.parse(content, doc["filename"])
            chunks = self._chunker.chunk(text)
            await rag_store.save_chunks(kb_id, doc_id, chunks)

            await rag_store.update_document_status(doc_id, "processed")
            return TaskInfo(task_id=doc_id, status="completed", progress=1.0)
        except Exception:
            await rag_store.update_document_status(doc_id, "failed")
            return TaskInfo(task_id=doc_id, status="failed")

    async def process_document(self, kb_id: str, doc_id: str, content: bytes, filename: str) -> TaskInfo:
        """Full pipeline: parse → chunk → embed → index."""
        await rag_store.update_document_status(doc_id, "processing")

        try:
            # Parse
            parser = BaseParser.for_filename(filename)
            text = parser.parse(content, filename)

            # Chunk
            chunks = self._chunker.chunk(text)
            saved_chunks = await rag_store.save_chunks(kb_id, doc_id, chunks)

            # Embed (in batches to avoid rate limits)
            chunk_texts = [c["content"] for c in saved_chunks]
            for i in range(0, len(chunk_texts), self._embed_batch_size):
                batch = chunk_texts[i:i + self._embed_batch_size]
                embeddings = await self._embedding.embed(batch)
                for j, emb in enumerate(embeddings):
                    chunk_idx = i + j
                    if chunk_idx < len(saved_chunks):
                        await rag_store.update_chunk_embedding(saved_chunks[chunk_idx]["chunk_id"], emb)

            await rag_store.update_document_status(doc_id, "processed")
            return TaskInfo(task_id=doc_id, status="completed", progress=1.0)
        except Exception:
            await rag_store.update_document_status(doc_id, "failed")
            return TaskInfo(task_id=doc_id, status="failed")

    # ═══════════════════════════════════════════════════════
    # Chunks
    # ═══════════════════════════════════════════════════════

    async def list_chunks(self, kb_id: str, doc_id: str) -> list[Chunk]:
        chunks = await rag_store.get_chunks_by_doc(doc_id)
        return [
            Chunk(
                chunk_id=c["chunk_id"], doc_id=c["doc_id"], content=c["content"],
                metadata=c.get("metadata", {}),
            )
            for c in chunks
        ]

    # ═══════════════════════════════════════════════════════
    # Search
    # ═══════════════════════════════════════════════════════

    async def search(self, kb_id: str, query: str, top_k: int = 10) -> list[SearchResult]:
        # Vector search
        try:
            embeddings = await self._embedding.embed([query])
            vec_results = await rag_store.search_vector(embeddings[0], kb_id, top_k)
        except Exception:
            vec_results = []

        # FTS
        fts_results = await rag_store.search_fts(query, kb_id, top_k)

        # Merge: FTS first, then vector results not already in FTS
        merged: dict[str, dict] = {}
        for r in fts_results:
            merged[r["chunk_id"]] = r
        for r in vec_results:
            if r["chunk_id"] not in merged:
                merged[r["chunk_id"]] = r

        results = sorted(merged.values(), key=lambda r: r.get("score", 0), reverse=True)
        return [
            SearchResult(
                doc_id=r["doc_id"], chunk_id=r["chunk_id"], content=r["content"],
                score=r.get("score", 0.0), metadata=r.get("metadata", {}),
            )
            for r in results[:top_k]
        ]

    # ═══════════════════════════════════════════════════════
    # Chat / QA
    # ═══════════════════════════════════════════════════════

    def _build_chat_messages(self, kb_id: str, question: str, context: str, history: list | None) -> list[Message]:
        messages = [
            Message(
                role="system",
                content=(
                    "你是一个基于知识库的问答助手。请严格基于以下上下文回答问题。"
                    "如果上下文没有相关信息，请明确告知用户。\n\n上下文：\n" + context
                ),
            ),
        ]
        if history:
            for h in history:
                messages.append(Message(role=h.get("role", "user"), content=h.get("content", "")))
        messages.append(Message(role="user", content=question))
        return messages

    async def chat(self, kb_id: str, question: str, history: list | None = None, top_k: int = 5) -> ChatResponse:
        results = await self.search(kb_id, question, top_k=top_k)
        context = "\n\n".join(f"[来源 {i + 1}] {r.content}" for i, r in enumerate(results))
        messages = self._build_chat_messages(kb_id, question, context, history)
        return await self._llm.chat(messages)

    async def chat_stream(self, kb_id: str, question: str, history: list | None = None, top_k: int = 5):
        results = await self.search(kb_id, question, top_k=top_k)
        context = "\n\n".join(f"[来源 {i + 1}] {r.content}" for i, r in enumerate(results))
        messages = self._build_chat_messages(kb_id, question, context, history)
        async for token in self._llm.chat_stream(messages):
            yield token
        sources = [
            {
                "chunk_id": r.chunk_id, "content": r.content,
                "doc_id": r.doc_id, "filename": r.metadata.get("filename", ""),
                "score": round(r.score, 4),
            }
            for r in results
        ]
        yield sources
