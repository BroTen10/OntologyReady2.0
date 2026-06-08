from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..config import settings
from .base import ChatResponse, LLMProvider, Message, ModelInfo


class OllamaLLM(LLMProvider):
    """LLM provider backed by Ollama (local LLM server)."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or settings.get_provider_config().get("llm", {}).get("config", {})
        self.base_url = cfg.get("api_base", "http://localhost:11434")
        self.default_model = cfg.get("default_model", "llama3.2")
        self.default_params = cfg.get("default_params", {"temperature": 0.1})

    async def chat(self, messages: list[Message], **kwargs) -> ChatResponse:
        model = kwargs.get("model", self.default_model)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "stream": False,
                    "options": {k: v for k, v in self.default_params.items()},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return ChatResponse(
                content=data["message"]["content"],
                model=model,
                usage=None,
                finish_reason="stop",
            )

    async def chat_stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        model = kwargs.get("model", self.default_model)
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "stream": True,
                    "options": {k: v for k, v in self.default_params.items()},
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]

    def supports_function_calling(self) -> bool:
        return False

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="llama3.2", name="Llama 3.2", provider="ollama"),
            ModelInfo(id="qwen2.5", name="Qwen 2.5", provider="ollama"),
            ModelInfo(id="mistral", name="Mistral", provider="ollama"),
        ]
