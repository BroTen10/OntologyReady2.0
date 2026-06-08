# Task ID: 11

**Title:** BuiltinRAGProvider 实现 — 文档解析 + Chunk + 检索 + 问答

**Status:** pending

**Dependencies:** 1

**Priority:** high

**Description:** 实现 BuiltinRAGProvider 自研 RAG 引擎。依赖 DocumentEngine + Embedding + LLM 三个 Provider 协作。功能: 文档解析（PDF/Word/Markdown/TXT/HTML/CSV/Excel）、Chunk 策略（固定大小/按段落/按标题/语义分块/自定义）、知识库 CRUD、文档上传与管理、检索（全文/向量/混合）、基于知识库的 LLM 问答、流式输出。管理员配置（OSS/文档引擎/模型）。

**Details:**

文档处理状态机: pending→processing→preprocessed→processed|failed。解析器支持 mineru/docling/paddleocr。分块参数: 大小1200，重叠100。前端页面: /ragflow/knowledge-base, /ragflow/chat, /ragflow/retrieval, /ragflow/model-config, /ragflow/service-config。角色权限: VIEWER查询/DEVELOPER管理/ADMIN配置。

**Test Strategy:**

No test strategy provided.
