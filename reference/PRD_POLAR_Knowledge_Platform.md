# POLAR 知识平台 (POLAR Knowledge Platform) — PRD 复刻文档

> **目标**: 1:1 复刻该 Ontology Platform 网站系统  
> **分析日期**: 2026-06-06  
> **原系统地址**: http://47.115.252.39:8080/  
> **系统名称**: POLAR 知识平台 v1.0.0  
> **系统描述**: PolarDB 智能知识平台 API — 企业数据管理语义操作系统

---

## 1. 系统概述

POLAR 知识平台是一个基于**本体论（Ontology）**的企业知识图谱管理系统。核心能力包括：

1. **数据集管理** — 创建和管理语义数据集
2. **本体建模** — 定义对象类型(Object Types)、链接类型(Link Types)、动作类型(Action Types)
3. **图谱可视化** — 2D/3D 交互式知识图谱浏览(G6引擎)
4. **LLM辅助建模** — 利用大模型自动从数据库Schema生成本体定义
5. **RAG知识库** — 集成RAGFlow完成文档解析、向量存储、智能问答
6. **权限管控** — 基于角色的访问控制(RBAC) + 行级/属性级安全(ACR)
7. **Skills扩展** — 可插拔的技能系统，支持自动化工作流
8. **多数据源同步** — 支持PostgreSQL/MySQL/Hive/Lindorm等数据源

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React SPA)                      │
│  Vite + React + Ant Design + AntV G6 + Zustand          │
│  + Markdown Renderer + PDF Viewer                       │
├─────────────────────────────────────────────────────────┤
│                   REST API (FastAPI)                     │
│  JWT Auth + RBAC + ACR + OpenAPI 3.1                    │
├─────────────────────────────────────────────────────────┤
│  核心后端服务              外部集成服务                    │
│  ┌──────────────┐    ┌──────────────────┐               │
│  │ PostgreSQL   │    │ RAGFlow v1       │               │
│  │ + Apache AGE │    │ (127.0.0.1:9380) │               │
│  │ (图存储)     │    └──────────────────┘               │
│  ├──────────────┤    ┌──────────────────┐               │
│  │ PolarDB PG   │    │ 阿里云百炼(Bailian)│              │
│  │ (文档引擎)   │    │ RAG/知识库API     │               │
│  └──────────────┘    └──────────────────┘               │
│  ┌──────────────┐    ┌──────────────────┐               │
│  │ 阿里云 OSS   │    │ LLM: 通义千问     │               │
│  │ (文件存储)   │    │ (qwen-plus)      │               │
│  └──────────────┘    └──────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 技术栈详解

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | React 18+ | Vite 构建，支持懒加载 |
| UI组件库 | Ant Design 5.x | 中文本地化 (zh-CN) |
| 状态管理 | Zustand | 支持 localStorage 持久化 |
| 图可视化 | AntV G6 | 2D/3D 知识图谱渲染 |
| HTTP客户端 | Axios 1.13.6 | baseURL="/api"，30秒超时 |
| 文档渲染 | Markdown Renderer | 支持 MD 编辑/预览 |
| PDF查看 | PDF.js | PDF 预览组件 |
| 后端框架 | FastAPI (Python) | OpenAPI 3.1.0 自动文档 |
| 认证 | JWT Bearer Token | Access Token + Refresh Token |
| 图数据库 | Apache AGE | PostgreSQL图扩展 |
| 文档检索引擎 | PostgreSQL GIN | 全文搜索 + 向量检索(混合模式) |
| RAG引擎 | RAGFlow v1 | 文档解析/Chunk/问答 |
| LLM | 通义千问 qwen-plus | 建模辅助/问答/解析 |

---

## 3. 功能模块详解

### 3.1 认证与用户系统

#### 登录页面
- URL: `/login`
- 紫色渐变背景，居中400px宽卡片
- 包含：系统标题、用户名输入框、密码输入框、登录按钮
- 页脚显示版权信息

#### 认证流程
- POST `/api/auth/login` — 用户名+密码 (form-urlencoded)
- 返回 `access_token` + `refresh_token` + `user` 对象
- Token 存储在 localStorage: `auth_access_token`, `auth_refresh_token`
- 自动刷新: 401时自动调用 `/api/auth/refresh`，失败则跳转 `/login`

#### 用户模型
```json
{
  "id": "UUID",
  "username": "string",
  "email": "string",
  "full_name": "string|null",
  "is_active": true,
  "is_superuser": true|false,
  "roles": ["admin"|"developer"|"viewer"],
  "groups": ["admins"|"developers"|"viewers"],
  "custom_attributes": {},
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_login": "datetime|null"
}
```

#### 角色与权限
| 角色 | 说明 |
|------|------|
| admin | 完全访问权限 |
| developer | 读写访问 |
| viewer | 只读访问 |

#### 用户组
- `admins` (管理员组)
- `developers` (开发者组)  
- `viewers` (观察者组)
- 支持父子层级（如子组 "fdsfsdaf" 父组为 "admins"）

### 3.2 前端导航结构

