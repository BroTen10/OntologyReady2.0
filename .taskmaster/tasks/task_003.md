# Task ID: 3

**Title:** 数据集 CRUD

**Status:** pending

**Dependencies:** None

**Priority:** high

**Description:** 数据集语义上相当于"命名空间/知识空间"，每个数据集包含独立的本体定义、实例数据和图谱。实现 GET/POST /api/datasets 和 GET/DELETE /api/datasets/{dataset_id}。每个数据集独立 Schema ({dataset_id}_ontology) 和独立图空间 ({dataset_id}_graph)。

**Details:**

数据模型: dataset_id (_ontology_xxx), display_name, description, created_at, updated_at。

**Test Strategy:**

No test strategy provided.
