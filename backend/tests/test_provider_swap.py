from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.security import create_access_token
from app.providers.base import (
    LLMProvider, EmbeddingProvider, RAGProvider,
    DocumentEngineProvider, FileStorageProvider, GraphDBProvider,
    Message, ChatResponse, ModelInfo, SearchResult, Chunk,
    Document, KbInfo, DocInfo, TaskInfo, Subgraph, TraversalResult,
)


make_auth_headers = lambda uid="admin-id": {"Authorization": f"Bearer {create_access_token({'sub': uid, 'jti': 'jti'})}"}


class MockLLMProvider(LLMProvider):
    async def chat(self, messages, **kwargs):
        return ChatResponse(content="mock reply", model="mock-model")

    async def chat_stream(self, messages, **kwargs):
        yield "mock "
        yield "reply"

    def supports_function_calling(self):
        return True

    def list_models(self):
        return [ModelInfo(id="mock-model", name="Mock Model", provider="mock")]


class MockEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts, **kwargs):
        return [[0.1] * 1536 for _ in texts]

    def dimension(self):
        return 1536


class MockRAGProvider(RAGProvider):
    async def create_knowledge_base(self, name, config):
        return KbInfo(kb_id="mock-kb", name=name)

    async def upload_document(self, kb_id, file, filename):
        return DocInfo(doc_id="mock-doc", kb_id=kb_id, filename=filename, status="uploaded")

    async def parse_document(self, kb_id, doc_id):
        return TaskInfo(task_id="mock-task", status="completed")

    async def list_chunks(self, kb_id, doc_id):
        return [Chunk(chunk_id="c1", doc_id=doc_id, content="mock chunk")]

    async def search(self, kb_id, query, top_k=10):
        return [SearchResult(doc_id="d1", chunk_id="c1", content="mock result", score=0.9)]

    async def chat(self, kb_id, question, history=None, top_k=5):
        return ChatResponse(content="mock answer")

    async def chat_stream(self, kb_id, question, history=None, top_k=5):
        yield "mock "
        yield "answer"


class TestProviderSwap:
    """验证 Provider 可替换性 — 切换不同 Provider 实现验证接口一致性"""

    def test_llm_provider_swap(self):
        """Verify mock LLM provider satisfies all interface methods"""
        provider = MockLLMProvider()
        assert isinstance(provider, LLMProvider)

        # All abstract methods must be callable without error
        assert provider.supports_function_calling() is True
        models = provider.list_models()
        assert len(models) == 1
        assert models[0].id == "mock-model"

    def test_embedding_provider_swap(self):
        """Verify mock embedding provider satisfies all interface methods"""
        provider = MockEmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)
        assert provider.dimension() == 1536

    def test_rag_provider_swap(self):
        """Verify mock RAG provider satisfies all interface methods"""
        provider = MockRAGProvider()
        assert isinstance(provider, RAGProvider)

    def test_factory_registry_can_register_new_providers(self):
        """Verify that new providers can be registered at runtime"""
        from app.providers.factory import register_provider, _provider_registry

        class CustomLLMProvider(LLMProvider):
            async def chat(self, messages, **kwargs):
                return ChatResponse(content="custom")
            async def chat_stream(self, messages, **kwargs):
                yield "custom"
            def supports_function_calling(self):
                return False
            def list_models(self):
                return []

        register_provider("custom_llm", CustomLLMProvider)
        assert "custom_llm" in _provider_registry
        assert _provider_registry["custom_llm"] == CustomLLMProvider

    def test_all_provider_types_abc_consistency(self):
        """Verify each ABC has at least one abstract method"""
        from app.providers.base import (
            LLMProvider, EmbeddingProvider, RAGProvider,
            DocumentEngineProvider, FileStorageProvider, GraphDBProvider,
            DataSourceProvider,
        )
        for cls in [LLMProvider, EmbeddingProvider, RAGProvider,
                     DocumentEngineProvider, FileStorageProvider, GraphDBProvider,
                     DataSourceProvider]:
            assert len(cls.__abstractmethods__) > 0, f"{cls.__name__} should have abstract methods"


async def test_acr_list_config(client, mock_store_auth):
    """Test ACR config listing endpoint"""
    with (
        patch("app.api.acr.acr_store.get_acr_config", new_callable=AsyncMock) as get_cfg,
    ):
        get_cfg.return_value = {"acr_enabled": False}
        resp = client.get("/api/acr/config", headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


async def test_acr_create_rule(client, mock_store_auth):
    """Test ACR rule creation"""
    with patch("app.api.acr.acr_store.create_rule", new_callable=AsyncMock) as create_rule:
        create_rule.return_value = {
            "id": 1, "name": "test-rule", "resource_type": "dataset",
            "field": "owner_id", "operator": "eq", "value": "user:user_id",
            "priority": 0, "enabled": True,
        }
        resp = client.post("/api/acr/rules", json={
            "name": "test-rule", "resource_type": "dataset",
            "field": "owner_id", "operator": "eq", "value": "user:user_id",
        }, headers=make_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == 1


async def test_acr_config_update(client, mock_store_auth):
    """Test ACR config update"""
    with (
        patch("app.api.acr.acr_store.update_acr_config", new_callable=AsyncMock) as set_cfg,
    ):
        set_cfg.return_value = {"acr_enabled": True, "row_level_security": True}
        resp = client.put("/api/acr/config", json={
            "acr_enabled": True, "row_level_security": True,
        }, headers=make_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_public_list_acr_rules(client, mock_store_auth):
    """Test listing ACR rules"""
    with patch("app.api.acr.acr_store.list_rules", new_callable=AsyncMock) as list_rules:
        list_rules.return_value = [{
            "id": 1, "name": "r1", "description": None, "resource_type": "dataset",
            "field": "owner", "operator": "eq", "value": "user:user_id",
            "priority": 0, "enabled": True,
        }]
        resp = client.get("/api/acr/rules", headers=make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