```
📊 概览 (Dashboard)
🤖 RAG 引擎
  ├── 📚 知识库管理     /ragflow/knowledge-base
  ├── 💬 对话助手       (Chat Assistant)
  ├── 🔍 内容检索       /ragflow/retrieval
  ├── 📊 RAG 评测       /rag-evaluation
  ├── ⚙️ 模型配置       (Model Config)
  ├── 🔧 服务配置       (Service Config)
  └── 🔒 权限管理       (RAG Permissions)
🔷 ONTOLOGY
  ├── 🗺️ 本体图谱       /ontology/graph
  ├── 📋 类型定义       /ontology/types
  ├── 📦 实例管理       (Object Management)
  ├── 🏗️ 数据管理（本体构建）
  │    ├── 🤖 LLM 建模   /ontology/modeling
  │    ├── ⚡ 快速建模   (Quick Modeling)
  │    ├── 🔄 结构变更   (Structure Changes)
  │    └── 🔗 数据同步   (Data Sync)
  ├── 📝 版本管理       (Version Management)
  └── 🔒 权限管理(FGAC)  (Object-level FGAC)
🔷 GRAPHRAG
  ├── 📚 知识库         (GraphRAG KB)
  ├── 📄 文档处理       /graphrag/documents
  ├── 🗺️ 知识图谱       (Knowledge Graph)
  ├── 💬 知识问答       (Knowledge Q&A)
  └── ⚙️ 模型配置       (Model Config)
⚡ SKILLS 管理           /skills
⚙️ 系统管理
  ├── 👤 用户管理       /admin/users
  ├── 🎭 角色管理       (Role Management)
  ├── 👥 用户组管理     (Group Management)
  ├── 🔑 令牌管理       (Token Management)
  ├── 📏 ACR 配置       (Access Control Rules)
  └── 🔧 系统配置       (System Config)
🔌 API 接口             (API Documentation)
```

### 3.3 数据集管理 (Datasets)

数据集的语义作用相当于"命名空间"或"知识空间"，每个数据集包含独立的本体定义、实例数据和图谱。

**API**: 
- `GET/POST /api/datasets` — 列出/创建数据集
- `GET/DELETE /api/datasets/{dataset_id}` — 查看/删除数据集

**数据模型**:
```json
{
  "dataset_id": "_ontology_xxx",  // UUID格式ID
  "display_name": "string",       // 显示名称
  "description": "string|null",   // 描述
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**前端页面**: `/datasets` — 数据集列表（表格+创建/删除操作）

### 3.4 本体建模 (Ontology Modeling)

这是平台最核心的功能模块，实现以下概念：

#### 3.4.1 Object Types（对象类型）

定义知识图谱中的**节点类型**，相当于关系数据库中的"表"。

**属性定义**:
```json
{
  "type_name": "string",     // 类型标识名 (英文)
  "display_name": "string",  // 显示名称 (中文)
  "description": "string",   // 业务描述
  "properties": [{
    "name": "string",        // 属性名
    "type": "string|number|datetime|boolean", // 属性类型
    "required": true|false,  // 是否必填
    "unique": true|false,    // 是否唯一
    "indexed": true|false,   // 是否索引
    "description": "string", // 属性说明
    "enum": null,            // 枚举值(可选)
    "format": null,          // 格式(可选)
    "metadata": null         // 元数据(可选)
  }],
  "fgac_config": null,       // 细粒度访问控制配置
  "compute_logic": null,     // 计算逻辑
  "source": null             // 数据来源
}
```

**示例**: 以"员工管理"数据集为例——
- `YuanGong` (员工): ygbh(编号), ygxm(姓名), rzrq(入职日期), ssbm(部门), sszw(职位)
- `JiNeng` (技能): jnbh(编号), jnmc(名称), jnlb(类别)
- `PeiXunKC` (培训课程): pxkcbh(编号), pxkcmc(名称), pxks(课时)
- `JiXiaoPG` (绩效评估): jxpgbh(编号), jxpgrq(日期), jxpgfs(分数)

**API**: 
- `GET/POST /api/datasets/{id}/ontology/object-types`
- `GET/PATCH/DELETE /api/datasets/{id}/ontology/object-types/{type_name}`
- `GET /api/datasets/{id}/ontology/object-types/{type_name}/dependencies`

#### 3.4.2 Link Types（链接类型）

定义节点之间的**边/关系**，有向边。

```json
{
  "link_name": "string",       // 链接标识名
  "display_name": "string",    // 显示名称
  "description": "string",     // 描述
  "source_type": "ObjectType", // 源节点类型
  "target_type": "ObjectType", // 目标节点类型
  "directed": true,            // 是否有向
  "properties": []             // 边属性(可取datetime/number/string)
}
```

**示例**:
- `yg_jn` (拥有技能): YuanGong → JiNeng [yyrq(日期), slcd(熟练程度)]
- `yg_jx` (获得绩效): YuanGong → JiXiaoPG
- `yg_pxkc` (参加培训): YuanGong → PeiXunKC [ksrq, jsrq, pxks, pxcj]

**API**:
- `GET/POST /api/datasets/{id}/ontology/link-types`
- `GET/PATCH/DELETE /api/datasets/{id}/ontology/link-types/{type_name}`

#### 3.4.3 Action Types（动作类型）

定义可执行的**操作/副作用**，通过 Webhook 触发。

```json
{
  "action_name": "string",          // 动作标识名
  "display_name": "string",         // 显示名称
  "target_type": "ObjectType",      // 目标对象类型
  "description": "string",
  "parameters": [],                 // 动作参数定义
  "webhook_url": "string",          // Webhook地址
  "method": "POST",                 // HTTP方法
  "headers": {},                    // 请求头
  "requires_confirmation": false,   // 是否需要人工确认
  "timeout_seconds": 30,            // 超时时间
  "effect_type": "create|update|delete"  // 副作用类型
}
```

**示例**: `fsxmyqyj` (发送项目邀请邮件) — 向员工发送邮件，Webhook到 `http://biaopu.cloud/api/mail/send`

