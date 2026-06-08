# Task ID: 4

**Title:** 本体类型定义管理 (Object/Link/Action Types)

**Status:** pending

**Dependencies:** None

**Priority:** high

**Description:** 实现 Object Types（节点类型定义，含属性 PropertyDefinition）、Link Types（有向边/关系定义）、Action Types（可执行操作定义，含 Webhook 配置）的完整 CRUD。支持属性类型 string/number/datetime/boolean，required/unique/indexed 标记。Link Type 含 source_type/target_type/directed。Action Type 含 webhook_url/method/headers/effect_type。

**Details:**

API: /api/datasets/{id}/ontology/object-types/*, /link-types/*, /action-types/*。支持批量操作。

**Test Strategy:**

No test strategy provided.
