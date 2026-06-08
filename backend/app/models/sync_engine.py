from __future__ import annotations

import asyncio
from typing import Any

from ..models import instance_store as istore
from ..models import ontology_store as ostore
from ..models import sync_store as sstore
from ..providers.datasources import get_datasource
from ..providers.base import DataSourceConfig

BATCH_SIZE_DEFAULT = 1000
LARGE_TABLE_THRESHOLD = 50_000


async def run_sync_task(task_id: str) -> None:
    """执行数据同步任务。大表自动转异步，小表同步执行。"""
    task = await sstore.get_sync_task(task_id)
    if not task:
        return

    dataset_id = task["dataset_id"]
    config = DataSourceConfig.from_dict(task["config"])
    mappings: list[dict] = task["mappings"]

    try:
        await sstore.update_sync_task_status(task_id, "running")
        await sstore.add_sync_log(task_id, "info", f"开始同步任务，数据源: {config.source_type}，映射表数: {len(mappings)}")

        adapter = get_datasource(config.source_type)
        test = await adapter.test_connection(config)
        if not test.get("success"):
            raise RuntimeError(f"数据源连接失败: {test.get('error')}")

        await adapter.connect(config)

        total_synced = 0
        total_count = 0

        for mapping in mappings:
            table = mapping["source_table"]
            obj_type = mapping["target_object_type"]
            id_col = mapping.get("id_column", "id")
            filter_cond = mapping.get("filter_condition")

            # Get row count to decide sync strategy
            try:
                row_count = await adapter.get_row_count(table)
            except Exception:
                row_count = 0

            total_count += row_count
            await sstore.update_sync_task_status(task_id, "running", total_rows=total_count)
            await sstore.add_sync_log(task_id, "info", f"表 {table} → {obj_type}，行数: {row_count}", table=table)

            # Fetch data in batches
            offset = 0
            batch_num = 0
            while True:
                rows = await adapter.fetch_data(table, limit=BATCH_SIZE_DEFAULT, offset=offset)
                if not rows:
                    break

                # Convert source rows to ontology instances
                objects, links = _transform_rows(dataset_id, obj_type, rows, mapping)

                # Write objects (UPSERT by object_id using the id_col)
                for obj in objects:
                    obj_id = obj.get("object_id")
                    if obj_id:
                        await istore.create_object(dataset_id, obj)

                # Write links
                for link in links:
                    await istore.create_link(dataset_id, link)

                offset += len(rows)
                batch_num += 1
                total_synced += len(objects)

                progress = (total_synced / max(total_count, 1)) * 100
                await sstore.update_sync_task_status(
                    task_id, "running", progress=min(progress, 99.9),
                    synced_rows=total_synced,
                )
                await sstore.add_sync_log(
                    task_id, "info",
                    f"表 {table} 批次 {batch_num}: 同步 {len(objects)} 条对象",
                    table=table, rows=len(objects),
                )

                # Yield control for responsiveness
                await asyncio.sleep(0)

        await adapter.disconnect()

        await sstore.update_sync_task_status(task_id, "completed", progress=100.0, synced_rows=total_synced)
        await sstore.add_sync_log(task_id, "info", f"同步完成: {total_synced} 条记录")

    except Exception as e:
        await sstore.add_sync_log(task_id, "error", str(e))
        await sstore.update_sync_task_status(task_id, "failed", error_msg=str(e))
        try:
            adapter = get_datasource(config.source_type)
            await adapter.disconnect()
        except Exception:
            pass


def _transform_rows(
    dataset_id: str, object_type: str, rows: list[dict[str, Any]], mapping: dict,
) -> tuple[list[dict], list[dict]]:
    """将源表行转换为本体 Objects 和 Links"""
    col_map = mapping.get("column_mapping", {}) or {}
    id_col = mapping.get("id_column", "id")
    objects = []
    links = []

    for row in rows:
        properties = {}
        for src_col, val in row.items():
            target_prop = col_map.get(src_col, src_col)
            # Convert non-JSON-safe values
            if isinstance(val, bytes):
                val = val.decode(errors="replace")
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            elif val is None:
                val = None
            properties[target_prop] = val

        obj_id_val = row.get(id_col)
        object_id = f"{object_type}_{obj_id_val}" if obj_id_val is not None else f"{object_type}_{len(objects)}"

        objects.append({
            "object_type": object_type,
            "object_id": str(object_id),
            "properties": properties,
        })

    return objects, links


async def cancel_sync_task(task_id: str) -> bool:
    """取消同步任务"""
    task = await sstore.get_sync_task(task_id)
    if not task or task["status"] not in ("pending", "running"):
        return False
    await sstore.update_sync_task_status(task_id, "cancelled")
    await sstore.add_sync_log(task_id, "info", "任务已取消")
    return True
