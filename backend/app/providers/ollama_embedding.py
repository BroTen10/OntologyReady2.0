from __future__ import annotations

from typing import Any

import httpx

from ..config import settings
from .base import EmbeddingProvider


class OllamaEmbedding(EmbeddingProvider):
    """Embedding provider backed by Ollama (local embedding models)."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or settings.get_provider_config().get("embedding", {}).get("config", {})
        self.base_url = cfg.get("api_base", "http://localhost:11434")
        self.default_model = cfg.get("default_model", "nomic-embed-text")
        self._dim = cfg.get("dimension", 768)

    async def embed(self, texts: list[str], **kwargs) -> list[list[float]]:
        model = kwargs.get("model", self.default_model)
        embeddings: list[list[float]] = []
        async with httpx.AsyncClient(timeout=60) as client:
            for text in texts:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings.append(data["embedding"])
        return embeddings

    def dimension(self) -> int:
        return self._dim
