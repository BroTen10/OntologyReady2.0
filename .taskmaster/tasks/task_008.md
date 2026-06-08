# Task ID: 8

**Title:** LLM 辅助建模（三步向导）+ 快速建模

**Status:** pending

**Dependencies:** 1

**Priority:** high

**Description:** LLM 辅助建模——三步向导式交互。步骤一：连接配置（项目默认实例/数据库连接参数/DSN连接串三选一，含测试连接），配置 Schema/业务背景/输出语言/高级选项。步骤二：LLM 分析完成后预览生成结果，列表视图+图视图切换，支持 JSON 编辑、级联删除、编译检查+自动修复。步骤三：注册本体定义+触发数据同步（merge/UPSERT语义）。后端 API: POST /api/datasets/{id}/ontology/modeling/analyze-schema, compile, register。

**Details:**

支持宽表实体提取、自定义LLM配置、排除表。超过5分钟分析超时可配置。快速建模（直接表映射，不用LLM）也在此任务中。数据集已有定义时提示用结构变更检测。

**Test Strategy:**

No test strategy provided.
