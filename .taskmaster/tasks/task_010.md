# Task ID: 10

**Title:** 图遍历与路径查询 API

**Status:** pending

**Dependencies:** 1

**Priority:** high

**Description:** 实现图遍历与路径查询 API。邻居节点展开（深度1-N层可配置）、最短路径查询、子图遍历、路径查询。底层使用 Apache AGE 图数据库 Cypher 查询实现。

**Details:**

API: GET /api/datasets/{id}/ontology/graph/neighbors/{obj_type}/{obj_id}, POST /api/datasets/{id}/ontology/graph/path, POST /api/datasets/{id}/ontology/graph/traverse。

**Test Strategy:**

No test strategy provided.
