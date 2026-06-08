# Provider Extension Guide

## Overview

The platform uses a **Provider pattern** to decouple infrastructure choices from business logic. Each of the 6 provider types defines an abstract interface in `backend/app/providers/base.py`. Concrete implementations are registered in `backend/app/providers/factory.py` and selected via `config/providers.json`.

### The 6 Provider Interfaces

| Interface | Purpose | Default Implementation |
|-----------|---------|----------------------|
| `LLMProvider` | Large language model chat/completion | `DeepSeekProvider` |
| `EmbeddingProvider` | Text-to-vector embedding | `DeepSeekEmbedding` |
| `RAGProvider` | Document parsing, chunking, retrieval, QA | `BuiltinRAGProvider` |
| `DocumentEngineProvider` | Full-text + vector search engine | `PostgresDocumentEngine` |
| `FileStorageProvider` | File/blob storage | `LocalFileStorage` |
| `GraphDBProvider` | Graph database operations | `AGEGraphDB` |

### Provider Configuration

Providers are configured in `backend/config/providers.json`:

```json
{
  "llm": {
    "provider": "deepseek",
    "config": {
      "api_base": "https://api.deepseek.com/v1",
      "api_key": "${env:DEEPSEEK_API_KEY}",
      "default_model": "deepseek-chat",
      "default_params": { "temperature": 0.1, "max_tokens": 4096 }
    }
  },
  "embedding": {
    "provider": "deepseek_embedding",
    "config": {
      "api_base": "https://api.deepseek.com/v1",
      "api_key": "${env:DEEPSEEK_API_KEY}",
      "dimension": 1536
    }
  },
  "rag": { "provider": "builtin", "config": {} },
  "document_engine": { "provider": "postgres", "config": {} },
  "file_storage": { "provider": "local", "config": { "root": "/data/files" } },
  "graph_db": { "provider": "age", "config": {} }
}
```

---

## How to Implement a New Provider

### Step 1: Understand the Abstract Interface

Each interface is defined in `backend/app/providers/base.py`. Open it and read the abstract methods you need to implement.

### Step 2: Create Your Implementation File

Create a new file in `backend/app/providers/` (e.g., `my_llm.py`).

### Step 3: Implement the Interface

```python
# backend/app/providers/my_llm.py
from __future__ import annotations
from collections.abc import AsyncIterator
from typing import Any
from .base import ChatResponse, LLMProvider, Message, ModelInfo

class MyLLMProvider(LLMProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self.api_base = cfg.get("api_base", "https://api.example.com/v1")
        self.api_key = cfg.get("api_key", "")
        self.default_model = cfg.get("default_model", "my-model")

    async def chat(self, messages: list[Message], **kwargs) -> ChatResponse:
        # Your implementation here
        ...

    async def chat_stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        # Your implementation here
        ...

    def supports_function_calling(self) -> bool:
        return True  # or False

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id="my-model", name="My Model", provider="my_llm")]
```

### Step 4: Register in Factory

In `backend/app/providers/factory.py`:

```python
from .my_llm import MyLLMProvider

_provider_registry: dict[str, type] = {
    # ... existing entries ...
    "my_llm": MyLLMProvider,  # Add this line
}
```

### Step 5: Configure

Update `backend/config/providers.json` to use your provider:

```json
{
  "llm": {
    "provider": "my_llm",
    "config": {
      "api_base": "https://api.example.com/v1",
      "api_key": "${env:MY_API_KEY}",
      "default_model": "my-model"
    }
  }
}
```

The `${env:VAR_NAME}` syntax reads from environment variables at runtime.

### Step 6: Test

Restart the backend. The new provider takes effect immediately.

---

## Interface-Specific Extension Guides

### 1. LLMProvider — Add a New LLM Backend

**Abstract methods to implement:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `chat(messages, **kwargs)` | `ChatResponse` | Non-streaming completion |
| `chat_stream(messages, **kwargs)` | `AsyncIterator[str]` | Streaming completion |
| `supports_function_calling()` | `bool` | Whether model supports tool use |
| `list_models()` | `list[ModelInfo]` | Available model list |

**Example: Ollama Provider**

```python
class OllamaProvider(LLMProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self.base_url = cfg.get("base_url", "http://localhost:11434")
        self.default_model = cfg.get("default_model", "llama3")

    async def chat(self, messages: list[Message], **kwargs) -> ChatResponse:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": kwargs.get("model", self.default_model),
                       "messages": [{"role": m.role, "content": m.content} for m in messages],
                       "stream": False},
                timeout=120,
            )
            data = resp.json()
            return ChatResponse(content=data["message"]["content"], model=data["model"])

    async def chat_stream(self, messages, **kwargs):
        # Implement SSE streaming from Ollama
        ...

    def supports_function_calling(self) -> bool:
        return False  # Ollama supports this for some models

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id="llama3", name="Llama 3", provider="ollama")]
```

### 2. EmbeddingProvider — Add a New Embedding Backend

