from __future__ import annotations

from unittest.mock import patch

from app.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.app_name == "OntologyReady 2.0"
    assert s.access_token_expire_minutes == 15
    assert s.refresh_token_expire_days == 7
    assert s.database_max_connections == 20


def test_get_provider_config_defaults():
    s = Settings()
    cfg = s.get_provider_config()
    assert "llm" in cfg
    assert "embedding" in cfg
    assert "rag" in cfg
    assert "document_engine" in cfg
    assert "file_storage" in cfg
    assert "graph_db" in cfg
    assert cfg["llm"]["provider"] == "deepseek"
    assert cfg["rag"]["provider"] == "builtin"
    assert cfg["document_engine"]["provider"] == "postgres"


def test_get_provider_config_from_file():
    s = Settings(provider_config="config/providers.json")
    cfg = s.get_provider_config()
    assert isinstance(cfg, dict)
    assert "llm" in cfg
