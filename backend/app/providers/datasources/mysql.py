from __future__ import annotations

from typing import Any

from ...providers.base import DataSourceConfig, DataSourceProvider


class MySQLDataSource(DataSourceProvider):
    """MySQL 数据源适配器 — 基于 aiomysql"""

    def __init__(self) -> None:
        self._conn: Any = None
        self._config: DataSourceConfig | None = None

    async def connect(self, config: DataSourceConfig) -> None:
        import aiomysql
        if self._conn is not None:
            await self.disconnect()
        self._config = config
        self._conn = await aiomysql.connect(
            host=config.host, port=config.port, user=config.username,
            password=config.password, db=config.database,
            connect_timeout=10,
        )

    async def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._config = None

    async def test_connection(self, config: DataSourceConfig) -> dict:
        import aiomysql
        try:
            conn = await aiomysql.connect(
                host=config.host, port=config.port, user=config.username,
                password=config.password, db=config.database,
                connect_timeout=10,
            )
            async with conn.cursor() as cur:
                await cur.execute("SELECT VERSION()")
                version = await cur.fetchone()
                await cur.execute(
                    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
                    (config.database,),
                )
                tables = [r[0] for r in await cur.fetchall()]
            conn.close()
            return {"success": True, "version": version[0] if version else "", "table_count": len(tables), "tables": tables}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_tables(self, schema: str | None = None) -> list[str]:
        conn, config = self._conn, self._config
        if conn is None or config is None:
            raise RuntimeError("Not connected")
        async with conn.cursor() as cur:
            db = config.database
            await cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
                (db,),
            )
            return [r[0] for r in await cur.fetchall()]

    async def get_table_info(self, table: str) -> dict:
        conn, config = self._conn, self._config
        if conn is None or config is None:
            raise RuntimeError("Not connected")
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT, COLUMN_KEY
                   FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION""",
                (config.database, table),
            )
            cols = await cur.fetchall()
            columns = []
            pk_col = None
            for c in cols:
                is_pk = c[5] == "PRI"
                columns.append({
                    "name": c[0], "data_type": c[1], "nullable": c[2] == "YES",
                    "is_primary": is_pk,
                    "default": str(c[3]) if c[3] is not None else None,
                    "comment": c[4] or "",
                })
                if is_pk:
                    pk_col = c[0]
        return {"table": table, "schema": config.database, "columns": columns, "primary_key": pk_col}

    async def get_row_count(self, table: str) -> int:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            result = await cur.fetchone()
            return result[0] if result else 0

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
        cols = ", ".join(f"`{c}`" for c in columns) if columns else "*"
        sql = f"SELECT {cols} FROM `{table}`"
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {limit} OFFSET {offset}"
        async with conn.cursor() as cur:
            await cur.execute(sql)
            col_names = [d[0] for d in cur.description]
            rows = await cur.fetchall()
            return [dict(zip(col_names, r)) for r in rows]

    async def upsert_data(
        self, table: str, rows: list[dict[str, Any]], primary_key: str,
    ) -> dict[str, int]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        if not rows:
            return {"inserted": 0, "updated": 0}
        columns = list(rows[0].keys())
        col_names = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        set_clause = ", ".join(f"`{c}` = VALUES(`{c}`)" for c in columns if c != primary_key)
        sql = (
            f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"
            f" ON DUPLICATE KEY UPDATE {set_clause}"
        )
        inserted = 0
        async with conn.cursor() as cur:
            for row in rows:
                values = [row[c] for c in columns]
                await cur.execute(sql, values)
                inserted += cur.rowcount
        return {"inserted": inserted, "updated": 0}
