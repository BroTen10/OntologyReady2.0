from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import asyncpg

from ..config import settings
from . import ontology_store as ostore


async def test_connection(params: dict) -> dict:
    """测试数据库连接"""
    dsn = _build_dsn(params)
    try:
        conn = await asyncpg.connect(dsn=dsn, timeout=10)
        await conn.execute("SELECT 1")
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = $1 ORDER BY table_name",
            params.get("schema_name", "public"),
        )
        await conn.close()
        return {
            "success": True,
            "table_count": len(tables),
            "tables": [r["table_name"] for r in tables],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def analyze_schema(params: dict) -> dict:
    """通过 LLM 分析数据库 Schema，生成本体候选定义"""
    conn_result = await test_connection(params)
    if not conn_result["success"]:
        return {"success": False, "error": conn_result["error"], "connection_test": conn_result}

    tables = conn_result.get("tables", [])
    exclude = params.get("exclude_tables", []) or []
    include = params.get("include_tables", []) or []
    if include:
        tables = [t for t in tables if t in include]
    else:
        tables = [t for t in tables if t not in exclude]

    if not tables:
        return {"success": True, "object_types": [], "link_types": [], "action_types": [], "tables_analyzed": 0, "raw_llm_response": "No tables to analyze"}

    # Fetch column info for each table
    schema_info = await _fetch_schema_detail(params, tables)

    # Build LLM prompt
    prompt = _build_analysis_prompt(schema_info, params.get("business_context", ""), params.get("output_language", "zh"), params.get("extract_wide_table_entities", False))

    # Call LLM
    llm_result = await _call_llm(prompt, params.get("custom_llm_config"))

    # Parse LLM response as JSON
    parsed = _parse_llm_response(llm_result)

    return {
        "success": True,
        "object_types": parsed.get("object_types", []),
        "link_types": parsed.get("link_types", []),
        "action_types": parsed.get("action_types", []),
        "tables_analyzed": len(tables),
        "raw_llm_response": llm_result,
    }


async def compile_ontology(analysis_result: dict) -> dict:
    """编译 LLM 分析结果 — 验证 + 自动修复"""
    errors = []
    warnings = []
    object_types = analysis_result.get("object_types", [])
    link_types = analysis_result.get("link_types", [])
    action_types = analysis_result.get("action_types", [])

    # Validate Object Types
    valid_ot_names = set()
    for ot in object_types:
        if not ot.get("type_name"):
            errors.append("对象类型缺少 type_name")
            continue
        valid_ot_names.add(ot["type_name"])
        if not ot.get("display_name"):
            ot["display_name"] = ot["type_name"]

        # Validate properties
        for prop in ot.get("properties", []):
            if not prop.get("name"):
                errors.append(f"ObjectType '{ot['type_name']}' 的属性缺少 name")
            if prop.get("type") not in ("string", "number", "datetime", "boolean", None):
                warnings.append(f"ObjectType '{ot['type_name']}' 的属性 '{prop.get('name')}' 类型 '{prop.get('type')}' 已修正为 'string'")
                prop["type"] = "string"

    # Validate Link Types — check source/target exist
    for lt in link_types:
        if not lt.get("link_name"):
            errors.append("链接类型缺少 link_name")
            continue
        if lt.get("source_type") and lt["source_type"] not in valid_ot_names:
            errors.append(f"LinkType '{lt['link_name']}' 的 source_type '{lt['source_type']}' 不存在")
        if lt.get("target_type") and lt["target_type"] not in valid_ot_names:
            errors.append(f"LinkType '{lt['link_name']}' 的 target_type '{lt['target_type']}' 不存在")

    # Suggest fixes for common issues
    auto_fix_count = 0
    for ot in object_types:
        for prop in ot.get("properties", []):
            if prop.get("type") not in ("string", "number", "datetime", "boolean"):
                prop["type"] = "string"
                auto_fix_count += 1

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "auto_fix_count": auto_fix_count,
        "compiled": {
            "object_types": object_types,
            "link_types": link_types,
            "action_types": action_types,
        },
        "stats": {
            "object_type_count": len(object_types),
            "link_type_count": len(link_types),
            "action_type_count": len(action_types),
        },
    }


async def register_ontology(dataset_id: str, compiled: dict) -> dict:
    """注册编译后的本体定义到数据库"""
    object_types = compiled.get("object_types", [])
    link_types = compiled.get("link_types", [])
    action_types = compiled.get("action_types", [])

    registered: dict = {"object_types": [], "link_types": [], "action_types": [], "merged": 0, "created": 0}

    for ot in object_types:
        existing = await ostore.get_object_type(dataset_id, ot["type_name"])
        await ostore.create_object_type(dataset_id, ot)  # UPSERT
        registered["object_types"].append(ot["type_name"])
        if existing:
            registered["merged"] += 1
        else:
            registered["created"] += 1

    for lt in link_types:
        existing = await ostore.get_link_type(dataset_id, lt["link_name"])
        await ostore.create_link_type(dataset_id, lt)  # UPSERT
        registered["link_types"].append(lt["link_name"])

    for at in action_types:
        existing = await ostore.get_action_type(dataset_id, at["action_name"])
        await ostore.create_action_type(dataset_id, at)
        registered["action_types"].append(at["action_name"])

    return registered


