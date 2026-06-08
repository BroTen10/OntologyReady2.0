# Task ID: 19

**Title:** 系统配置管理界面（Provider 切换可视化 + 连接测试）

**Status:** pending

**Dependencies:** 1

**Priority:** medium

**Description:** 全局系统配置管理界面。数据库连接配置（含连接测试）、文档引擎类型配置与切换（PostgreSQL/OpenSearch）、对象存储 OSS 配置（本地/MinIO/S3，含测试连接）、LLM/Embedding Provider 配置与切换、系统级参数（默认分页大小/会话超时等）。支持 ${env:VAR_NAME} 语法读取环境变量，UI 修改即时生效（不重启）。配置优先级: 环境变量 > .env > 数据库 system_config > 代码默认值。

**Details:**

API: GET/POST /api/admin/system-config, GET/PUT/DELETE /api/admin/system-config/{key}。前端: /admin/system-config。SystemConfigItem, EngineConfig, StorageConfig, LLMConfig。

**Test Strategy:**

No test strategy provided.
