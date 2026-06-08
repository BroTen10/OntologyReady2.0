from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from ..database import get_pool

SCHEMA = "skills"


async def _ensure_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE SCHEMA IF NOT EXISTS {SCHEMA}
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.skills (
                id           TEXT PRIMARY KEY,
                name         TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                category     TEXT DEFAULT 'general',
                description  TEXT,
                tags         JSONB DEFAULT '[]',
                author       TEXT,
                version      TEXT DEFAULT '1.0.0',
                skill_md     TEXT,
                prompt_md    TEXT,
                schema_json  JSONB DEFAULT NULL,
                scripts      JSONB DEFAULT '{{}}',
                enabled      BOOLEAN DEFAULT TRUE,
                icon         TEXT,
                is_preset    BOOLEAN DEFAULT FALSE,
                created_at   TIMESTAMPTZ DEFAULT now(),
                updated_at   TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_skills_category ON {SCHEMA}.skills (category)
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_skills_name ON {SCHEMA}.skills (name)
        """)


# ═══════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════

async def create_skill(data: dict) -> dict:
    await _ensure_tables()
    pool = await get_pool()
    skill_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {SCHEMA}.skills (id, name, display_name, category, description,
                 tags, author, version, skill_md, prompt_md, schema_json, scripts,
                 enabled, icon, is_preset, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $16)
               RETURNING *""",
            skill_id,
            data["name"],
            data["display_name"],
            data.get("category", "general"),
            data.get("description"),
            json.dumps(data.get("tags", []), ensure_ascii=False),
            data.get("author"),
            data.get("version", "1.0.0"),
            data.get("skill_md"),
            data.get("prompt_md"),
            json.dumps(data.get("schema"), ensure_ascii=False) if data.get("schema") else None,
            json.dumps(data.get("scripts", {}), ensure_ascii=False),
            data.get("enabled", True),
            data.get("icon"),
            data.get("is_preset", False),
            now,
        )
    return _row_to_dict(row)


async def get_skill(skill_id: str) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {SCHEMA}.skills WHERE id = $1", skill_id)
    return _row_to_dict(row) if row else None


async def get_skill_by_name(name: str) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {SCHEMA}.skills WHERE name = $1", name)
    return _row_to_dict(row) if row else None


async def list_skills(
    page: int = 1,
    page_size: int = 100,
    category: str | None = None,
    search: str | None = None,
    tags: list[str] | None = None,
    enabled_only: bool = False,
) -> tuple[list[dict], int]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        wheres = []
        params: list[Any] = []
        idx = 1

        if category:
            wheres.append(f"category = ${idx}")
            params.append(category)
            idx += 1
        if search:
            wheres.append(f"(name ILIKE ${idx} OR display_name ILIKE ${idx} OR description ILIKE ${idx})")
            params.append(f"%{search}%")
            idx += 1
        if tags:
            tag_conds = []
            for t in tags:
                tag_conds.append(f"tags ? ${idx}")
                params.append(t)
                idx += 1
            wheres.append(f"({' OR '.join(tag_conds)})")
        if enabled_only:
            wheres.append("enabled = TRUE")

        where_clause = f"WHERE {' AND '.join(wheres)}" if wheres else ""

        total = await conn.fetchval(f"SELECT count(*) FROM {SCHEMA}.skills {where_clause}", *params)

        query_params = params + [page_size, (page - 1) * page_size]
        rows = await conn.fetch(
            f"SELECT * FROM {SCHEMA}.skills {where_clause} ORDER BY updated_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *query_params,
        )
    return [_row_to_dict(r) for r in rows], total


