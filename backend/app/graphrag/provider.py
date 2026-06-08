"""GraphRAG Provider — knowledge graph enhanced retrieval.

Entity extraction → knowledge graph construction → community detection →
6 retrieval modes (local/global/hybrid/mixed/naive/bypass) → multi-turn QA.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from ..graphrag import store as graphrag_store
from ..providers.base import ChatResponse, Message
from ..providers.factory import get_llm, get_embedding
from ..rag.parsers import BaseParser
from ..rag.chunkers import FixedSizeChunker

ENTITY_TYPES = ["organization", "person", "geo", "event", "category"]

ENTITY_EXTRACTION_PROMPT = """你是一个知识图谱实体抽取专家。从以下文本中抽取所有重要实体。

实体类型只能是以下之一: {entity_types}

对于每个实体，提取:
- name: 实体名称
- entity_type: 实体类型
- description: 简短描述(一句话)
- properties: 额外属性(JSON对象)

请严格按JSON数组格式输出,每个元素是一个实体对象:
[
  {{"name": "实体名", "entity_type": "organization", "description": "描述", "properties": {{"key": "value"}}}}
]

只输出JSON数组,不要其他内容。

文本:
{text}"""

RELATION_EXTRACTION_PROMPT = """你是一个知识图谱关系抽取专家。给定实体列表和文本，找出实体之间的关系。

已知实体:
{entities}

从以下文本中抽取实体间的关系。对于每个关系:
- source_name: 源实体名称(必须精确匹配已知实体)
- target_name: 目标实体名称(必须精确匹配已知实体)
- relation_type: 关系类型(如 works_for, located_in, founded_by, part_of, related_to, manages, owns, collaborates_with 等)
- description: 关系描述(一句话)

请严格按JSON数组格式输出:
[
  {{"source_name": "源实体名", "target_name": "目标实体名", "relation_type": "关系类型", "description": "描述"}}
]

只输出JSON数组,不要其他内容。

文本:
{text}"""

COMMUNITY_SUMMARY_PROMPT = """你是一个知识图谱社区分析专家。以下是图谱中一个社区的实体和关系信息，请生成该社区的摘要。

社区标题: {title}

实体列表:
{entities_text}

关系列表:
{relations_text}

请生成:
1. summary: 社区整体摘要(2-3句话,描述这个社区的主要内容和特征)

以JSON格式输出:
{{"summary": "社区摘要"}}

只输出JSON,不要其他内容。"""

QA_SYSTEM_PROMPT = """你是一个基于知识图谱的问答助手。以下是知识图谱中检索到的相关信息。

请严格基于以下上下文回答问题。如果上下文没有相关信息，请明确告知用户。

