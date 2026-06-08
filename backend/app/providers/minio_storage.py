from __future__ import annotations

import io
from typing import Any

import httpx

from .base import FileStorageProvider


class MinIOFileStorage(FileStorageProvider):
    """File storage backed by MinIO (S3-compatible) via HTTP API."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg: dict[str, Any] = config or {}
        self.endpoint = cfg.get("endpoint", "http://localhost:9000")
        self.access_key = cfg.get("access_key", "minioadmin")
        self.secret_key = cfg.get("secret_key", "minioadmin")
        self.bucket = cfg.get("bucket", "ontology-files")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.endpoint,
                timeout=30,
            )
        return self._client

    def _sign_headers(self, method: str, key: str) -> dict[str, str]:
        # MinIO / S3 compatible signing — use presigned-style for simple cases
        return {
            "x-amz-access-key": self.access_key,
            "x-amz-secret-key": self.secret_key,
        }

    async def _ensure_bucket(self) -> None:
        client = await self._get_client()
        resp = await client.head(f"/{self.bucket}")
        if resp.status_code == 404:
            resp = await client.put(
                f"/{self.bucket}",
                headers=self._sign_headers("PUT", ""),
            )
            resp.raise_for_status()

    async def upload(self, key: str, data: bytes, content_type: str | None = None) -> str:
        await self._ensure_bucket()
        client = await self._get_client()
        headers = self._sign_headers("PUT", key)
        if content_type:
            headers["Content-Type"] = content_type
        resp = await client.put(
            f"/{self.bucket}/{key}",
            content=data,
            headers=headers,
        )
        resp.raise_for_status()
        return f"{self.endpoint}/{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        client = await self._get_client()
        resp = await client.get(
            f"/{self.bucket}/{key}",
            headers=self._sign_headers("GET", key),
        )
        resp.raise_for_status()
        return resp.content

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        resp = await client.delete(
            f"/{self.bucket}/{key}",
            headers=self._sign_headers("DELETE", key),
        )
        resp.raise_for_status()

    async def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        return f"{self.endpoint}/{self.bucket}/{key}?X-Amz-Expires={expires}"