**Abstract methods to implement:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `embed(texts, **kwargs)` | `list[list[float]]` | Vectorize text batch |
| `dimension()` | `int` | Embedding vector dimension |

**The `dimension()` return value must match the actual output.** The document engine uses this to create the vector column (`vector(N)`).

### 3. RAGProvider — Replace the RAG Engine

**This is the most complex provider.** It orchestrates DocumentEngine + Embedding + LLM.

**Abstract methods to implement:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `create_knowledge_base(name, config)` | `KbInfo` | Create KB |
| `upload_document(kb_id, file, filename)` | `DocInfo` | Upload document |
| `parse_document(kb_id, doc_id)` | `TaskInfo` | Parse & chunk document |
| `list_chunks(kb_id, doc_id)` | `list[Chunk]` | List document chunks |
| `search(kb_id, query, top_k)` | `list[SearchResult]` | Search KB |
| `chat(kb_id, question, history, top_k)` | `ChatResponse` | QA with context |
| `chat_stream(kb_id, question, history, top_k)` | `AsyncIterator` | Streaming QA |

### 4. DocumentEngineProvider — Add a Search Engine Backend

**Abstract methods to implement:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `index_document(doc, chunks)` | `None` | Index chunks for search |
| `search_fts(query, top_n)` | `list[SearchResult]` | Full-text search |
| `search_vector(embedding, top_n)` | `list[SearchResult]` | Vector similarity search |
| `search_hybrid(query, embedding, top_n, fts_weight)` | `list[SearchResult]` | Combined search |

**Example: OpenSearch Provider**

```python
class OpenSearchDocumentEngine(DocumentEngineProvider):
    def __init__(self, config):
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 9200)
        self.client = None  # Lazy init OpenSearch client

    async def index_document(self, doc, chunks):
        # Index chunks into OpenSearch with vector fields
        ...

    async def search_fts(self, query, top_n):
        # Use OpenSearch match query
        ...

    async def search_vector(self, embedding, top_n):
        # Use OpenSearch k-NN query
        ...
```

### 5. FileStorageProvider — Add a New Storage Backend

**Abstract methods to implement:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `upload(key, data, content_type)` | `str` | Store file, return path |
| `download(key)` | `bytes` | Retrieve file content |
| `delete(key)` | `None` | Remove file |
| `get_presigned_url(key, expires)` | `str` | Temporary access URL |

**Example: MinIO/S3 Provider**

```python
class MinIOFileStorage(FileStorageProvider):
    def __init__(self, config):
        self.endpoint = config.get("endpoint", "localhost:9000")
        self.access_key = config.get("access_key", "")
        self.secret_key = config.get("secret_key", "")
        self.bucket = config.get("bucket", "ontology")

    async def upload(self, key, data, content_type=None):
        # Use aioboto3 to upload to S3
        ...

    async def download(self, key):
        # Use aioboto3 to download from S3
        ...

    async def delete(self, key):
        # Use aioboto3 to delete from S3
        ...

    async def get_presigned_url(self, key, expires=3600):
        # Generate S3 presigned URL
        ...
```

### 6. GraphDBProvider — Add a Graph Database Backend

**Abstract methods to implement:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `create_graph(graph_name)` | `None` | Initialize graph space |
| `add_node(graph_name, label, properties)` | `str` | Create node, return ID |
| `add_edge(graph_name, src, tgt, type, props)` | `None` | Create relationship |
| `get_neighbors(graph_name, node_id, depth)` | `Subgraph` | Expand neighbors |
| `traverse(graph_name, start_node, **params)` | `TraversalResult` | Path traversal |

**Example: Neo4j Provider**

```python
class Neo4jGraphDB(GraphDBProvider):
    def __init__(self, config):
        self.uri = config.get("uri", "bolt://localhost:7687")
        self.user = config.get("user", "neo4j")
        self.password = config.get("password", "")
        self.driver = None  # Lazy init Neo4j driver

    async def create_graph(self, graph_name):
        # In Neo4j, "graphs" are database names
        ...

    async def add_node(self, graph_name, label, properties):
        # MERGE (n:{label} {properties}) RETURN id(n)
        ...

    async def get_neighbors(self, graph_name, node_id, depth):
        # MATCH (n)-[*1..{depth}]-(m) WHERE id(n) = node_id RETURN n, r, m
        ...
```

---

## Design Principles

1. **Constructor takes `config: dict | None`** — Always accept optional config, fall back to system settings.
2. **All I/O is async** — Use `httpx.AsyncClient` for HTTP, `asyncpg` for PostgreSQL.
3. **Lazy initialization** — Create connections/pools on first use, not in `__init__`.
4. **Stateless helpers** — Factories like `factory.py` cache singleton instances.
5. **Config priority** — Environment variables (`${env:VAR}`) > `.env` file > `providers.json` > code defaults.

## Validation Test

After implementing a new provider, run the provider swap test:

```bash
cd backend
pytest tests/test_providers.py -v -k "test_provider_swap"
```

This verifies that your new implementation satisfies the interface contract.