上下文:
{context}"""


class GraphRAGProvider:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._chunker = FixedSizeChunker(chunk_size=self._config.get("chunk_size", 1000))
        self._embed_batch_size = self._config.get("embed_batch_size", 16)

    @property
    def _llm(self):
        return get_llm()

    @property
    def _embedding(self):
        return get_embedding()

    # ═══════════════════════════════════════════════════════
    # Workspace Management
    # ═══════════════════════════════════════════════════════

    async def create_workspace(self, name: str, description: str = "", config: dict | None = None) -> dict:
        ws = await graphrag_store.create_workspace(name, description, config)
        return ws

    async def list_workspaces(self) -> list[dict]:
        return await graphrag_store.list_workspaces()

    async def get_workspace(self, ws_id: str) -> dict | None:
        return await graphrag_store.get_workspace(ws_id)

    async def update_workspace(self, ws_id: str, **kwargs) -> dict | None:
        return await graphrag_store.update_workspace(ws_id, **kwargs)

    async def delete_workspace(self, ws_id: str) -> bool:
        return await graphrag_store.delete_workspace(ws_id)

    async def set_default_workspace(self, ws_id: str) -> None:
        await graphrag_store.set_default_workspace(ws_id)

    async def get_default_workspace(self) -> dict | None:
        return await graphrag_store.get_default_workspace()

    # ═══════════════════════════════════════════════════════
    # Document Processing
    # ═══════════════════════════════════════════════════════

    async def upload_document(self, workspace_id: str, file_content: bytes, filename: str) -> dict:
        doc = await graphrag_store.create_document(workspace_id, filename, file_content)
        return doc

    async def list_documents(self, workspace_id: str) -> list[dict]:
        return await graphrag_store.list_documents(workspace_id)

    async def get_document(self, doc_id: str) -> dict | None:
        return await graphrag_store.get_document(doc_id)

    async def delete_document(self, doc_id: str) -> bool:
        return await graphrag_store.delete_document(doc_id)

    async def process_document(self, workspace_id: str, doc_id: str, file_content: bytes, filename: str) -> dict:
        """Full pipeline: parse → chunk → extract entities/relations → build graph → detect communities."""
        await graphrag_store.update_document_status(doc_id, "processing")

        try:
            parser = BaseParser.for_filename(filename)
            text = parser.parse(file_content, filename)
            chunks = self._chunker.chunk(text)

            all_entities: dict[str, str] = {}
            all_relations: list[dict] = []

            for chunk in chunks:
                entities = await self._extract_entities(chunk["content"])
                for e in entities:
                    key = e["name"].lower().strip()
                    if key not in all_entities:
                        e["entity_id"] = uuid.uuid4().hex[:12]
                        all_entities[key] = e

            if all_entities:
                entity_list = list(all_entities.values())
                entity_names = [e["name"] for e in entity_list]

                for chunk in chunks:
                    rels = await self._extract_relations(chunk["content"], entity_names)
                    for r in rels:
                        src_key = r["source_name"].lower().strip()
                        tgt_key = r["target_name"].lower().strip()
                        if src_key in all_entities and tgt_key in all_entities:
                            all_relations.append({
                                "relation_id": uuid.uuid4().hex[:12],
                                "source_id": all_entities[src_key]["entity_id"],
                                "target_id": all_entities[tgt_key]["entity_id"],
                                "relation_type": r["relation_type"],
                                "description": r.get("description", ""),
                                "properties": r.get("properties", {}),
                            })

            if all_entities:
                await graphrag_store.save_entities(workspace_id, [
                    {"entity_id": e["entity_id"], "name": e["name"], "entity_type": e["entity_type"],
                     "description": e.get("description", ""), "properties": e.get("properties", {})}
                    for e in all_entities.values()
                ])

            if all_relations:
                await graphrag_store.save_relations(workspace_id, all_relations)

            if all_entities:
                communities = await self._detect_communities(workspace_id)
                await graphrag_store.save_communities(workspace_id, communities)

            await graphrag_store.update_document_status(doc_id, "processed")
            return {"doc_id": doc_id, "status": "completed",
                    "entity_count": len(all_entities), "relation_count": len(all_relations)}

        except Exception as e:
            await graphrag_store.update_document_status(doc_id, "failed")
            return {"doc_id": doc_id, "status": "failed", "error": str(e)}

    async def _extract_entities(self, text: str) -> list[dict]:
        prompt = ENTITY_EXTRACTION_PROMPT.format(
            entity_types=", ".join(ENTITY_TYPES),
            text=text[:6000],
        )
        try:
            resp = await self._llm.chat([Message(role="user", content=prompt)])
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(content)
        except Exception:
            return []

    async def _extract_relations(self, text: str, entity_names: list[str]) -> list[dict]:
        prompt = RELATION_EXTRACTION_PROMPT.format(
            entities="\n".join(f"- {n}" for n in entity_names[:50]),
            text=text[:6000],
        )
        try:
            resp = await self._llm.chat([Message(role="user", content=prompt)])
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(content)
        except Exception:
            return []

    async def _detect_communities(self, workspace_id: str) -> list[dict]:
        """Simple community detection based on connected components."""
        entities = await graphrag_store.list_entities(workspace_id)
        relations = await graphrag_store.list_relations(workspace_id)

        if not entities:
            return []

        adj: dict[str, set[str]] = {e["entity_id"]: set() for e in entities}
        for r in relations:
            src = r["source_id"]
            tgt = r["target_id"]
            if src in adj and tgt in adj:
                adj[src].add(tgt)
                adj[tgt].add(src)

        visited: set[str] = set()
        communities: list[dict] = []

        for entity in entities:
            eid = entity["entity_id"]
            if eid in visited:
                continue
            comp = self._bfs_component(eid, adj)
            visited.update(comp)
            if comp:
                comp_entities = [e for e in entities if e["entity_id"] in comp]
                comp_relations = [r for r in relations if r["source_id"] in comp and r["target_id"] in comp]
                title = ", ".join(e["name"] for e in comp_entities[:5])
                if len(comp_entities) > 5:
                    title += f" 等{len(comp_entities)}个实体"
                summary = await self._summarize_community(title, comp_entities, comp_relations)
                communities.append({
                    "title": title,
                    "summary": summary,
                    "entity_ids": list(comp),
                    "weight": len(comp_relations) + len(comp),
                })

        return communities

    def _bfs_component(self, start: str, adj: dict[str, set[str]]) -> set[str]:
        visited: set[str] = set()
        queue = [start]
        visited.add(start)
        while queue:
            node = queue.pop(0)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    async def _summarize_community(self, title: str, entities: list[dict], relations: list[dict]) -> str:
        entities_text = "\n".join(
            f"- {e['name']} ({e.get('entity_type', 'unknown')}): {e.get('description', '')}"
            for e in entities[:20]
        )
        relations_text = "\n".join(
            f"- {r.get('source_id', '')} -[{r.get('relation_type', '')}]-> {r.get('target_id', '')}"
            for r in relations[:30]
        )
        prompt = COMMUNITY_SUMMARY_PROMPT.format(
            title=title, entities_text=entities_text, relations_text=relations_text,
        )
        try:
            resp = await self._llm.chat([Message(role="user", content=prompt)])
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
            result = json.loads(content)
            return result.get("summary", f"包含 {len(entities)} 个实体的社区")
        except Exception:
            return f"包含 {len(entities)} 个实体的社区"

    # ═══════════════════════════════════════════════════════
    # Graph Operations
    # ═══════════════════════════════════════════════════════

    async def get_graph_data(self, workspace_id: str) -> dict:
        entities = await graphrag_store.list_entities(workspace_id)
        relations = await graphrag_store.list_relations(workspace_id)
        stats = await graphrag_store.get_graph_stats(workspace_id)

        entity_map = {e["entity_id"]: e for e in entities}

        nodes = [
            {
                "id": e["entity_id"],
                "label": e["name"],
                "entity_type": e.get("entity_type", "organization"),
                "description": e.get("description", ""),
                "properties": e.get("properties", {}),
            }
            for e in entities
        ]

        edges = [
            {
                "id": r["relation_id"],
                "source": r["source_id"],
                "target": r["target_id"],
                "label": r.get("relation_type", ""),
                "source_name": entity_map.get(r["source_id"], {}).get("name", r["source_id"]),
                "target_name": entity_map.get(r["target_id"], {}).get("name", r["target_id"]),
            }
            for r in relations
        ]

        return {"nodes": nodes, "edges": edges, "stats": stats}

    async def get_graph_stats(self, workspace_id: str) -> dict:
        return await graphrag_store.get_graph_stats(workspace_id)

    async def get_neighbors(self, workspace_id: str, entity_id: str, depth: int = 1) -> dict:
        entity = await graphrag_store.get_entity(entity_id)
        if not entity:
            return {"nodes": [], "edges": []}

        relations = await graphrag_store.list_relations(workspace_id)
        entities = {e["entity_id"]: e for e in await graphrag_store.list_entities(workspace_id)}

        edge_map: dict[str, list] = {}
        for r in relations:
            src = r["source_id"]
            tgt = r["target_id"]
            edge_map.setdefault(src, []).append(tgt)
            edge_map.setdefault(tgt, []).append(src)

        visited: set[str] = set()
        current = {entity_id}
        all_edges: set[str] = set()

        for _ in range(depth):
            next_level: set[str] = set()
            for nid in current:
                visited.add(nid)
                for neighbor in edge_map.get(nid, []):
                    if neighbor not in visited:
                        edge_key = tuple(sorted([nid, neighbor]))
                        all_edges.add(edge_key)
                        next_level.add(neighbor)
                        visited.add(neighbor)
            current = next_level

        node_ids: set[str] = {entity_id}
        for src, tgt in all_edges:
            node_ids.add(src)
            node_ids.add(tgt)

        nodes = []
        for nid in node_ids:
            e = entities.get(nid, {})
            nodes.append({
                "id": nid,
                "label": e.get("name", nid),
                "entity_type": e.get("entity_type", "organization"),
                "description": e.get("description", ""),
            })

        edges = []
        seen_edges: set[str] = set()
        for r in relations:
            pair = tuple(sorted([r["source_id"], r["target_id"]]))
            if pair in all_edges and r["relation_id"] not in seen_edges:
                seen_edges.add(r["relation_id"])
                edges.append({
                    "id": r["relation_id"],
                    "source": r["source_id"],
                    "target": r["target_id"],
                    "label": r.get("relation_type", ""),
                })

        return {"nodes": nodes, "edges": edges}

    async def search_entities(self, workspace_id: str, query: str, entity_type: str | None = None) -> list[dict]:
        entities = await graphrag_store.list_entities(workspace_id, entity_type)
        if not query:
            return entities
        q = query.lower()
        return [e for e in entities if q in e.get("name", "").lower() or q in e.get("description", "").lower()]

    # ═══════════════════════════════════════════════════════
    # Communities
    # ═══════════════════════════════════════════════════════

    async def get_communities(self, workspace_id: str) -> list[dict]:
        return await graphrag_store.list_communities(workspace_id)

    # ═══════════════════════════════════════════════════════
    # Retrieval Modes
    # ═══════════════════════════════════════════════════════

    async def _local_search(self, workspace_id: str, query: str, top_k: int = 10) -> list[str]:
        """Local search: find relevant entities, then expand neighbors."""
        entities = await graphrag_store.list_entities(workspace_id)
        if not entities:
            return []

        q = query.lower()
        scored = []
        for e in entities:
            score = 0
            if q in e.get("name", "").lower():
                score += 10
            if q in e.get("description", "").lower():
                score += 5
            entity_type = e.get("entity_type", "")
            for word in q.split():
                if word in entity_type.lower():
                    score += 2
            if score > 0:
                scored.append((e, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_entities = scored[:top_k]

        context_parts = []
        seen: set[str] = set()

        for entity, score in top_entities:
            eid = entity["entity_id"]
            if eid not in seen:
                seen.add(eid)
                context_parts.append(
                    f"[实体] {entity['name']} ({entity.get('entity_type', '')}): {entity.get('description', '')}"
                )

            neighbors = await self.get_neighbors(workspace_id, eid, depth=1)
            for node in neighbors.get("nodes", []):
                nid = node.get("id", "")
                if nid not in seen:
                    seen.add(nid)
                    label = node.get("label", node.get("id", ""))
                    context_parts.append(
                        f"[关联实体] {label} ({node.get('entity_type', '')}): {node.get('description', '')}"
                    )

            for edge in neighbors.get("edges", []):
                context_parts.append(
                    f"[关系] {edge.get('source', '')} -[{edge.get('label', '')}]-> {edge.get('target', '')}"
                )

        return context_parts

    async def _global_search(self, workspace_id: str, query: str, top_k: int = 5) -> list[str]:
        """Global search: use community summaries as context."""
        communities = await graphrag_store.list_communities(workspace_id)
        if not communities:
            return []

        q = query.lower()
        scored = []
        for c in communities:
            score = 0
            if q in c.get("title", "").lower():
                score += 10
            if q in c.get("summary", "").lower():
                score += 5
            if score > 0:
                scored.append((c, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        context_parts = []
        for c, _ in scored[:top_k]:
            context_parts.append(f"## {c['title']}\n{c.get('summary', '')}")

        return context_parts

    async def _hybrid_search(self, workspace_id: str, query: str, top_k: int = 5) -> list[str]:
        """Hybrid: combine local + global context."""
        local_ctx = await self._local_search(workspace_id, query, top_k)
        global_ctx = await self._global_search(workspace_id, query, top_k)
        return local_ctx + ["\n--- 全局视角 ---\n"] + global_ctx

    async def _naive_search(self, workspace_id: str, query: str, top_k: int = 5) -> list[str]:
        """Naive RAG: use entity descriptions + relations as context."""
        entities = await graphrag_store.list_entities(workspace_id)
        relations = await graphrag_store.list_relations(workspace_id)

        context_parts = []
        context_parts.append("## 实体列表")
        for e in entities[:50]:
            context_parts.append(f"- {e['name']} ({e.get('entity_type', '')}): {e.get('description', '')}")

        context_parts.append("\n## 关系列表")
        entity_names = {e["entity_id"]: e.get("name", e["entity_id"]) for e in entities}
        for r in relations[:100]:
            src_name = entity_names.get(r["source_id"], r["source_id"])
            tgt_name = entity_names.get(r["target_id"], r["target_id"])
            context_parts.append(f"- {src_name} -[{r.get('relation_type', '')}]-> {tgt_name}")

        return context_parts

    async def _mixed_search(self, workspace_id: str, query: str, top_k: int = 5) -> list[str]:
        """Mixed: hybrid + naive combined."""
        hybrid = await self._hybrid_search(workspace_id, query, top_k)
        naive = await self._naive_search(workspace_id, query, top_k)
        return hybrid + naive

    async def retrieve(self, workspace_id: str, query: str, mode: str = "hybrid", top_k: int = 5) -> list[str]:
        """Execute retrieval in the specified mode."""
        modes = {
            "local": self._local_search,
            "global": self._global_search,
            "hybrid": self._hybrid_search,
            "mixed": self._mixed_search,
            "naive": self._naive_search,
        }
        handler = modes.get(mode, self._hybrid_search)
        return await handler(workspace_id, query, top_k)

    # ═══════════════════════════════════════════════════════
    # QA / Chat
    # ═══════════════════════════════════════════════════════

    def _build_qa_messages(self, context_parts: list[str], question: str, history: list | None) -> list[Message]:
        context = "\n\n".join(context_parts) if context_parts else "知识图谱中没有相关信息。"
        messages = [Message(role="system", content=QA_SYSTEM_PROMPT.format(context=context))]
        if history:
            for h in history[-10:]:
                messages.append(Message(role=h.get("role", "user"), content=h.get("content", "")))
        messages.append(Message(role="user", content=question))
        return messages

    async def chat(self, workspace_id: str, question: str, history: list | None = None,
                   mode: str = "hybrid") -> ChatResponse:
        if mode == "bypass":
            messages = [
                Message(role="system",
                        content="你是一个知识问答助手。请基于你的知识回答问题。如果不知道，请明确告知。"),
            ]
            if history:
                for h in history[-10:]:
                    messages.append(Message(role=h.get("role", "user"), content=h.get("content", "")))
            messages.append(Message(role="user", content=question))
            return await self._llm.chat(messages)

        context_parts = await self.retrieve(workspace_id, question, mode)
        messages = self._build_qa_messages(context_parts, question, history)
        return await self._llm.chat(messages)

    async def chat_stream(self, workspace_id: str, question: str, history: list | None = None,
                          mode: str = "hybrid"):
        if mode == "bypass":
            messages = [
                Message(role="system",
                        content="你是一个知识问答助手。请基于你的知识回答问题。如果不知道，请明确告知。"),
            ]
            if history:
                for h in history[-10:]:
                    messages.append(Message(role=h.get("role", "user"), content=h.get("content", "")))
            messages.append(Message(role="user", content=question))
        else:
            context_parts = await self.retrieve(workspace_id, question, mode)
            messages = self._build_qa_messages(context_parts, question, history)

        async for token in self._llm.chat_stream(messages):
            yield token

    # ═══════════════════════════════════════════════════════
    # Model Configs
    # ═══════════════════════════════════════════════════════

    async def create_model_config(self, workspace_id: str, model_type: str, provider_name: str,
                                  model_name: str, config: dict | None = None, is_default: bool = False) -> dict:
        return await graphrag_store.create_model_config(
            workspace_id, model_type, provider_name, model_name, config, is_default,
        )

    async def list_model_configs(self, workspace_id: str = "", model_type: str | None = None) -> list[dict]:
        return await graphrag_store.list_model_configs(workspace_id, model_type)

    async def get_model_config(self, config_id: str) -> dict | None:
        return await graphrag_store.get_model_config(config_id)

    async def update_model_config(self, config_id: str, **kwargs) -> dict | None:
        return await graphrag_store.update_model_config(config_id, **kwargs)

    async def delete_model_config(self, config_id: str) -> bool:
        return await graphrag_store.delete_model_config(config_id)


_graphrag_instance: GraphRAGProvider | None = None


def get_graphrag() -> GraphRAGProvider:
    global _graphrag_instance
    if _graphrag_instance is None:
        _graphrag_instance = GraphRAGProvider()
    return _graphrag_instance
