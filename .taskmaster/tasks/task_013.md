# Task ID: 13

**Title:** GraphRAG — 知识图谱增强检索 + 知识问答

**Status:** pending

**Dependencies:** 1

**Priority:** high

**Description:** 基于图结构的知识增强检索系统。Workspace 管理（创建/切换/删除/默认空间）、文档解析与分块、知识图谱构建（LLM实体抽取+关系抽取写入AGE图存储）、6种检索模式（本地/全局/混合/混合检索/朴素/绕过）、多轮对话问答、知识图谱可视化（实体-关系网络G6渲染，支持缩放/平移/高亮/标签筛选/搜索）。

**Details:**

前端: /graphrag/knowledge-base, /graphrag/documents, /graphrag/graph, /graphrag/qa, /graphrag/model-config。默认实体类型: organization/person/geo/event/category。模型配置: LLM/Embedding/Rerank/VLM 四种类型，模型提供商+模型两层架构，格式 model@provider。

**Test Strategy:**

No test strategy provided.
