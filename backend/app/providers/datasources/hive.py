from __future__ import annotations

from typing import Any

from ...providers.base import DataSourceConfig, DataSourceProvider


class HiveDataSource(DataSourceProvider):
    """Hive 数据源适配器 — 基于 pyhive thrift 连接"""

    def __init__(self) -> None:
        self._conn: Any = None
        self._config: DataSourceConfig | None = None

    async def connect(self, config: DataSourceConfig) -> None:
        from pyhive import hive
        if self._conn is not None:
            await self.disconnect()
        self._config = config
        self._conn = hive.Connection(
            host=config.host, port=config.port, database=config.database,
            username=config.username or "hive",
            auth=config.extra_params.get("auth", "NONE"),
            configuration=config.extra_params.get("configuration"),
        )

    async def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._config = None

    async def test_connection(self, config: DataSourceConfig) -> dict:
        from pyhive import hive
        try:
            conn = hive.Connection(
                host=config.host, port=config.port, database=config.database,
                username=config.username or "hive",
                auth=config.extra_params.get("auth", "NONE"),
            )
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [r[0] for r in cursor.fetchall()]
            cursor.close()
            conn.close()
            return {"success": True, "version": "Hive", "table_count": len(tables), "tables": tables}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_tables(self, schema: str | None = None) -> list[str]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        result = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return result

    async def get_table_info(self, table: str) -> dict:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE {table}")
        rows = cursor.fetchall()
        cursor.close()
        columns = []
        for r in rows:
            columns.append({
                "name": r[0], "data_type": r[1] if len(r) > 1 else "string",
                "nullable": True, "is_primary": False,
                "default": None, "comment": r[2] if len(r) > 2 else "",
            })
        return {"table": table, "columns": columns, "primary_key": None}

    async def get_row_count(self, table: str) -> int:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else 0

    async def get_primary_key(self, table: str) -> str | None:
        return None

    async def fetch_data(
        self, table: str, columns: list[str] | None = None,
        where: str | None = None, limit: int = 1000, offset: int = 0,
    ) -> list[dict[str, Any]]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        cols = ", ".join(columns) if columns else "*"
        sql = f"SELECT {cols} FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
        cursor = conn.cursor()
        cursor.execute(sql)
        col_names = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        return [dict(zip(col_names, r)) for r in rows]

    async def upsert_data(
        self, table: str, rows: list[dict[str, Any]], primary_key: str,
    ) -> dict[str, int]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        cursor = conn.cursor()
        inserted = 0
        for row in rows:
            columns = list(row.keys())
            values = [str(row[c]) if row[c] is not None else "NULL" for c in columns]
            placeholders = ", ".join("NULL" if v == "NULL" else f"'{v}'" for v in values)
            col_names = ", ".join(columns)
            try:
                cursor.execute(f"INSERT INTO TABLE {table} ({col_names}) VALUES ({placeholders})")
                inserted += 1
            except Exception:
                # Hive doesn't support UPSERT natively; fall back to insert-only
                pass
        cursor.close()
        return {"inserted": inserted, "updated": 0}