**API**:
- `GET/POST /api/datasets/{id}/ontology/action-types`
- `GET/PATCH/DELETE /api/datasets/{id}/ontology/action-types/{type_name}`
- `POST /api/datasets/{id}/ontology/actions/{action_type}/execute`
- `POST /api/datasets/{id}/ontology/actions/{action_id}/confirm`
- `POST /api/datasets/{id}/ontology/actions/{action_id}/cancel`
- `POST /api/datasets/{id}/ontology/actions/{action_id}/report`
- `GET /api/datasets/{id}/ontology/actions/history`

#### 3.4.4 Objects（对象实例）

即知识图谱中的**具体节点数据**。

**API**:
- `GET/POST /api/datasets/{id}/ontology/objects/{object_type}`
- `GET/PATCH/DELETE /api/datasets/{id}/ontology/objects/{object_type}/{object_id}`
- `POST /api/datasets/{id}/ontology/objects/batch/create`

#### 3.4.5 Links（关系实例）

即知识图谱中的**具体边数据**。

**API**:
- `POST /api/datasets/{id}/ontology/links` (需要 link_type query参数)
- `GET /api/datasets/{id}/ontology/links/{link_type}`
- `DELETE /api/datasets/{id}/ontology/links/{link_type}`
- `GET /api/datasets/{id}/ontology/links/{link_type}/between`
- `POST /api/datasets/{id}/ontology/links/batch/create`

---

### 3.5 Auto Modeling（LLM辅助建模）

这是平台的**核心差异化功能**，利用LLM自动发现数据库Schema并生成本体定义。

#### 本体建模总流程

1. **创建数据集** — 在 ONTOLOGY 概览页面创建新 Dataset，作为本体的容器。
2. **生成本体定义** — 进入**数据管理**页面，选择 LLM 建模（推荐）或快速建模。
3. **审核与调整类型定义** — 进入**类型定义**页面，审核自动生成的对象类型、链接类型和动作类型。
4. **数据同步** — 配置数据同步任务，将源数据库数据按本体定义导入知识图谱。
5. **图谱探索与验证** — 通过**本体图谱**可视化验证建模结果。
6. **持续迭代** — 数据源结构变更时，通过**结构变更检测**更新本体定义和数据。

#### LLM 建模详细流程（三步向导）

**步骤一：连接配置**

配置数据源连接和LLM分析参数。数据库连接方式（三选一）：

| 连接方式 | 说明 | 适用场景 |
|---------|------|---------|
| 项目默认实例 | 使用后端配置的集群，仅需选择**源数据库名**和**Schema**。 | 数据源与平台在同一集群中。 |
| 数据库连接参数 | 手动输入**主机地址**、**端口**、**数据库**、**用户名**与**密码**。 | 数据源为外部独立数据库。 |
| DSN连接串 | 输入标准连接串（`postgresql://user:pass@host:port/db`）。 | 已有连接串的场景。 |

> 使用**数据库连接参数**或**DSN连接串**方式时，需先单击**测试连接**验证连通性。

参数说明：Schema、业务背景（可选）、输出语言、生成ActionType、高级选项（排除表、自定义LLM、宽表实体提取、分析超时）。

**步骤二：预览与精炼**

LLM分析完成后进入预览页面，展示生成的类型定义：
- **列表视图**：卡片形式分标签展示 ObjectType、LinkType、ActionType。
- **图视图**：可视化图谱展示类型关系结构。
- 支持编辑类型（JSON编辑器）、删除类型（级联删除）、图视图编辑。
- **编译检查**：验证类型名称唯一性、id属性、引用有效性，支持**自动修复**。

**步骤三：注册与数据同步**

- **注册**：验证通过后，系统依次创建 ObjectType、LinkType、ActionType，在图数据库中创建对应标签。
- **数据同步**：注册后自动触发同步，使用 merge（UPSERT）语义（不存在则 INSERT，存在则 UPDATE），按数据量自动选择同步/异步执行。

