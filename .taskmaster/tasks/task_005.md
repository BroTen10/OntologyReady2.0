# Task ID: 5

**Title:** Objects/Links 实例管理

**Status:** pending

**Dependencies:** None

**Priority:** high

**Description:** 知识图谱中具体节点(Object)和关系(Link)的实例数据管理。支持 CRUD 单条和批量操作。对象搜索、分页查询。数据写入图数据库（Apache AGE 扩展）。

**Details:**

API: POST /api/datasets/{id}/ontology/objects/search, POST /api/datasets/{id}/ontology/graph/path, POST /api/datasets/{id}/ontology/graph/traverse。批量: BatchObjectsRequest, BatchLinksRequest。

**Test Strategy:**

No test strategy provided.
