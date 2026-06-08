from __future__ import annotations

from typing import Any

import httpx

from ..config import settings
from .base import EmbeddingProvider


class DeepSeekEmbedding(EmbeddingProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or settings.get_provider_config()["embedding"]["config"]
        self.api_base = cfg.get("api_base", "https://api.deepseek.com/v1")
        self.api_key = cfg.get("api_key", "")
        self._dim = cfg.get("dimension", 1536)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def embed(self, texts: list[str], **kwargs) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.api_base}/embeddings",
                headers=self._headers(),
                json={"input": texts, "model": kwargs.get("model", "deepseek-chat")},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]

    def dimension(self) -> int:
        return self._dim