**API 端点**:
| 功能 | 端点 |
|------|------|
| 数据库列表 | `GET /api/datasets/{id}/ontology/modeling/databases` |
| Schema列表 | `GET /api/datasets/{id}/ontology/modeling/databases/{db}/schemas` |
| 表列表 | `POST /api/datasets/{id}/ontology/modeling/list-tables` |
| 表描述 | `POST /api/datasets/{id}/ontology/modeling/describe-table` |
| 连接测试 | `POST /api/datasets/{id}/ontology/modeling/test-connection` |
| LLM分析 | `POST /api/datasets/{id}/ontology/modeling/analyze` |
| 快速分析 | `POST /api/datasets/{id}/ontology/modeling/quick-analyze` |
| 变更检测 | `POST /api/datasets/{id}/ontology/modeling/detect-changes` |
| 本体变更检测 | `POST /api/datasets/{id}/ontology/modeling/detect-ontology-changes` |
| 精炼 | `POST /api/datasets/{id}/ontology/modeling/refine` |
| 验证 | `POST /api/datasets/{id}/ontology/modeling/validate` |
| 导入 | `POST /api/datasets/{id}/ontology/modeling/import` |
| 应用变更 | `POST /api/datasets/{id}/ontology/modeling/apply-changes` |
| 暂存区 | `GET/POST /api/datasets/{id}/ontology/modeling/staging` |
| 提交暂存 | `POST /api/datasets/{id}/ontology/modeling/staging/commit` |
| 丢弃暂存 | `POST /api/datasets/{id}/ontology/modeling/staging/discard` |
| 撤销操作 | `POST /api/datasets/{id}/ontology/modeling/staging/undo` |
| 批量撤销 | `POST /api/datasets/{id}/ontology/modeling/staging/batch-undo` |
| 版本列表 | `GET /api/datasets/{id}/ontology/modeling/versions` |
| 版本详情 | `GET /api/datasets/{id}/ontology/modeling/versions/{v_id}` |
| 更新版本说明 | `PATCH /api/datasets/{id}/ontology/modeling/versions/{v_id}/notes` |
| 比较版本 | `GET /api/datasets/{id}/ontology/modeling/versions/compare` |
| 回滚 | `POST /api/datasets/{id}/ontology/modeling/versions/{v_id}/rollback` |
| 同步配置 | `GET /api/datasets/{id}/ontology/modeling/sync-config` |
| 同步数据 | `POST /api/datasets/{id}/ontology/modeling/sync` |
| 同步状态 | `GET /api/datasets/{id}/ontology/modeling/sync-status/{task_id}` |
| 上传参考文档 | `GET/POST/DELETE /api/datasets/{id}/ontology/modeling/upload-reference` |
| 参考文档内容 | `GET /api/datasets/{id}/ontology/modeling/upload-reference/{file_id}` |

**支持的数据源类型**: PostgreSQL, MySQL, Hive (SparkSQL), HBase, Lindorm

---

### 3.6 图谱可视化 (Graph Visualization)

平台最核心的交互界面，基于 AntV G6 实现。

#### 功能特性:
- **双模式**: 2D 模式 和 3D 模式切换
- **布局算法**: 层次化、力导向、径向、圆形、网格、同心圆
- **搜索**: 图中搜索节点
- **深度控制**: 滑块控制展开深度(1-5层)
- **节点详情面板**: 右侧280px滑出面板显示节点属性、关联关系
- **工具栏**: 左侧图标工具栏（缩放、适应画布、布局切换等）
- **全屏模式**: 支持全屏查看
- **状态栏**: 底部统计栏显示节点/边统计
- **Tab切换**: 实体图谱 / 结构图谱 双视图
- **响应式**: 桌面端和移动端适配

#### CSS类名结构:
```
graph-view-container
├── view-mode-toggle (2D/3D切换)
├── graph-top-toolbar (顶部工具栏-搜索/操作)
├── graph-main-content
│   ├── graph-left-toolbar (左侧工具-深度/布局)
│   ├── graph-canvas-wrapper (画布区域)
│   └── graph-detail-panel (右侧详情面板)
└── graph-stats-bar (底部统计)
```

**API**:
- `GET /api/datasets/{id}/ontology/graph/stats` — 图谱统计
- `GET /api/datasets/{id}/ontology/graph/knowledge` — 知识图谱数据
- `GET /api/datasets/{id}/ontology/graph/neighbors/{obj_type}/{obj_id}` — 邻居节点
- `POST /api/datasets/{id}/ontology/graph/path` — 路径查询
- `POST /api/datasets/{id}/ontology/graph/traverse` — 图遍历
- `GET/POST /api/datasets/{id}/ontology/graph/graphs` — AGE图管理
- `POST /api/datasets/{id}/ontology/query/objects/search` — 对象搜索

---

### 3.7 RAG引擎 (RAGFlow集成)

