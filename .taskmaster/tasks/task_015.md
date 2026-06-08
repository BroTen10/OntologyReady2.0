# Task ID: 15

**Title:** 多数据源同步（PostgreSQL/MySQL/Hive/HBase/Lindorm）

**Status:** pending

**Dependencies:** 3

**Priority:** high

**Description:** 实现对多种外部数据源的连接与数据同步。支持 PostgreSQL / MySQL / Hive / HBase / Lindorm 等数据源接入。数据同步使用 merge（UPSERT）语义：目标不存在则 INSERT，存在则 UPDATE。根据 ID 防重复。小数据量同步执行，大数据量自动转异步后台任务。增量同步+断点续传。

**Details:**

API: SyncRequest, SyncConfig。异步任务管理: GET /api/tasks/{task_id}, GET /api/tasks/{task_id}/logs, POST /api/tasks/{task_id}/cancel。状态: pending→running→completed|failed|cancelled。

**Test Strategy:**

No test strategy provided.
