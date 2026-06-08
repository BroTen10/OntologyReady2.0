# Task ID: 20

**Title:** 快速建模 + 结构变更检测 + 异步任务队列

**Status:** pending

**Dependencies:** 8

**Priority:** medium

**Description:** 实现快速建模（直接基于数据库表结构生成，每表→ObjectType，无需LLM）、结构变更检测（自动对比当前Schema与已注册Ontology定义差异 → 审核差异清单 → 增量更新）、异步任务队列（内存队列开发用/Redis+Celery生产用）支持 LLM Schema分析/数据同步/文档解析/GraphRAG运行/RAG评测运行。

**Details:**

前端: /ontology/data-management 数据管理入口（含4个子入口），/ontology/modeling LLM建模。结构变更检测复用 SchemaAnalyzeRequest。

**Test Strategy:**

No test strategy provided.
