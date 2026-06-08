from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..config import settings
from .base import ChatResponse, LLMProvider, Message, ModelInfo


class DeepSeekProvider(LLMProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or settings.get_provider_config()["llm"]["config"]
        self.api_base = cfg.get("api_base", "https://api.deepseek.com/v1")
        self.api_key = cfg.get("api_key", "")
        self.default_model = cfg.get("default_model", "deepseek-chat")
        self.default_params = cfg.get("default_params", {"temperature": 0.1, "max_tokens": 4096})

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _build_payload(self, messages: list[Message], **kwargs) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.default_model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            **self.default_params,
            **{k: v for k, v in kwargs.items() if k not in ("model",)},
        }
        return payload

    async def chat(self, messages: list[Message], **kwargs) -> ChatResponse:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=self._build_payload(messages, **kwargs),
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return ChatResponse(
                content=choice["message"]["content"],
                model=data.get("model", self.default_model),
                usage=data.get("usage"),
                finish_reason=choice.get("finish_reason", "stop"),
            )

    async def chat_stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        payload = self._build_payload(messages, **kwargs)
        payload["stream"] = True
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        import json
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    def supports_function_calling(self) -> bool:
        return True

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat", provider="deepseek"),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner", provider="deepseek"),
        ]
