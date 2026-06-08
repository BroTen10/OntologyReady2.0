# Task ID: 17

**Title:** Skills 系统（预设 Skills + 自定义上传 + 自动生成）

**Status:** pending

**Dependencies:** 4

**Priority:** high

**Description:** 可插拔的技能扩展框架。Skill CRUD（创建/编辑/删除/搜索/分类过滤）、Markdown 格式编写技能文档（SKILL.md + prompt.md + schema.json + scripts/）、预设技能包导入（rdb-to-ontology/csv-to-ontology/ontology-data-build/ontology-subgraph-search/ontology-ops-agent/polardb-kb-search-agent/polardb-kb-agent）、Zip 包上传下载、从本体 Action Types 自动生成技能定义。

**Details:**

Skill 结构: skill-name/SKILL.md(描述元数据), prompt.md(LLM提示词), schema.json(输入输出), scripts/(自动化)。API: CRUD + presets + upload + enable/disable/clone/regenerate + download + generate from dataset。前端: /skills 管理页面。

**Test Strategy:**

No test strategy provided.
