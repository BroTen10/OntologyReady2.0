from __future__ import annotations

import pytest
from app.providers.base import (
    ChatResponse,
    Chunk,
    DataSourceConfig,
    DocInfo,
    Document,
    KbInfo,
    Message,
    ModelInfo,
    SearchResult,
    Subgraph,
    TaskInfo,
    TraversalResult,
)


def test_message_dataclass():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_chat_response_dataclass():
    resp = ChatResponse(content="hi", model="gpt-4", finish_reason="stop")
    assert resp.content == "hi"
    assert resp.model == "gpt-4"
    assert resp.finish_reason == "stop"


def test_model_info_dataclass():
    mi = ModelInfo(id="deepseek-chat", name="DeepSeek", provider="deepseek")
    assert mi.id == "deepseek-chat"
    assert mi.name == "DeepSeek"


def test_document_dataclass():
    doc = Document(doc_id="d1", kb_id="kb1", filename="test.pdf", content="hello world")
    assert doc.doc_id == "d1"
    assert doc.filename == "test.pdf"


def test_chunk_dataclass():
    chunk = Chunk(chunk_id="c1", doc_id="d1", content="hello")
    assert chunk.chunk_id == "c1"
    assert chunk.content == "hello"
    assert chunk.metadata == {}


def test_search_result_dataclass():
    sr = SearchResult(doc_id="d1", chunk_id="c1", content="result", score=0.95)
    assert sr.score == 0.95


def test_kb_info_dataclass():
    kb = KbInfo(kb_id="kb1", name="test-kb", config={"chunk_size": 500})
    assert kb.name == "test-kb"
    assert kb.config["chunk_size"] == 500


def test_doc_info_dataclass():
    di = DocInfo(doc_id="d1", kb_id="kb1", filename="doc.pdf", status="done")
    assert di.status == "done"


def test_task_info_dataclass():
    ti = TaskInfo(task_id="t1", status="running", progress=0.5)
    assert ti.status == "running"
    assert ti.progress == 0.5


def test_subgraph_dataclass():
    sg = Subgraph(nodes=[{"id": 1}], edges=[{"source": 1, "target": 2}])
    assert len(sg.nodes) == 1
    assert len(sg.edges) == 1


def test_traversal_result_dataclass():
    tr = TraversalResult(path=[{"step": 1}], metadata={"depth": 3})
    assert len(tr.path) == 1


def test_data_source_config_defaults():
    cfg = DataSourceConfig(source_type="postgresql")
    assert cfg.host == "localhost"
    assert cfg.port == 5432
    assert cfg.schema_name == "public"


def test_data_source_config_to_dict():
    cfg = DataSourceConfig(source_type="mysql", host="db.host", port=3306, username="u", password="p")
    d = cfg.to_dict()
    assert d["source_type"] == "mysql"
    assert d["host"] == "db.host"
    assert d["port"] == 3306


def test_data_source_config_from_dict():
    d = {"source_type": "postgresql", "host": "10.0.0.1", "port": 5432, "database": "testdb"}
    cfg = DataSourceConfig.from_dict(d)
    assert cfg.source_type == "postgresql"
    assert cfg.host == "10.0.0.1"
    assert cfg.database == "testdb"


def test_data_source_config_extra_params():
    cfg = DataSourceConfig(source_type="hive", extra_params={"thrift.transport": "buffered"})
    assert cfg.extra_params["thrift.transport"] == "buffered"


def test_all_provider_abc_definitions():
    """Verify all provider ABCs have all abstract methods defined."""
    from app.providers.base import (
        LLMProvider,
        EmbeddingProvider,
        RAGProvider,
        DocumentEngineProvider,
        FileStorageProvider,
        GraphDBProvider,
        DataSourceProvider,
    )
    # Each ABC should have abstract methods
    for cls in [LLMProvider, EmbeddingProvider, RAGProvider, DocumentEngineProvider,
                FileStorageProvider, GraphDBProvider, DataSourceProvider]:
        abstract_methods = cls.__abstractmethods__
        assert len(abstract_methods) > 0


def test_provider_registry_has_required_keys():
    """Verify the provider registry has all required provider slots."""
    from app.providers.factory import _provider_registry
    # Original defaults
    assert "deepseek" in _provider_registry
    assert "builtin" in _provider_registry
    assert "local" in _provider_registry
    # New optional providers (task 25)
    assert "ollama" in _provider_registry
    assert "ollama_embedding" in _provider_registry
    assert "ragflow" in _provider_registry
    assert "opensearch" in _provider_registry
    assert "minio" in _provider_registry
    assert "neo4j" in _provider_registry


def test_new_providers_satisfy_abcs():
    """Verify all new (task 25) providers satisfy their ABC interfaces."""
    from app.providers.factory import _provider_registry
    from app.providers.base import (
        LLMProvider, EmbeddingProvider, RAGProvider,
        DocumentEngineProvider, FileStorageProvider, GraphDBProvider,
    )

    expected = {
        "ollama": LLMProvider,
        "ollama_embedding": EmbeddingProvider,
        "ragflow": RAGProvider,
        "opensearch": DocumentEngineProvider,
        "minio": FileStorageProvider,
        "neo4j": GraphDBProvider,
    }

    for key, abc in expected.items():
        cls = _provider_registry[key]
        assert issubclass(cls, abc), f"{key} ({cls.__name__}) should be a {abc.__name__}"
        # Verify all abstract methods are implemented
        for method_name in abc.__abstractmethods__:
            assert hasattr(cls, method_name), f"{key} missing method {method_name}"
            method = getattr(cls, method_name)
            assert callable(method), f"{key}.{method_name} should be callable"