RAG引擎提供文档解析、向量存储与知识问答能力。平台代理转发到RAGFlow v1 (http://127.0.0.1:9380)，同时支持阿里云百炼集成。

**典型使用流程**：
1. **管理员配置**：配置OSS、文档引擎和AI模型。
2. **创建知识库**：定义文档集合和切片参数。
3. **导入与解析**：上传文档并触发解析，系统切分为Chunk并生成向量嵌入。
4. **检索与问答**：通过检索测试验证召回效果，创建对话助手进行知识问答。
5. **Skill检索**：通过AI助手内置Skill直接检索知识库。

**角色权限**：
| 操作 | 所需角色 |
|------|---------|
| 查询知识库、检索、问答 | VIEWER及以上 |
| 创建知识库、上传或删除文档 | DEVELOPER及以上 |
| 配置模型、OSS、文档引擎 | ADMIN |

#### 3.7.1 管理员配置
- OSS配置：Storage Type, Access Key, Endpoint, Bucket等
- 文档引擎配置：PostgreSQL GIN / OpenSearch
- 绑定LLM与Embedding模型：模型厂商 + 模型的两层架构

#### 3.7.2 知识库管理
- CRUD 知识库
- 切片方法：General (Naive), Manual, Paper, QA, Table
- 权限：me / team

#### 3.7.3 文档导入与解析
- 支持格式：PDF, Word, PPT, Excel, TXT, Markdown, 图像
- 上传 → 触发解析 → 查看/修正切片
- 文档状态：pending → processing → preprocessed → processed / failed

#### 3.7.4 检索测试
- 选择知识库，输入问题，调整检索参数（Top K, 相似度阈值, 向量权重）
- 验证召回效果后再创建对话助手

#### 3.7.5 对话助手与问答
- 创建助手：关联知识库、配置模型参数（Temperature, Top-P, Top N, 空结果兜底回复）、系统提示词
- 对话：多轮对话 + 流式输出 + 引用溯源

#### 3.7.6 通过Skill检索
| Skill名称 | 能力 | 适用角色 |
|-----------|------|---------|
| polardb-kb-search-agent | 只读：列库、列文档、语义检索 | 普通用户 |
| polardb-kb-agent | 读写：管理知识库、上传/删除文档、修改切片、检索 | 管理员/运维 |

#### 3.7.7 GraphRAG
GraphRAG是基于图结构的知识增强检索系统，将文档内容解析为实体-关系图谱：
- **核心概念**：Workspace, Entity, Relation, Chunk
- **6种检索模式**：本地模式、全局模式、混合模式、混合检索（推荐）、朴素模式、绕过模式
- **默认实体类型**：organization, person, geo, event, category
- **API**：运行GraphRAG、追踪进度、取消

#### 3.7.8 RAPTOR
- `POST /api/ragflow/datasets/{id}/run_raptor` — 运行RAPTOR
- `GET /api/ragflow/datasets/{id}/trace_raptor` — 追踪进度
- `POST /api/ragflow/datasets/{id}/cancel_raptor` — 取消

#### 3.7.9 阿里云百炼(Bailian)集成
- 知识库 CRUD
- 文档上传/解析/管理
- Chunk管理
- 检索

#### 3.7.7 数据源同步
- 飞书文档同步: `POST /api/ragflow/feishu/sync`
- 钉钉文档导入
- OSS 文件导入

---

### 3.8 RAG 评测 (Evaluation)

**API**:
- `GET/POST /api/rag-evaluation/datasets` — 评测数据集管理
- `GET/DELETE /api/rag-evaluation/datasets/{id}` 
- `GET /api/rag-evaluation/datasets/{id}/cases` — 测试用例
- `POST /api/rag-evaluation/upload` — 上传评测数据
- `GET /api/rag-evaluation/upload/{id}/preview` — 预览
- `POST /api/rag-evaluation/upload/{id}/confirm` — 确认创建
- `GET/POST /api/rag-evaluation/runs` — 评测运行
- `GET /api/rag-evaluation/runs/{id}`
- `POST /api/rag-evaluation/runs/{id}/cancel`
- `GET /api/rag-evaluation/runs/{id}/results`
- `GET /api/rag-evaluation/runs/{id}/summary`
- `POST /api/rag-evaluation/compare` — 多次运行比较

---

### 3.9 Skills 系统

可插拔的技能扩展框架，支持上传/导入/克隆/启用/禁用。

**预设Skills (14个)**:
| Skill | 分类 | 说明 |
|-------|------|------|
| nuscenes-ontology-explorer | ops | nuScenes自动驾驶数据集图谱探索 |
| nuscenes-build | build | nuScenes JSON元数据建图 |
| av-clip-build | build | NVIDIA AV Clip数据导入 |
| csv-to-ontology | build | CSV文件智能导入本体图谱 |
| rdb-to-ontology | build | 关系数据库表结构→本体 |
| polardb-kb-search-agent | integration | PolarDB知识库语义检索(只读) |
| av-clip-query | ops | AV Clip查询与轨迹回放 |
| ontology-subgraph-search | ops | 子图检索与定位 |
| polardb-kb-agent | integration | PolarDB知识库完整管理 |
| ontology-data-build | build | 通用数据导入(JSON/CSV/Parquet) |
| polardb-chat-agent | integration | 对话助手问答代理 |
| ontology-ops-agent | ops | 运维故障排查(图遍历驱动) |
| tire-blowout-analysis | analyze | 轮胎爆胎风险分析 |
| nuscenes-query | ops | nuScenes图谱查询 |

**API**:
- `GET/POST /api/skills`
- `GET /api/skills/presets`
- `POST /api/skills/import-preset`
- `POST /api/skills/upload` — 上传skill zip包
- `GET/PATCH/DELETE /api/skills/{skill_id}`
- `POST /api/skills/{skill_id}/enable`
- `POST /api/skills/{skill_id}/disable`
- `POST /api/skills/{skill_id}/clone`
- `GET /api/skills/{skill_id}/download`
- `POST /api/skills/{skill_id}/regenerate` — 重新生成
- `POST /api/skills/datasets/{dataset_id}/generate` — 从本体生成技能

---

### 3.10 权限管控 (ACR - Access Control Rules)

细粒度的行级和属性级安全控制（当前全局关闭）。

**概念**:
- **ACR规则**: 定义对哪些对象类型的哪些用户/组施加访问限制
- **规则组**: 将多条规则组织为策略组
- **规则组绑定**: 将规则组绑定到特定的资源/用户
- **比较运算符**: eq, ne, in, not_in, intersects
- **用户属性**: user_id, username, groups, roles, custom:*

**配置项**:
- `acr_enabled`: 全局开关 (当前: false)
- `row_level_security`: 行级安全 (false)
- `property_level_security`: 属性级安全 (false)
- `userid_injection`: 用户ID注入 (true)
- `admin_bypass`: 管理员绕过 (true)
- `admin_roles`: ["admin"]
- `public_data_allowed`: 允许公共数据 (true)

---

### 3.11 系统管理

系统管理模块为管理员提供全局系统配置与运维管理功能，包含以下6个子模块：

| 子模块 | 说明 |
|--------|------|
| **用户管理** | 创建和维护用户账户，支持用户启用/禁用和自定义属性存储。 |
| **角色管理** | 定义和分配角色（admin/developer/viewer），支持角色层级体系。 |
| **用户组管理** | 创建用户分组，管理组成员，实现组级权限分配，支持父子层级。 |
| **令牌管理** | API Key（管理员级别）和个人令牌（用户级别），支持创建、撤销和加密存储。Token黑名单机制支持即时撤销。 |
| **ACR配置** | 定义和管理细粒度访问控制规则，配置规则与用户组的绑定关系。 |
| **系统配置** | 全局系统设置：数据库连接、文档引擎类型、对象存储(OSS)、系统级参数等。 |

#### API Key管理
- 用户自行管理: `GET/POST /api/api-keys`, `DELETE /api/api-keys/{id}`
- 管理员管理: `GET /api/admin/api-keys`, `DELETE /api/admin/api-keys/{id}`

#### Personal Access Token管理
- 用户自行管理: `GET/POST /api/personal-tokens`, `DELETE /api/personal-tokens/{id}`
- 管理员管理: `GET /api/admin/personal-tokens`, `DELETE /api/admin/personal-tokens/{id}`

#### Token管理 (管理员)
- `GET /api/admin/tokens` — 黑名单列表
- `GET /api/admin/tokens/stats` — 统计
- `DELETE /api/admin/tokens/{id}` — 撤销
- `DELETE /api/admin/tokens/user/{user_id}` — 撤销某用户所有Token

#### 系统配置
- `GET/POST /api/admin/system-config`
- `GET/PUT/DELETE /api/admin/system-config/{key}`

#### 文档引擎配置
- `GET /api/doc-engine/config`
- `POST /api/doc-engine/engine-type` — 切换引擎(postgresql/opensearch)
- `POST /api/doc-engine/pg/config` — PG配置
- `POST /api/doc-engine/pg/test` — 测试连接
- `POST /api/doc-engine/os/config` — OpenSearch配置
- `POST /api/doc-engine/os/test` — 测试连接

#### OSS配置
- `GET/POST /api/oss/config`
- `POST /api/oss/test`

---

### 3.12 异步任务管理

所有耗时操作(LLM分析、数据同步、GraphRAG等)均通过异步任务执行。

**API**:
- `GET /api/tasks/{task_id}` — 任务状态
- `GET /api/tasks/{task_id}/logs` — 执行日志
- `POST /api/tasks/{task_id}/cancel` — 取消任务

---

## 4. 数据模型汇总

### 4.1 统一API响应格式

```json
{
  "code": 0,            // 0=成功, 非0=业务错误
  "message": "success", // 消息
  "data": {},           // 实际数据
  "timestamp": "ISO8601"
}
```

管理员端点直接返回数据（无code/message包装）。

### 4.2 分页格式

```json
{
  "total": 100,
  "items": [],
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### 4.3 核心Schema清单

| Schema | 用途 |
|--------|------|
| DatasetCreate | 创建数据集 |
| ObjectTypeCreate/Update | 对象类型定义 |
| LinkTypeCreate/Update | 链接类型定义 |
| ActionTypeCreate/Update | 动作类型定义 |
| ObjectCreate/Update | 对象实例 |
| LinkCreate | 链接实例 |
| PropertyDefinition | 属性定义 |
| PropertyMetadata | 属性元数据 |
| FGACConfig | 细粒度访问控制配置 |
| SchemaAnalyzeRequest | LLM分析请求 |
| DetectChangesRequest | 变更检测请求 |
| ColumnMapping | 列映射 |
| BulkImportRequest | 批量导入 |
| SyncRequest | 数据同步请求 |
| StagedChangeRef | 暂存变更引用 |
| CommitStagingRequest | 提交暂存请求 |
| UndoStagedChangeRequest | 撤销暂存变更 |
| ApplyChangesRequest | 应用变更 |
| UpdateVersionNotesRequest | 更新版本说明 |
| SkillCreate/Update | 技能定义 |
| SkillGenerateRequest | 技能生成请求 |
| SkillGenerateLLMConfig | 技能LLM配置 |
| SkillImportPresetRequest | 导入预设技能 |
| SkillRegenerateRequest | 重新生成技能 |
| ACRConfigUpdate | ACR配置更新 |
| AccessRuleCreate/Update | ACR规则 |
| AdminRolesUpdate | 管理员角色更新 |
| GroupCreateRequest/UpdateRequest | 用户组管理 |
| PasswordChangeRequest | 密码修改 |
| APIKeyCreateRequest/Response | API Key管理 |
| EvaluationConfig | 评测配置 |
| EvaluationRunCreate | 评测运行 |
| CompareRunsRequest | 运行比较 |
| ConfirmUploadRequest | 确认上传 |
| RAGFlowDatasetCreate/Update/Delete | RAGFlow数据集 |

---

## 5. 前端页面清单

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录页 | 紫色渐变背景，居中卡片 |
| `/` | 概览/仪表盘 | 系统首页 |
| `/datasets` | 数据集列表 | 表格+CRUD |
| `/ontology/graph` | 本体图谱 | G6 2D/3D可视化 |
| `/ontology/types` | 类型定义 | Object/Link/Action Types管理 |
| `/ontology/types?tab=link` | 链接类型 | Link Types Tab |
| `/ontology/types?tab=action` | 动作类型 | Action Types Tab |
| `/ontology/modeling` | LLM建模 | AI辅助建模 |
| `/ragflow/knowledge-base` | 知识库管理 | RAGFlow知识库 |
| `/ragflow/retrieval` | 内容检索 | 知识检索 |
| `/graphrag/documents` | GraphRAG文档处理 | 文档管理 |
| `/query` | 查询 | 查询页面 |
| `/query/stream` | 流式查询 | 流式查询结果 |
| `/skills` | Skills管理 | 技能列表 |
| `/rag-evaluation` | RAG评测 | 评测管理 |
| `/admin/users` | 用户管理 | 用户CRUD |
| `/permissions/acr-rules` | ACR规则管理 | 规则列表 |
| `/health` | 健康检查 | 系统健康 |
| `/profile` | 个人中心 | 用户信息/密码修改 |
| `/documents` | 文档列表 | 文档管理 |
| `/documents/upload` | 文档上传 | 上传界面 |
| `/documents/scan` | 文档扫描 | 扫描处理 |
| `/documents/{doc_id}` | 文档详情 | 文档内容 |
| `/graphs` | 图谱列表 | 图谱管理 |
| `/graph/label/list` | 图标签列表 | G6标签管理 |
| `/parser` | 解析器 | 解析器管理 |
| `/pipeline/status` | 管道状态 | 管道监控 |
| `/doc-engine` | 文档引擎 | 引擎配置 |
| `/oss` | OSS配置 | 对象存储 |
| `/api-keys` | API Key管理 | 用户API Key |
| `/personal-tokens` | PAT管理 | Personal Access Token |
| `/workspaces` | 工作空间 | 工作区管理 |
| `/forbidden` | 403页面 | 权限不足 |

---

## 6. UI/UX设计规范

### 6.1 全局样式
- 字体: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif
- 背景色: `#f4f5f7`
- 滚动条: 6px宽, 轨道 `#f4f5f7`, 滑块 `#d1d5db`, hover `#9ca3af`
- Ant Design 中文本地化 (zh-CN)
- 侧边栏菜单: 多层级嵌套, 图标+文字

### 6.2 登录页
- 背景: `linear-gradient(135deg, #667eea, #764ba2)`
- 卡片: 400px宽, `box-shadow: 0 4px 12px rgba(0,0,0,0.15)`, `border-radius: 8px`
- 标题: 居中, 20px, font-weight 600
- 副标题: 居中, `#666`, margin-bottom 24px
- 页脚: 居中, `#999`, 12px, 上边框 `1px solid #f0f0f0`

### 6.3 图谱视图
- 3D模式: 深色主题 (`#1a1a2e` 背景)
- 2D模式: 浅色主题 (`#f5f5f5` 背景)
- 详情面板: 280px宽 (响应式: <1200px → 240px, <900px → 浮动面板)
- 左侧工具栏: 44px宽
- 底部状态栏: 填充式

### 6.4 通用UI组件
- Table: 分页、筛选、排序、展开/折叠、批量选择
- Form: 支持校验、可选标记、错误提示
- Modal: 确认/取消操作
- Upload: 上传中提示、移除、预览、下载
- Transfer: 搜索、穿梭选择
- Popconfirm: 二次确认
- Text: 可编辑、可复制、可展开/折叠
- Image: 预览
- QRCode: 过期/刷新/已扫描状态
- ColorPicker: 预设、透明、单色、渐变
- Tour: 引导步骤（上一步/下一步/完成）
- DatePicker/TimePicker: 日期时间选择

---

## 7. 安全与认证

### 7.1 JWT Token
- Access Token: 过期时间约15分钟
- Refresh Token: 过期时间约7天
- 存储: localStorage
- 传输: `Authorization: Bearer <token>` Header
- 黑名单机制: 服务端可撤销

### 7.2 密码安全
- 支持修改密码 (需验证当前密码)
- 管理员可重置用户密码
- 密码通过 form-urlencoded 传输（OAuth2 password grant 风格）

### 7.3 错误处理
| HTTP状态码 | 处理 |
|-----------|------|
| 401 | 自动刷新Token，失败则跳转/login |
| 403 | 显示"权限不足，请联系管理员授权" |
| 404 | 显示"Resource not found" |
| 409 | 静默忽略 |
| 422 | 解析验证错误详情并展示 |
| 500 | 显示"Server error" |
| Network Error | 显示"Network error - please check your connection" |

---

## 8. 环境与依赖

### 8.1 外部服务
| 服务 | 地址/版本 | 用途 |
|------|----------|------|
| PostgreSQL | pc-wz92jd0a28886r611.pg.polardb.rds.aliyuncs.com:5432 | 主数据库 |
| Apache AGE | (PG扩展) | 图存储 |
| PolarDB PG | knowledgedb_user / _rag_doc_db | 文档检索引擎 |
| RAGFlow | http://127.0.0.1:9380 (v1) | RAG引擎 |
| 阿里云百炼 | API | 知识库/检索(可选) |
| 阿里云OSS | (可选配置) | 文件存储 |
| 通义千问 | qwen-plus | LLM服务 |

### 8.2 文档检索引擎配置
- 引擎类型: PostgreSQL
- FTS引擎: GIN (中文全文搜索)
- 混合模式: weighted_fusion (向量+全文混合)
- FTS Top-N: 100
- Vector Top-N: 100

---

## 9. 实现建议

### 9.1 复刻优先级

**Phase 1 — 核心基础 (必须)**
1. FastAPI后端框架搭建 + JWT认证
2. 数据集 CRUD
3. Object Types / Link Types / Action Types 定义与CRUD
4. Objects / Links 实例管理
5. React前端框架 + Ant Design布局 + 侧边栏导航

**Phase 2 — 可视化与建模 (核心)**  
6. AntV G6 图谱可视化 (2D/3D)
7. LLM辅助建模（数据库Schema → Ontology）
8. 暂存区 + 版本管理
9. 图遍历与搜索

**Phase 3 — RAG集成 (增值)**
10. RAGFlow / 阿里云百炼集成
11. 文档解析/Chunk/问答
12. RAG评测框架
13. GraphRAG + RAPTOR

**Phase 4 — 权限与扩展 (完善)**
14. RBAC + ACR细粒度权限
15. Skills系统
16. API Key / PAT管理
17. 多数据源同步 (MySQL/Hive/Lindorm)

### 9.2 数据库设计要点
- 每个数据集独立Schema: `{dataset_id}_ontology`
- 每个数据集独立AGE图: `{dataset_id}_graph`
- 版本快照存储完整Ontology定义
- 暂存区使用JSON存储待提交变更

### 9.3 关键技术难点
- **G6图可视化**: 需要自定义节点/边样式、布局算法、3D渲染
- **LLM建模**: Prompt工程是核心，需要让LLM理解数据库Schema语义
- **暂存区设计**: 类似Git的add/commit/discard/undo机制
- **ACR**: 行级/属性级安全需要在SQL查询时动态注入条件
- **数据同步**: 增量同步 + 断点续传

---

## 10. 附录

### A. 完整API路径索引 (218个路径, ~279个端点)

详见 OpenAPI 3.1 规范文件: `/api/openapi.json` (496KB)

### B. 完整Schema定义索引 (206个Schema)

包括所有请求/响应模型、枚举类型、嵌套对象等。

### C. 图可视化布局算法
- 层次化 (Hierarchical): 从上到下/从下到上/从左到右/从右到左
- 力导向 (Force-Directed)
- 径向 (Radial)
- 圆形 (Circular)
- 网格 (Grid)
- 同心圆 (Concentric)

### D. Skills开发规范
Skills 包含 `SKILL.md` 描述文件，支持:
- 分类标签 (build/ops/integration/analyze)
- LLM配置（可指定模型、temperature等）
- 数据集关联
- 版本管理
- 导入/导出 (zip包)
