# Task ID: 9

**Title:** 暂存区 (Staging) + 版本管理

**Status:** pending

**Dependencies:** 4

**Priority:** high

**Description:** 实现类 Git 的暂存区机制（staged/commit/discard/undo）和版本管理系统（每次变更创建版本快照，支持版本对比分析和回滚到任意历史版本）。Staging 使用 JSON 存储待提交变更。版本快照存储完整 Ontology 定义。

**Details:**

API: StagedChangeRef, CommitStagingRequest, UndoStagedChangesRequest。VersionSnapshot, UpdateVersionNotesRequest。前端: /ontology/versions 版本对比与回滚页面。

**Test Strategy:**

No test strategy provided.
