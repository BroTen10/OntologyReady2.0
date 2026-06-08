from __future__ import annotations

import os
from typing import Any

from ..config import settings
from .base import FileStorageProvider


class LocalFileStorage(FileStorageProvider):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or settings.get_provider_config()["file_storage"]["config"]
        self.root = cfg.get("root", settings.file_storage_root)
        os.makedirs(self.root, exist_ok=True)

    def _full_path(self, key: str) -> str:
        safe_key = os.path.normpath(key).lstrip(os.sep)
        return os.path.join(self.root, safe_key)

    async def upload(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._full_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    async def download(self, key: str) -> bytes:
        path = self._full_path(key)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {key}")
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        if os.path.isfile(path):
            os.remove(path)

    async def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        return f"file:///{self._full_path(key)}"
