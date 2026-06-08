from __future__ import annotations

from typing import Any

from ...providers.base import DataSourceConfig, DataSourceProvider


class HBaseDataSource(DataSourceProvider):
    """HBase 数据源适配器 — 基于 happybase (Thrift)"""

    def __init__(self) -> None:
        self._conn: Any = None
        self._config: DataSourceConfig | None = None

    async def connect(self, config: DataSourceConfig) -> None:
        import happybase
        if self._conn is not None:
            await self.disconnect()
        self._config = config
        self._conn = happybase.Connection(
            host=config.host, port=config.port,
            compat=config.extra_params.get("compat", "0.98"),
            table_prefix=config.extra_params.get("table_prefix", ""),
        )

    async def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._config = None

    async def test_connection(self, config: DataSourceConfig) -> dict:
        import happybase
        try:
            conn = happybase.Connection(
                host=config.host, port=config.port,
                compat=config.extra_params.get("compat", "0.98"),
            )
            tables = conn.tables()
            conn.close()
            return {"success": True, "version": "HBase", "table_count": len(tables), "tables": tables}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_tables(self, schema: str | None = None) -> list[str]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        return [t.decode() if isinstance(t, bytes) else t for t in conn.tables()]

    async def get_table_info(self, table: str) -> dict:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        t = conn.table(table)
        families = t.families()
        columns = []
        for name, fam in (families or {}).items():
            n = name.decode() if isinstance(name, bytes) else name
            columns.append({
                "name": n, "data_type": "binary",
                "nullable": True, "is_primary": False,
                "default": None, "comment": "",
            })
        columns.insert(0, {
            "name": "row_key", "data_type": "string",
            "nullable": False, "is_primary": True,
            "default": None, "comment": "HBase row key",
        })
        return {"table": table, "columns": columns, "primary_key": "row_key"}

    async def get_row_count(self, table: str) -> int:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        t = conn.table(table)
        count = 0
        for _ in t.scan(limit=10000):
            count += 1
        return count

    async def get_primary_key(self, table: str) -> str | None:
        return "row_key"

    async def fetch_data(
        self, table: str, columns: list[str] | None = None,
        where: str | None = None, limit: int = 1000, offset: int = 0,
    ) -> list[dict[str, Any]]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        t = conn.table(table)
        col_list = [c.encode() if isinstance(c, str) else c for c in columns] if columns else None
        result = []
        skipped = 0
        for row_key, data in t.scan(columns=col_list, limit=limit + offset):
            if skipped < offset:
                skipped += 1
                continue
            rk = row_key.decode() if isinstance(row_key, bytes) else row_key
            row = {"row_key": rk}
            for col, val in (data or {}).items():
                name = col.decode() if isinstance(col, bytes) else col
                val_str = val.decode(errors="replace") if isinstance(val, bytes) else str(val)
                row[name] = val_str.split(":")[-1] if ":" in name else val_str
            result.append(row)
            if len(result) >= limit:
                break
        return result

    async def upsert_data(
        self, table: str, rows: list[dict[str, Any]], primary_key: str,
    ) -> dict[str, int]:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Not connected")
        t = conn.table(table)
        inserted = 0
        with t.batch() as b:
            for row in rows:
                rk = row.pop(primary_key, None)
                if rk is None:
                    continue
                data = {}
                for k, v in row.items():
                    cf, _, qual = k.partition(":")
                    col = f"{cf}:{qual}" if qual else k
                    data[col.encode()] = str(v).encode() if not isinstance(v, bytes) else v
                if data:
                    b.put(str(rk).encode(), data)
                    inserted += 1
        return {"inserted": inserted, "updated": 0}