async def update_skill(skill_id: str, data: dict) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        setters: list[str] = []
        vals: list[Any] = []
        idx = 1

        scalar_fields = [
            ("display_name", "display_name"), ("category", "category"),
            ("description", "description"), ("author", "author"), ("version", "version"),
            ("enabled", "enabled"), ("icon", "icon"), ("skill_md", "skill_md"),
            ("prompt_md", "prompt_md"),
        ]
        for py_key, col in scalar_fields:
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(data[py_key])
                idx += 1

        json_fields = [("tags", "tags"), ("schema", "schema_json"), ("scripts", "scripts")]
        for py_key, col in json_fields:
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(json.dumps(data[py_key], ensure_ascii=False))
                idx += 1

        if not setters:
            return await get_skill(skill_id)

        setters.append(f"updated_at = ${idx}")
        vals.append(datetime.now(UTC))
        idx += 1
        vals.append(skill_id)
        sql = f"UPDATE {SCHEMA}.skills SET {', '.join(setters)} WHERE id = ${idx} RETURNING *"
        row = await conn.fetchrow(sql, *vals)
    return _row_to_dict(row) if row else None


async def delete_skill(skill_id: str) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {SCHEMA}.skills WHERE id = $1", skill_id)
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# Actions — enable / disable / clone
# ═══════════════════════════════════════════════════════════

async def set_enabled(skill_id: str, enabled: bool) -> dict | None:
    return await update_skill(skill_id, {"enabled": enabled})


async def clone_skill(skill_id: str, new_name: str) -> dict | None:
    original = await get_skill(skill_id)
    if not original:
        return None
    data = dict(original)
    data["name"] = new_name
    data["display_name"] = f"{original['display_name']} (Copy)"
    data["is_preset"] = False
    # Remove fields that are auto-generated
    for k in ("id", "created_at", "updated_at"):
        data.pop(k, None)
    return await create_skill(data)


# ═══════════════════════════════════════════════════════════
# Preset skills
# ═══════════════════════════════════════════════════════════

