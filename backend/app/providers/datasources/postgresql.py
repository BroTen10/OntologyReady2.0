from __future__ import annotations

from typing import Any

import asyncpg

from ...providers.base import DataSourceConfig, DataSourceProvider


class PostgreSQLDataSource(DataSourceProvider):
    """PostgreSQL 数据源适配器 — 基于 asyncpg"""

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._config: DataSourceConfig | None = None

    def _dsn(self, config: DataSourceConfig) -> str:
        return (
            f"postgresql://{config.username}:{config.password}"
            f"@{config.host}:{config.port}/{config.database}"
        )

    async def connect(self, config: DataSourceConfig) -> None:
        if self._conn is not None:
            await self.disconnect()
        self._config = config
        self._conn = await asyncpg.connect(dsn=self._dsn(config), timeout=10)

    async def disconnect(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            self._config = None

    async def test_connection(self, config: DataSourceConfig) -> dict:
        try:
            conn = await asyncpg.connect(dsn=self._dsn(config), timeout=10)
            version = await conn.fetchval("SELECT version()")
            tables = await self.list_tables_with_conn(conn, config.schema_name)
            await conn.close()
            return {"success": True, "version": version, "table_count": len(tables), "tables": tables}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_tables_with_conn(self, conn: asyncpg.Connection, schema: str) -> list[str]:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = $1 ORDER BY table_name",
            schema,
        )
        return [r["table_name"] for r in rows]

    async def list_tables(self, schema: str | None = None) -> list[str]:
        schema = schema or (self._config.schema_name if self._config else "public")
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        return await self.list_tables_with_conn(conn, schema)

    async def get_table_info(self, table: str) -> dict:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        schema = self._config.schema_name if self._config else "public"
        cols = await conn.fetch(
            """SELECT column_name, data_type, is_nullable, column_default,
                      col_description(
                          (SELECT oid FROM pg_class WHERE relname = $1), ordinal_position
                      ) as comment
               FROM information_schema.columns
               WHERE table_schema = $2 AND table_name = $1 ORDER BY ordinal_position""",
            table, schema,
        )
        pk = await conn.fetchrow(
            """SELECT kcu.column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
               WHERE tc.table_schema = $2 AND tc.table_name = $1 AND tc.constraint_type = 'PRIMARY KEY'
               LIMIT 1""",
            table, schema,
        )
        pk_col = pk["column_name"] if pk else None
        column_list = []
        for c in cols:
            column_list.append({
                "name": c["column_name"], "data_type": c["data_type"],
                "nullable": c["is_nullable"] == "YES",
                "is_primary": c["column_name"] == pk_col,
                "default": str(c["column_default"]) if c.get("column_default") else None,
                "comment": c.get("comment") or "",
            })
        return {"table": table, "schema": schema, "columns": column_list, "primary_key": pk_col}

    async def get_row_count(self, table: str) -> int:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        schema = self._config.schema_name if self._config else "public"
        return await conn.fetchval(f'SELECT COUNT(*) FROM "{schema}"."{table}"')

    async def get_primary_key(self, table: str) -> str | None:
        info = await self.get_table_info(table)
        return info.get("primary_key")

    async def fetch_data(
        self, table: str, columns: list[str] | None = None,
        where: str | None = None, limit: int = 1000, offset: int = 0,
    ) -> list[dict[str, Any]]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        schema = self._config.schema_name if self._config else "public"
        cols = ", ".join(f'"{c}"' for c in columns) if columns else "*"
        sql = f'SELECT {cols} FROM "{schema}"."{table}"'
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {limit} OFFSET {offset}"
        rows = await conn.fetch(sql)
        return [dict(r) for r in rows]

    async def upsert_data(
        self, table: str, rows: list[dict[str, Any]], primary_key: str,
    ) -> dict[str, int]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        schema = self._config.schema_name if self._config else "public"
        if not rows:
            return {"inserted": 0, "updated": 0}
        columns = list(rows[0].keys())
        placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
        col_names = ", ".join(f'"{c}"' for c in columns)
        set_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in columns if c != primary_key)
        sql = (
            f'INSERT INTO "{schema}"."{table}" ({col_names}) VALUES ({placeholders})'
            f" ON CONFLICT (\"{primary_key}\") DO UPDATE SET {set_clause}"
        )
        inserted, updated = 0, 0
        for row in rows:
            values = [row[c] for c in columns]
            result = await conn.execute(sql, *values)
            tag = result.split()[-1] if result else "0"
            if tag == "0":
                pass
            else:
                count = int(tag)
                inserted += count
        return {"inserted": inserted, "updated": updated}