async def quick_model(params: dict) -> dict:
    """快速建模 — 直接从表结构映射，每表→ObjectType，不用 LLM"""
    conn_result = await test_connection(params)
    if not conn_result["success"]:
        return {"success": False, "error": conn_result["error"]}

    tables = conn_result.get("tables", [])
    exclude = params.get("exclude_tables", []) or []
    include = params.get("include_tables", []) or []
    if include:
        tables = [t for t in tables if t in include]
    else:
        tables = [t for t in tables if t not in exclude]

    schema_info = await _fetch_schema_detail(params, tables)

    object_types = []
    for table, cols in schema_info.items():
        properties = []
        for col in cols:
            prop = {
                "name": col["column_name"],
                "type": _map_pg_type(col["data_type"]),
                "required": col["is_nullable"] == "NO",
                "unique": col.get("is_identity", False),
                "indexed": col.get("is_identity", False) or col.get("is_primary", False),
                "description": col.get("comment", ""),
            }
            properties.append(prop)
        object_types.append({
            "type_name": _pascal_case(table),
            "display_name": table,
            "description": f"从表 {table} 快速映射",
            "properties": properties,
            "source": {"table": table, "connection_type": params.get("connection_type", "parameters")},
        })

    return {
        "success": True,
        "object_types": object_types,
        "link_types": [],
        "action_types": [],
        "tables_analyzed": len(tables),
    }


async def detect_changes(dataset_id: str, params: dict) -> dict:
    """结构变更检测 — 对比当前 Schema 与已注册 Ontology 定义的差异"""
    # Connect to source database
    conn_result = await test_connection(params)
    if not conn_result["success"]:
        return {"success": False, "error": conn_result["error"]}

    tables = conn_result.get("tables", [])
    exclude = params.get("exclude_tables", []) or []
    include = params.get("include_tables", []) or []
    if include:
        tables = [t for t in tables if t in include]
    else:
        tables = [t for t in tables if t not in exclude]

    # Fetch current schema from source DB
    current_schema = await _fetch_schema_detail(params, tables)

    # Fetch registered object_types from ontology
    registered_ots, _ = await ostore.list_object_types(dataset_id, page=1, page_size=10000)

    changes: list[dict] = []
    registered_tables: dict[str, dict] = {}

    for ot in registered_ots:
        source = ot.get("source") or {}
        source_table = source.get("table") if isinstance(source, dict) else None
        if source_table:
            registered_tables[source_table] = ot

    detected_tables = set()

    # Check each current table
    for table, cols in current_schema.items():
        detected_tables.add(table)
        ot_name = _pascal_case(table)

        if table not in registered_tables:
            changes.append({
                "type": "added",
                "entity_type": "object_type",
                "object_type": ot_name,
                "field": table,
                "old_value": None,
                "new_value": f"新表 {table} 未注册（{len(cols)} 列）",
            })
            continue

        ot = registered_tables[table]
        existing_props = {p["name"]: p for p in ot.get("properties", [])}
        current_cols = {c["column_name"]: c for c in cols}

        # Check for added/modified columns
        for col_name, col_info in current_cols.items():
            if col_name not in existing_props:
                changes.append({
                    "type": "added",
                    "entity_type": "property",
                    "object_type": ot["type_name"],
                    "field": col_name,
                    "old_value": None,
                    "new_value": _map_pg_type(col_info["data_type"]),
                })
            else:
                ep = existing_props[col_name]
                new_type = _map_pg_type(col_info["data_type"])
                if ep.get("type") != new_type:
                    changes.append({
                        "type": "modified",
                        "entity_type": "property",
                        "object_type": ot["type_name"],
                        "field": col_name,
                        "old_value": ep.get("type"),
                        "new_value": new_type,
                    })

        # Check for deleted columns
        for prop_name, prop_info in existing_props.items():
            if prop_name not in current_cols:
                changes.append({
                    "type": "deleted",
                    "entity_type": "property",
                    "object_type": ot["type_name"],
                    "field": prop_name,
                    "old_value": prop_info.get("type"),
                    "new_value": None,
                })

    # Check for deleted tables (registered but no longer in source)
    for table, ot in registered_tables.items():
        if table not in detected_tables:
            changes.append({
                "type": "deleted",
                "entity_type": "object_type",
                "object_type": ot["type_name"],
                "field": table,
                "old_value": f"已注册表 {table}",
                "new_value": None,
            })

    # Build summary
    added = [c for c in changes if c["type"] == "added"]
    modified = [c for c in changes if c["type"] == "modified"]
    deleted = [c for c in changes if c["type"] == "deleted"]

    return {
        "success": True,
        "changes": changes,
        "summary": {
            "total": len(changes),
            "added": len(added),
            "modified": len(modified),
            "deleted": len(deleted),
        },
        "current_tables": tables,
        "registered_objects": list(registered_tables.keys()),
        "tables_analyzed": len(tables),
    }


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _build_dsn(params: dict) -> str:
    ct = params.get("connection_type", "parameters")
    if ct == "dsn" and params.get("dsn"):
        return params["dsn"]
    host = params.get("host", "localhost")
    port = params.get("port", 5432)
    db = params.get("database", "postgres")
    user = params.get("username", "postgres")
    pwd = params.get("password", "postgres")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


