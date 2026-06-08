from __future__ import annotations

from typing import Any

from ..config import settings
from .base import (
    DocumentEngineProvider,
    EmbeddingProvider,
    FileStorageProvider,
    GraphDBProvider,
    LLMProvider,
    RAGProvider,
)
from .document_engine import PostgresDocumentEngine
from .embedding import DeepSeekEmbedding
from .file_storage import LocalFileStorage
from .graph_db import AGEGraphDB
from .llm import DeepSeekProvider
from .minio_storage import MinIOFileStorage
from .neo4j import Neo4jGraphDB
from .ollama_embedding import OllamaEmbedding
from .ollama_llm import OllamaLLM
from .opensearch import OpenSearchDocumentEngine
from .rag import BuiltinRAGProvider
from .ragflow import RAGFlowProvider

_provider_registry: dict[str, type] = {
    # LLM
    "deepseek": DeepSeekProvider,
    "ollama": OllamaLLM,
    # Embedding
    "deepseek_embedding": DeepSeekEmbedding,
    "ollama_embedding": OllamaEmbedding,
    # RAG
    "builtin": BuiltinRAGProvider,
    "ragflow": RAGFlowProvider,
    # Document Engine
    "postgres": PostgresDocumentEngine,
    "opensearch": OpenSearchDocumentEngine,
    # File Storage
    "local": LocalFileStorage,
    "minio": MinIOFileStorage,
    # Graph DB
    "age": AGEGraphDB,
    "neo4j": Neo4jGraphDB,
}

_instances: dict[str, Any] = {}


def get_llm() -> LLMProvider:
    return _get_or_create("llm", "deepseek")


def get_embedding() -> EmbeddingProvider:
    return _get_or_create("embedding", "deepseek_embedding")


def get_rag() -> RAGProvider:
    return _get_or_create("rag", "builtin")


def get_document_engine() -> DocumentEngineProvider:
    return _get_or_create("document_engine", "postgres")


def get_file_storage() -> FileStorageProvider:
    return _get_or_create("file_storage", "local")


def get_graph_db() -> GraphDBProvider:
    return _get_or_create("graph_db", "age")


def _get_or_create(provider_type: str, default_key: str) -> Any:
    if provider_type in _instances:
        return _instances[provider_type]
    provider_cfg = settings.get_provider_config().get(provider_type, {})
    key = provider_cfg.get("provider", default_key)
    cls = _provider_registry.get(key)
    if cls is None:
        raise ValueError(f"Unknown provider '{key}' for type '{provider_type}'")
    instance = cls(provider_cfg.get("config"))
    _instances[provider_type] = instance
    return instance


def register_provider(key: str, cls: type) -> None:
    _provider_registry[key] = cls
