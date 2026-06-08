from __future__ import annotations

from ...providers.base import DataSourceConfig, DataSourceProvider

from .postgresql import PostgreSQLDataSource
from .mysql import MySQLDataSource
from .hive import HiveDataSource
from .hbase import HBaseDataSource
from .lindorm import LindormDataSource


def get_datasource(source_type: str) -> DataSourceProvider:
    """Factory: return the right adapter for a source type string."""
    mapping: dict[str, type[DataSourceProvider]] = {
        "postgresql": PostgreSQLDataSource,
        "postgres": PostgreSQLDataSource,
        "mysql": MySQLDataSource,
        "hive": HiveDataSource,
        "hbase": HBaseDataSource,
        "lindorm": LindormDataSource,
    }
    cls = mapping.get(source_type.lower())
    if cls is None:
        raise ValueError(f"Unsupported data source type: {source_type}")
    return cls()


__all__ = [
    "DataSourceProvider", "DataSourceConfig",
    "PostgreSQLDataSource", "MySQLDataSource", "HiveDataSource",
    "HBaseDataSource", "LindormDataSource", "get_datasource",
]
