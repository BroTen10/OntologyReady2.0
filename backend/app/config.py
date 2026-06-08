from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings


def _load_json_config(path: str) -> dict[str, Any]:
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    app_name: str = "Ontology Knowledge Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ── Database ─────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ontology"
    database_max_connections: int = 20

    # ── File Storage ─────────────────────────────────────
    file_storage_root: str = "/data/files"

    # ── Provider Config (JSON blob or loaded from file) ───
    provider_config: str = "config/providers.json"

    # ── CORS ─────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_provider_config(self) -> dict[str, Any]:
        cfg = _load_json_config(self.provider_config)
        cfg.setdefault("llm", {"provider": "deepseek", "config": {}})
        cfg.setdefault("embedding", {"provider": "deepseek", "config": {}})
        cfg.setdefault("rag", {"provider": "builtin", "config": {}})
        cfg.setdefault("document_engine", {"provider": "postgres", "config": {}})
        cfg.setdefault("file_storage", {"provider": "local", "config": {}})
        cfg.setdefault("graph_db", {"provider": "age", "config": {}})
        return cfg


settings = Settings()
