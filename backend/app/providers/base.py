from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════════════
# Shared data types
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Message:
    role: str  # system | user | assistant
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str = ""
    usage: dict | None = None
    finish_reason: str = "stop"


@dataclass
class ModelInfo:
    id: str
    name: str = ""
    provider: str = ""


@dataclass
class Document:
    doc_id: str
    kb_id: str
    filename: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KbInfo:
    kb_id: str
    name: str
    config: dict = field(default_factory=dict)


@dataclass
class DocInfo:
    doc_id: str
    kb_id: str
    filename: str
    file_type: str = ""
    status: str = "pending"


@dataclass
class TaskInfo:
    task_id: str
    status: str  # pending | running | completed | failed
    progress: float = 0.0


@dataclass
class Subgraph:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraversalResult:
    path: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════
# Provider interfaces
# ═══════════════════════════════════════════════════════════════════


class LLMProvider(ABC):
    """大语言模型抽象接口"""

    @abstractmethod
    async def chat(self, messages: list[Message], **kwargs) -> ChatResponse: ...

    @abstractmethod
    async def chat_stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]: ...

    @abstractmethod
    def supports_function_calling(self) -> bool: ...

    @abstractmethod
    def list_models(self) -> list[ModelInfo]: ...


class EmbeddingProvider(ABC):
    """向量嵌入抽象接口"""

    @abstractmethod
    async def embed(self, texts: list[str], **kwargs) -> list[list[float]]: ...

    @abstractmethod
    def dimension(self) -> int: ...


class RAGProvider(ABC):
    """RAG 引擎抽象接口 — 文档解析、Chunk、知识库管理"""

    @abstractmethod
    async def create_knowledge_base(self, name: str, config: dict) -> KbInfo: ...

    @abstractmethod
    async def upload_document(self, kb_id: str, file: bytes, filename: str) -> DocInfo: ...

    @abstractmethod
    async def parse_document(self, kb_id: str, doc_id: str) -> TaskInfo: ...

    @abstractmethod
    async def list_chunks(self, kb_id: str, doc_id: str) -> list[Chunk]: ...

    @abstractmethod
    async def search(self, kb_id: str, query: str, top_k: int = 10) -> list[SearchResult]: ...

    @abstractmethod
    async def chat(self, kb_id: str, question: str, history: list | None = None, top_k: int = 5) -> ChatResponse: ...

    @abstractmethod
    async def chat_stream(self, kb_id: str, question: str, history: list | None = None, top_k: int = 5): ...


class DocumentEngineProvider(ABC):
    """文档检索引擎抽象接口 — 全文搜索 + 向量检索"""

    @abstractmethod
    async def index_document(self, doc: Document, chunks: list[Chunk]) -> None: ...

    @abstractmethod
    async def search_fts(self, query: str, top_n: int = 100) -> list[SearchResult]: ...

    @abstractmethod
    async def search_vector(self, embedding: list[float], top_n: int = 100) -> list[SearchResult]: ...

    @abstractmethod
    async def search_hybrid(self, query: str, embedding: list[float], top_n: int = 100, fts_weight: float = 0.3) -> list[SearchResult]: ...


class FileStorageProvider(ABC):
    """文件存储抽象接口"""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str | None = None) -> str: ...

    @abstractmethod
    async def download(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def get_presigned_url(self, key: str, expires: int = 3600) -> str: ...


class GraphDBProvider(ABC):
    """图数据库抽象接口"""

    @abstractmethod
    async def create_graph(self, graph_name: str) -> None: ...

    @abstractmethod
    async def add_node(self, graph_name: str, label: str, properties: dict) -> str: ...

    @abstractmethod
    async def add_edge(self, graph_name: str, source_id: str, target_id: str, edge_type: str, properties: dict | None = None) -> None: ...

    @abstractmethod
    async def get_neighbors(self, graph_name: str, node_id: str, depth: int = 1) -> Subgraph: ...

    @abstractmethod
    async def traverse(self, graph_name: str, start_node: str, **params) -> TraversalResult: ...


@dataclass
class DataSourceConfig:
    source_type: str  # postgresql | mysql | hive | hbase | lindorm
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    schema_name: str = "public"
    extra_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type, "host": self.host, "port": self.port,
            "database": self.database, "username": self.username, "password": self.password,
            "schema_name": self.schema_name, "extra_params": self.extra_params,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DataSourceConfig":
        return cls(
            source_type=d.get("source_type", "postgresql"), host=d.get("host", "localhost"),
            port=d.get("port", 5432), database=d.get("database", ""),
            username=d.get("username", ""), password=d.get("password", ""),
            schema_name=d.get("schema_name", "public"), extra_params=d.get("extra_params", {}),
        )


class DataSourceProvider(ABC):
    """外部数据源抽象接口 — PostgreSQL / MySQL / Hive / HBase / Lindorm"""

    @abstractmethod
    async def connect(self, config: DataSourceConfig) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def test_connection(self, config: DataSourceConfig) -> dict: ...

    @abstractmethod
    async def list_tables(self, schema: str | None = None) -> list[str]: ...

    @abstractmethod
    async def get_table_info(self, table: str) -> dict: ...

    @abstractmethod
    async def get_row_count(self, table: str) -> int: ...

    @abstractmethod
    async def get_primary_key(self, table: str) -> str | None: ...

    @abstractmethod
    async def fetch_data(
        self, table: str, columns: list[str] | None = None,
        where: str | None = None, limit: int = 1000, offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def upsert_data(
        self, table: str, rows: list[dict[str, Any]], primary_key: str,
    ) -> dict[str, int]: ...