async def _fetch_schema_detail(params: dict, tables: list[str]) -> dict[str, list[dict]]:
    dsn = _build_dsn(params)
    schema_name = params.get("schema_name", "public")
    conn = await asyncpg.connect(dsn=dsn, timeout=10)
    try:
        result = {}
        for table in tables:
            cols = await conn.fetch(
                """SELECT column_name, data_type, is_nullable, column_default,
                          col_description((SELECT oid FROM pg_class WHERE relname = $1), ordinal_position) as comment
                   FROM information_schema.columns
                   WHERE table_schema = $2 AND table_name = $1 ORDER BY ordinal_position""",
                table, schema_name,
            )
            # Get primary key info
            pk = await conn.fetchrow(
                """SELECT kcu.column_name
                   FROM information_schema.table_constraints tc
                   JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                   WHERE tc.table_schema = $2 AND tc.table_name = $1 AND tc.constraint_type = 'PRIMARY KEY'
                   LIMIT 1""",
                table, schema_name,
            )
            pk_col = pk["column_name"] if pk else None
            col_list = []
            for c in cols:
                entry = dict(c)
                entry["is_primary"] = c["column_name"] == pk_col
                entry["is_identity"] = "nextval" in str(c.get("column_default", "") or "")
                col_list.append(entry)
            result[table] = col_list
        return result
    finally:
        await conn.close()


def _build_analysis_prompt(schema_info: dict, business_context: str, language: str, extract_wide: bool) -> str:
    schema_text = json.dumps(schema_info, ensure_ascii=False, indent=2)
    lang_instruction = "请用中文输出" if language == "zh" else "Please output in English"
    wide_instruction = "尝试从宽表中提取嵌套实体（例如：员工表中拆分出部门、职位等独立实体）" if extract_wide else ""

    return f"""你是一个数据库建模专家。请根据以下数据库表结构，生成本体定义（Ontology）。

{lang_instruction}

数据库表结构：
```json
{schema_text}
```

业务背景说明：
{business_context or "未提供"}

要求：
1. 每个表映射为一个 ObjectType，type_name 使用驼峰命名
2. 分析列的外键关系，推断 LinkType（表间关系），link_name 使用小写下划线
3. 如果列包含 webhook/回调相关字段，考虑生成 ActionType
4. 列的类型映射：varchar/text → string, integer/bigint → number, timestamp/date → datetime, boolean → boolean
5. 标记主键列 required+unique
{wide_instruction}

输出格式严格 JSON（不要包含其他文本）：
{{
  "object_types": [
    {{
      "type_name": "驼峰命名",
      "display_name": "中文显示名",
      "description": "简要描述",
      "properties": [
        {{"name": "列名", "type": "string|number|datetime|boolean", "required": true|false, "unique": true|false, "indexed": true|false, "description": "列注释"}}
      ]
    }}
  ],
  "link_types": [
    {{
      "link_name": "snake_case",
      "display_name": "关系中文名",
      "source_type": "源ObjectType",
      "target_type": "目标ObjectType",
      "directed": true,
      "description": "关系描述"
    }}
  ],
  "action_types": []
}}"""


async def _call_llm(prompt: str, custom_config: dict | None = None) -> str:
    import httpx

    cfg = custom_config or {}
    api_base = cfg.get("api_base", "https://api.deepseek.com/v1")
    api_key = cfg.get("api_key", "")
    model = cfg.get("model", "deepseek-chat")
    timeout = cfg.get("timeout_seconds", 300)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 8192,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _parse_llm_response(raw: str) -> dict:
    # Try direct JSON parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try extracting JSON from ```json blocks
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try extracting JSON between { and }
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"object_types": [], "link_types": [], "action_types": [], "parse_error": True, "raw": raw}


def _map_pg_type(pg_type: str) -> str:
    if pg_type in ("integer", "bigint", "smallint", "numeric", "decimal", "real", "double precision", "serial", "bigserial"):
        return "number"
    if pg_type in ("timestamp", "timestamptz", "date", "time", "timetz"):
        return "datetime"
    if pg_type in ("boolean", "bool"):
        return "boolean"
    return "string"


def _pascal_case(s: str) -> str:
    return "".join(part.capitalize() for part in s.replace("_", " ").split())