PRESET_SKILLS = {
    "rdb-to-ontology": {
        "name": "rdb-to-ontology",
        "display_name": "RDB to Ontology",
        "category": "ingestion",
        "description": "从关系型数据库（MySQL/PostgreSQL）自动提取表结构并生成 Object/Link Type 定义",
        "tags": ["rdb", "ontology", "ingestion"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "database",
        "skill_md": "# RDB to Ontology\n\n## 描述\n连接关系型数据库，分析 Schema 并生成本体类型定义。\n\n## 能力\n- 自动发现表和外键关系\n- 映射 SQL 类型到本体属性类型\n- 生成 Object Type 和 Link Type",
        "prompt_md": "You are an RDB schema analyzer. Given database connection info, discover tables, columns, and foreign keys. Map each table to an Object Type with appropriate properties. Map foreign keys to Link Types with correct source/target. Output the ontology definitions in the schema format.",
        "schema": {
            "inputs": [
                {"name": "connection_string", "type": "string", "required": True, "description": "Database connection string"},
                {"name": "schema_filter", "type": "array", "required": False, "description": "Schemas to include"},
                {"name": "table_filter", "type": "array", "required": False, "description": "Tables to include"},
            ],
            "outputs": [
                {"name": "object_types", "type": "array", "description": "Generated Object Type definitions"},
                {"name": "link_types", "type": "array", "description": "Generated Link Type definitions"},
            ],
        },
    },
    "csv-to-ontology": {
        "name": "csv-to-ontology",
        "display_name": "CSV to Ontology",
        "category": "ingestion",
        "description": "从 CSV 文件自动推断列类型并生成 Object Type 定义",
        "tags": ["csv", "ontology", "ingestion"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "file-text",
        "skill_md": "# CSV to Ontology\n\n## 描述\n解析 CSV 文件，推断每列的数据类型，自动生成 Object Type 定义。\n\n## 能力\n- 采样分析列数据类型\n- 检测枚举值\n- 生成 PropertyDefinition 列表",
        "prompt_md": "You are a CSV data profiler. Analyze the provided CSV headers and sample rows. Infer the data type for each column (string, number, datetime, boolean). Detect potential enum values. Generate a complete Object Type definition including all properties with appropriate types, required flags, and descriptions.",
        "schema": {
            "inputs": [
                {"name": "csv_content", "type": "string", "required": True, "description": "CSV file content"},
                {"name": "type_name", "type": "string", "required": True, "description": "Target Object Type name"},
                {"name": "sample_rows", "type": "number", "required": False, "default": 100, "description": "Number of rows to sample"},
            ],
            "outputs": [
                {"name": "object_type", "type": "object", "description": "Generated Object Type definition"},
            ],
        },
    },
    "ontology-data-builder": {
        "name": "ontology-data-builder",
        "display_name": "Ontology Data Builder",
        "category": "ontology",
        "description": "批量创建本体实例数据，支持从多种数据源导入并填充 Object/Link 实例",
        "tags": ["ontology", "instance", "bulk"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "build",
        "skill_md": "# Ontology Data Builder\n\n## 描述\n批量导入和构建本体实例数据。\n\n## 能力\n- 批量创建 Object 实例\n- 批量创建 Link 实例\n- 支持 JSON/CSV 数据源\n- 自动验证属性类型和必填字段",
        "prompt_md": "You are a data builder for ontology instances. Given a dataset ID and instance data, create Object and Link instances in bulk. Validate property types, required fields, and type references. Report any validation errors or duplicates.",
        "schema": {
            "inputs": [
                {"name": "dataset_id", "type": "string", "required": True, "description": "Target dataset ID"},
                {"name": "objects", "type": "array", "required": False, "description": "Object instances to create"},
                {"name": "links", "type": "array", "required": False, "description": "Link instances to create"},
                {"name": "data_source", "type": "string", "required": False, "description": "JSON data or CSV content"},
            ],
            "outputs": [
                {"name": "objects_created", "type": "number", "description": "Number of objects created"},
                {"name": "links_created", "type": "number", "description": "Number of links created"},
                {"name": "errors", "type": "array", "description": "Validation errors"},
            ],
        },
    },
    "graphrag-builder": {
        "name": "graphrag-builder",
        "display_name": "GraphRAG Builder",
        "category": "graphrag",
        "description": "从文档/文本构建 GraphRAG 知识图谱，自动抽取实体和关系",
        "tags": ["graphrag", "knowledge-graph", "extraction"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "node-index",
        "skill_md": "# GraphRAG Builder\n\n## 描述\n从非结构化文本中抽取实体和关系，构建 GraphRAG 知识图谱。\n\n## 能力\n- 实体识别和抽取\n- 关系抽取\n- 实体合并和去重\n- 社区检测",
        "prompt_md": "You are a GraphRAG knowledge graph builder. Extract entities and relationships from the provided text. Use the configured LLM for entity recognition. Output the graph structure ready for indexing.",
        "schema": {
            "inputs": [
                {"name": "documents", "type": "array", "required": True, "description": "Documents to process"},
                {"name": "entity_types", "type": "array", "required": False, "description": "Entity types to extract"},
            ],
            "outputs": [
                {"name": "entities", "type": "array", "description": "Extracted entities"},
                {"name": "relationships", "type": "array", "description": "Extracted relationships"},
                {"name": "communities", "type": "array", "description": "Detected communities"},
            ],
        },
    },
    "data-quality-checker": {
        "name": "data-quality-checker",
        "display_name": "Data Quality Checker",
        "category": "quality",
        "description": "数据质量检查：检测缺失值、重复数据、异常值和类型不匹配",
        "tags": ["quality", "validation", "data"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "check-circle",
        "skill_md": "# Data Quality Checker\n\n## 描述\n对本体实例数据进行质量检查，生成质量报告。\n\n## 能力\n- 检测缺失的必填属性\n- 检测重复实例\n- 检测属性值类型不匹配\n- 检测孤立节点\n- 生成数据质量评分",
        "prompt_md": "You are a data quality inspector. Scan the provided ontology instances for common quality issues: missing required fields, type mismatches, duplicates, orphaned nodes. Generate a quality report with actionable recommendations.",
        "schema": {
            "inputs": [
                {"name": "dataset_id", "type": "string", "required": True, "description": "Target dataset ID"},
                {"name": "object_types", "type": "array", "required": False, "description": "Specific object types to check (empty = all)"},
                {"name": "checks", "type": "array", "required": False, "description": "Specific checks to run (null_check, duplicate_check, type_check, orphan_check)"},
            ],
            "outputs": [
                {"name": "report", "type": "object", "description": "Quality report with issues and score"},
            ],
        },
    },
    "ontology-subgraph-search": {
        "name": "ontology-subgraph-search",
        "display_name": "Ontology Subgraph Search",
        "category": "ontology",
        "description": "图遍历查询：按实体/关系/深度检索子图，支持路径发现和邻域探索",
        "tags": ["ontology", "graph", "search", "traversal"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "search",
        "skill_md": "# Ontology Subgraph Search\n\n## 描述\n从起始节点出发，按指定的关系和深度对知识图谱进行遍历查询，返回子图结构。\n\n## 能力\n- 指定起始实体，按关系类型搜索 K-hop 邻居\n- 双向扩展（入边 + 出边）\n- 路径发现和最短路径查询\n- 子图导出为 JSON/GraphML",
        "prompt_md": "You are a graph traversal engine for ontology knowledge graphs. Given a starting entity, relation types to follow, and a hop depth, traverse the graph and return the induced subgraph. Support bidirectional traversal and path queries.",
        "schema": {
            "inputs": [
                {"name": "dataset_id", "type": "string", "required": True, "description": "Target dataset ID"},
                {"name": "start_entity_ids", "type": "array", "required": True, "description": "Starting entity IDs"},
                {"name": "relation_types", "type": "array", "required": False, "description": "Link types to traverse (empty = all)"},
                {"name": "max_depth", "type": "number", "required": False, "default": 3, "description": "Maximum traversal depth (K-hop)"},
                {"name": "direction", "type": "string", "required": False, "default": "both", "enum": ["outgoing", "incoming", "both"], "description": "Traversal direction"},
                {"name": "limit", "type": "number", "required": False, "default": 100, "description": "Max nodes to return"},
            ],
            "outputs": [
                {"name": "nodes", "type": "array", "description": "Subgraph nodes"},
                {"name": "edges", "type": "array", "description": "Subgraph edges"},
                {"name": "paths", "type": "array", "description": "Discovered paths"},
            ],
        },
    },
    "ontology-ops-agent": {
        "name": "ontology-ops-agent",
        "display_name": "Ontology Ops Agent",
        "category": "ontology",
        "description": "本体运维代理：批量编辑、合并、拆分、校验、迁移等运维操作",
        "tags": ["ontology", "ops", "maintenance"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "tool",
        "skill_md": "# Ontology Ops Agent\n\n## 描述\n面向本体运维的 Agent，提供批量操作和自动化运维能力。\n\n## 能力\n- 批量属性更新（按条件筛选 → 批量修改）\n- 实体合并（合并重复实体，迁移关联）\n- 实体拆分（按属性拆分 + 关联）\n- 类型迁移（Object Type 变更）\n- 一致性校验和修复",
        "prompt_md": "You are an ontology operations agent. Execute maintenance tasks on ontology instances: batch updates, entity merging/deduplication, type migrations, and consistency repairs. Always validate before applying changes and report affected counts.",
        "schema": {
            "inputs": [
                {"name": "dataset_id", "type": "string", "required": True, "description": "Target dataset ID"},
                {"name": "operation", "type": "string", "required": True, "enum": ["batch_update", "merge", "split", "migrate", "validate", "repair"], "description": "Operation type"},
                {"name": "params", "type": "object", "required": True, "description": "Operation-specific parameters"},
                {"name": "dry_run", "type": "boolean", "required": False, "default": True, "description": "Preview changes without applying"},
            ],
            "outputs": [
                {"name": "affected_count", "type": "number", "description": "Number of affected entities"},
                {"name": "changes", "type": "array", "description": "Detailed change log"},
                {"name": "errors", "type": "array", "description": "Validation errors"},
            ],
        },
    },
    "polardb-kb-search-agent": {
        "name": "polardb-kb-search-agent",
        "display_name": "PolarDB KB Search Agent",
        "category": "knowledge",
        "description": "基于 PolarDB 知识库的语义搜索 Agent，支持混合检索（向量 + 关键词）",
        "tags": ["polardb", "knowledge-base", "search", "hybrid"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "search",
        "skill_md": "# PolarDB KB Search Agent\n\n## 描述\n对接 PolarDB 知识库，提供混合语义搜索能力。结合向量相似度与关键词匹配，返回排序后的知识片段。\n\n## 能力\n- 向量语义搜索\n- 关键词 BM25 检索\n- 混合检索与重排序\n- 搜索结果摘要生成",
        "prompt_md": "You are a knowledge base search agent for PolarDB. Perform hybrid search combining vector similarity and keyword matching. Return ranked knowledge snippets with relevance scores and summaries.",
        "schema": {
            "inputs": [
                {"name": "query", "type": "string", "required": True, "description": "Search query"},
                {"name": "top_k", "type": "number", "required": False, "default": 10, "description": "Number of results to return"},
                {"name": "search_mode", "type": "string", "required": False, "default": "hybrid", "enum": ["vector", "keyword", "hybrid"], "description": "Search mode"},
                {"name": "filters", "type": "object", "required": False, "description": "Metadata filters"},
            ],
            "outputs": [
                {"name": "results", "type": "array", "description": "Ranked search results with snippets and scores"},
                {"name": "summary", "type": "string", "description": "Search result summary"},
            ],
        },
    },
    "polardb-kb-agent": {
        "name": "polardb-kb-agent",
        "display_name": "PolarDB KB Agent",
        "category": "knowledge",
        "description": "PolarDB 知识库综合 Agent：文档入库、问答、知识管理一站式服务",
        "tags": ["polardb", "knowledge-base", "qa", "ingestion"],
        "author": "platform",
        "version": "1.0.0",
        "icon": "robot",
        "skill_md": "# PolarDB KB Agent\n\n## 描述\nPolarDB 知识库综合管理 Agent。支持文档入库、智能问答、知识库维护等全流程操作。\n\n## 能力\n- 文档批量入库（支持 PDF/Markdown/代码文件）\n- 基于知识库的 RAG 问答\n- 知识库索引管理（重建/更新/删除）\n- 知识质量监控和告警",
        "prompt_md": "You are a comprehensive knowledge base agent for PolarDB. Manage the full lifecycle: document ingestion, index management, RAG-based QA, and quality monitoring. Provide clear, cited answers from the knowledge base.",
        "schema": {
            "inputs": [
                {"name": "action", "type": "string", "required": True, "enum": ["ingest", "qa", "index_manage", "monitor"], "description": "Action to perform"},
                {"name": "documents", "type": "array", "required": False, "description": "Documents for ingestion"},
                {"name": "question", "type": "string", "required": False, "description": "Question for QA"},
                {"name": "index_operation", "type": "string", "required": False, "enum": ["rebuild", "update", "delete"], "description": "Index management operation"},
            ],
            "outputs": [
                {"name": "answer", "type": "string", "description": "QA answer or operation result"},
                {"name": "sources", "type": "array", "description": "Source citations"},
                {"name": "status", "type": "string", "description": "Operation status"},
            ],
        },
    },
}

async def list_presets() -> list[dict]:
    return [v for v in PRESET_SKILLS.values()]


async def get_preset(name: str) -> dict | None:
    return PRESET_SKILLS.get(name)


async def import_presets(preset_names: list[str]) -> list[dict]:
    results = []
    for name in preset_names:
        preset = PRESET_SKILLS.get(name)
        if not preset:
            results.append({"name": name, "status": "not_found", "error": "Preset not found"})
            continue
        # Check if already imported
        existing = await get_skill_by_name(name)
        if existing:
            results.append({"name": name, "status": "skipped", "error": "Already exists"})
            continue
        data = dict(preset)
        data["is_preset"] = True
        data.pop("schema", None)
        if preset.get("schema"):
            data["schema"] = preset["schema"]
        try:
            created = await create_skill(data)
            results.append({"name": name, "status": "created", "id": created["id"]})
        except Exception as e:
            results.append({"name": name, "status": "error", "error": str(e)})
    return results


# ═══════════════════════════════════════════════════════════
# Generate skill from Action Type
# ═══════════════════════════════════════════════════════════

async def generate_from_action_type(
    dataset_id: str,
    action_name: str,
    category: str = "generated",
    display_name: str | None = None,
    description: str | None = None,
) -> dict | None:
    from . import ontology_store
    schema = dataset_id.replace("-", "_")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {schema}.action_types WHERE action_name = $1", action_name)
    if not row:
        return None

    action = dict(row)
    # Parse JSON fields
    for k in ("parameters", "headers"):
        if isinstance(action.get(k), str):
            try:
                action[k] = json.loads(action[k])
            except (json.JSONDecodeError, TypeError):
                pass

    skill_name = f"action-{action_name}"
    existing = await get_skill_by_name(skill_name)
    if existing:
        return existing

    # Build schema inputs from action parameters
    inputs = []
    for p in action.get("parameters", []):
        inputs.append({
            "name": p.get("name", "param"),
            "type": p.get("type", "string"),
            "required": p.get("required", False),
            "description": p.get("description", ""),
            "enum": p.get("enum"),
        })

    # Add target object as input
    inputs.insert(0, {
        "name": "target_object",
        "type": "string",
        "required": True,
        "description": f"Target {action.get('target_type', 'object')} ID",
    })

    skill_data = {
        "name": skill_name,
        "display_name": display_name or f"Action: {action.get('display_name', action_name)}",
        "category": category,
        "description": description or action.get("description", f"Execute action {action_name}"),
        "tags": ["generated", f"action:{action_name}", f"target:{action.get('target_type', 'unknown')}"],
        "author": "system",
        "version": "1.0.0",
        "icon": "thunderbolt",
        "skill_md": f"# {action.get('display_name', action_name)}\n\nAuto-generated from Action Type `{action_name}`.\n\nTarget Type: `{action.get('target_type', 'unknown')}`\nMethod: `{action.get('method', 'POST')}`\nWebhook: `{action.get('webhook_url', 'N/A')}`",
        "prompt_md": f"Execute action {action_name} on the target {action.get('target_type', 'object')}. Use the webhook at {action.get('webhook_url', 'N/A')}. Validate all parameters before execution.",
        "schema": {
            "inputs": inputs,
            "outputs": [
                {"name": "status", "type": "string", "description": "Execution status"},
                {"name": "result", "type": "object", "description": "Execution result"},
            ],
        },
        "is_preset": False,
    }
    return await create_skill(skill_data)


# ═══════════════════════════════════════════════════════════
# Category list
# ═══════════════════════════════════════════════════════════

async def list_categories() -> list[str]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT DISTINCT category FROM {SCHEMA}.skills ORDER BY category")
    return [r["category"] for r in rows]


# ═══════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════

def _row_to_dict(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    json_fields = ["tags", "schema_json", "scripts"]
    for k in json_fields:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    # Map schema_json → schema for response
    if "schema_json" in d:
        d["schema"] = d.pop("schema_json")
    for ts_field in ["created_at", "updated_at"]:
        if d.get(ts_field):
            d[ts_field] = d[ts_field].isoformat()
    return d
