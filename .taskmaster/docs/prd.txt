# OntologyReady 2.0 — PRD 复刻文档（解耦版）

> **目标**: 1:1 复刻该 OntologyReady 2.0 网站系统，所有外部依赖通过抽象层解耦  
> **分析日期**: 2026-06-06  
> **原系统地址**: http://47.115.252.39:8080/  
> **设计原则**: 不绑定任何特定云厂商；LLM、RAG引擎、文档检索引擎、文件存储、图数据库均采用可替换的 Provider 接口设计

---

## 1. 系统概述

本平台是一个基于**本体论（Ontology）**的企业知识图谱管理系统。核心能力包括：

1. **数据集管理** — 创建和管理语义数据集（知识空间/命名空间）
2. **本体建模** — 定义对象类型(Object Types)、链接类型(Link Types)、动作类型(Action Types)
3. **图谱可视化** — 2D/3D 交互式知识图谱浏览（AntV G6 引擎）
4. **LLM 辅助建模** — 利用大模型自动从数据库 Schema 生成本体定义
5. **RAG 知识库** — 文档解析、向量存储、智能问答
6. **权限管控** — RBAC + 行级/属性级安全（ACR）
7. **Skills 扩展** — 可插拔的技能系统，支持自动化工作流
8. **多数据源同步** — 支持 PostgreSQL / MySQL / Hive / HBase / Lindorm 等数据源

---

## 2. 技术架构（解耦设计）

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                    前端 (React SPA)                           │
│  Vite + React + Ant Design + AntV G6 + Zustand               │
│  + Markdown Renderer + PDF Viewer                            │
├──────────────────────────────────────────────────────────────┤
│                  REST API (FastAPI)                           │
│  JWT Auth + RBAC + ACR + OpenAPI 3.1                         │
├──────────────────────────────────────────────────────────────┤
│                    抽象层 (Provider Interface)                │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ LLM ★    │ Embedding│ RAG ★    │ Doc Eng  │ File     │   │
│  │ DeepSeek │ ★ DeepSe │ Builtin  │ ★ PG GIN │ Store ★  │   │
│  │          │          │          │ +pvector │ Local FS │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│                           │ GraphDB ★ (Apache AGE)            │
├──────────────────────────────────────────────────────────────┤
│                    核心后端服务                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ PostgreSQL 14+ (主数据库)                              │    │
│  │ + pgvector (向量检索)  + Apache AGE (图存储)           │    │
│  │ + GIN 索引 (全文搜索)  + 业务元数据                     │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 文件存储: 本地磁盘 /data/files                          │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘

★ = 推荐默认方案，开箱即用，零额外服务依赖。
```

### 2.2 Provider 接口设计

所有外部依赖通过统一的 Provider 接口抽象，具体实现可在系统配置中切换。

#### 2.2.1 LLM Provider

```python
class LLMProvider(ABC):
    """大语言模型抽象接口"""
    
    @abstractmethod
    async def chat(self, messages: list[Message], **kwargs) -> ChatResponse:
        """对话补全"""
        ...
    
    @abstractmethod
    async def chat_stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """流式对话补全"""
        ...
    
    @abstractmethod
    def supports_function_calling(self) -> bool:
        """是否支持 Function Calling"""
        ...
    
    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """列出可用模型"""
        ...
```

**内置实现**:

| 实现 | 说明 | 适用场景 |
|------|------|---------|
| **`DeepSeekProvider` ★** | 对接 DeepSeek API (deepseek-chat, deepseek-reasoner) | **推荐默认方案** — 性价比最优，中文能力强 |
| `OpenAICompatibleProvider` | 通用 OpenAI 兼容 API — 覆盖通义千问/智谱/DeepSeek/MiniMax 等国产模型 | 备选国产模型 |
| `OpenAIProvider` | 对接 OpenAI API (GPT-4o, GPT-4 等) | 海外部署 / 英文场景 |
| `AnthropicProvider` | 对接 Anthropic API (Claude Opus, Sonnet, Haiku) | 复杂推理 / 长文本 |
| `OllamaProvider` | 对接 Ollama 本地服务 (Qwen, Llama, DeepSeek 本地版等) | 完全离线 / 数据不出网 |
| `VLLMProvider` | 对接 vLLM / TGI 自部署推理框架 | 自建高性能推理集群 |

> **★ = 推荐默认方案**。开发人员开箱即用，无需在多个等效方案间选择。

**配置示例**:
```json
{
  "llm": {
    "provider": "deepseek",
    "config": {
      "api_base": "https://api.deepseek.com/v1",
      "api_key": "${env:DEEPSEEK_API_KEY}",
      "default_model": "deepseek-chat",
      "default_params": {
        "temperature": 0.1,
        "max_tokens": 4096
      }
    }
  }
}
```

#### 2.2.2 Embedding Provider

```python
class EmbeddingProvider(ABC):
    """向量嵌入抽象接口"""
    
    @abstractmethod
    async def embed(self, texts: list[str], **kwargs) -> list[list[float]]:
        """文本向量化"""
        ...
    
    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        ...
```

**内置实现**: 

| 实现 | 说明 | 适用场景 |
|------|------|---------|
| **`DeepSeekEmbedding` ★** | DeepSeek 嵌入 API | **推荐默认方案** |
| `OpenAIEmbedding` | OpenAI text-embedding-3-small/large | 海外部署 |
| `OllamaEmbedding` | 本地 Ollama 嵌入模型 (nomic-embed-text, bge-large 等) | 完全离线 |
| `OpenAICompatibleEmbedding` | 通用 OpenAI 兼容嵌入 API (智谱/百度/通义等) | 备选国产模型 |

#### 2.2.3 RAG / 文档解析 Provider

```python
class RAGProvider(ABC):
    """RAG 引擎抽象接口 — 文档解析、Chunk、知识库管理"""
    
    @abstractmethod
    async def create_knowledge_base(self, name: str, config: dict) -> KbInfo:
        ...
    
    @abstractmethod
    async def upload_document(self, kb_id: str, file: bytes, filename: str) -> DocInfo:
        ...
    
    @abstractmethod
    async def parse_document(self, kb_id: str, doc_id: str) -> TaskInfo:
        ...
    
    @abstractmethod
    async def list_chunks(self, kb_id: str, doc_id: str) -> list[Chunk]:
        ...
    
    @abstractmethod
    async def search(self, kb_id: str, query: str, top_k: int = 10) -> list[SearchResult]:
        """知识库检索"""
        ...
    
    @abstractmethod
    async def chat(self, kb_id: str, question: str, history: list = None) -> ChatResponse:
        """基于知识库的问答"""
        ...
```

**内置实现**:

| 实现 | 说明 |
|------|------|
| **`BuiltinRAGProvider` ★** | **推荐默认方案** — 自研 RAG 引擎，基于 Document Engine + LLM + Embedding 三个 Provider 协作完成。无额外外部依赖，功能完整 |
| `RAGFlowProvider` | 对接 RAGFlow 开源版 — 适合需要更成熟文档解析能力的场景，需额外部署 RAGFlow 服务 |

> **开发指令**: 仅需实现 `BuiltinRAGProvider`。`RAGFlowProvider` 为远期可选项，Phase 1-3 不实现。

#### 2.2.4 Document Engine Provider

```python
class DocumentEngineProvider(ABC):
    """文档检索引擎抽象接口 — 全文搜索 + 向量检索"""
    
    @abstractmethod
    async def index_document(self, doc: Document, chunks: list[Chunk]) -> None:
        ...
    
    @abstractmethod
    async def search_fts(self, query: str, top_n: int = 100) -> list[SearchResult]:
        """全文搜索"""
        ...
    
    @abstractmethod
    async def search_vector(self, embedding: list[float], top_n: int = 100) -> list[SearchResult]:
        """向量相似度搜索"""
        ...
    
    @abstractmethod
    async def search_hybrid(self, query: str, embedding: list[float], ...) -> list[SearchResult]:
        """混合搜索 (全文+向量加权融合)"""
        ...
```

**内置实现**:

| 实现 | 说明 |
|------|------|
| **`PostgresDocumentEngine` ★** | **推荐默认方案** — PostgreSQL GIN 全文搜索 + pgvector 向量检索 + weighted_fusion 混合模式。零额外组件 |
| `OpenSearchEngine` | OpenSearch / Elasticsearch — 适合大规模全文搜索场景，需额外部署 |

> **开发指令**: 仅需实现 `PostgresDocumentEngine`。`OpenSearchEngine` 为远期可选项，Phase 1-3 不实现。

#### 2.2.5 File Storage Provider

```python
class FileStorageProvider(ABC):
    """文件存储抽象接口"""
    
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = None) -> str:
        ...
    
    @abstractmethod
    async def download(self, key: str) -> bytes:
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        ...
    
    @abstractmethod
    async def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        ...
```

**内置实现**:

| 实现 | 说明 |
|------|------|
| **`LocalFileStorage` ★** | **推荐默认方案** — 本地文件系统，开箱即用 |
| `MinIOStorage` | MinIO 对象存储 (S3 兼容) — 适合生产环境横向扩展 |

> **开发指令**: 仅需实现 `LocalFileStorage`。`MinIOStorage` 为远期可选项。

#### 2.2.6 Graph Database Provider

```python
class GraphDBProvider(ABC):
    """图数据库抽象接口"""
    
    @abstractmethod
    async def create_graph(self, graph_name: str) -> None:
        ...
    
    @abstractmethod
    async def add_node(self, graph_name: str, label: str, properties: dict) -> str:
        ...
    
    @abstractmethod
    async def add_edge(self, graph_name: str, source_id: str, target_id: str,
                       edge_type: str, properties: dict = None) -> None:
        ...
    
    @abstractmethod
    async def get_neighbors(self, graph_name: str, node_id: str,
                            depth: int = 1) -> Subgraph:
        ...
    
    @abstractmethod
    async def traverse(self, graph_name: str, start_node: str, **params) -> TraversalResult:
        ...
```

**内置实现**:

| 实现 | 说明 |
|------|------|
| **`AGEGraphDB` ★** | **推荐默认方案** — Apache AGE (PostgreSQL 图扩展)，与主数据库共用实例，零额外运维 |
| `Neo4jGraphDB` | Neo4j 社区版 — 适合复杂图查询/大规模图数据场景 |

> **开发指令**: 仅需实现 `AGEGraphDB`。`Neo4jGraphDB` 为远期可选项。

---

### 2.3 完整技术栈（含推荐方案）

| 层级 | 技术 | 推荐方案（开箱即用） | 说明 |
|------|------|---------------------|------|
| 前端框架 | React 18+ | — | Vite 构建，支持懒加载 |
| UI 组件库 | Ant Design 5.x | — | 中文本地化 (zh-CN) |
| 状态管理 | Zustand | — | 支持 localStorage 持久化 |
| 图可视化 | AntV G6 | — | 2D/3D 知识图谱渲染 |
| HTTP 客户端 | Axios | — | baseURL="/api" |
| 后端框架 | FastAPI (Python) | — | OpenAPI 3.1 自动文档 |
| 认证 | JWT Bearer Token | — | Access Token + Refresh Token |
| 主数据库 | PostgreSQL 14+ | — | 业务数据 + 元数据存储 |
| LLM | _Provider 模式_ | **DeepSeek** (deepseek-chat) | 另可选 OpenAI / Ollama / vLLM |
| Embedding | _Provider 模式_ | **DeepSeek Embedding** | 另可选 OpenAI / Ollama / 兼容 API |
| RAG 引擎 | _Provider 模式_ | **BuiltinRAGProvider** (自研) | 另可选 RAGFlow |
| 文档检索引擎 | _Provider 模式_ | **PostgreSQL GIN + pgvector** | 另可选 OpenSearch |
| 图存储 | _Provider 模式_ | **Apache AGE** (PG 扩展) | 另可选 Neo4j |
| 文件存储 | _Provider 模式_ | **本地文件系统** | 另可选 MinIO |

---

## 3. 功能模块详解

### 3.1 认证与用户系统

#### 登录页面
- URL: `/login`
- 紫色渐变背景，居中 400px 宽卡片
- 包含：系统标题、用户名输入框、密码输入框、登录按钮
- 页脚显示版权信息

#### 认证流程
- POST `/api/auth/login` — 用户名 + 密码 (form-urlencoded)
- 返回 `access_token` + `refresh_token` + `user` 对象
- Token 存储在 localStorage: `auth_access_token`, `auth_refresh_token`
- 自动刷新: 401 时自动调用 `/api/auth/refresh`，失败则跳转 `/login`

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
- 支持父子层级嵌套

---

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

---

### 3.3 数据集管理 (Datasets)

数据集语义上相当于"命名空间"或"知识空间"，每个数据集包含独立的本体定义、实例数据和图谱。

**数据模型**:
```json
{
  "dataset_id": "_ontology_xxx",
  "display_name": "string",
  "description": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**API**: `GET/POST /api/datasets`, `GET/DELETE /api/datasets/{dataset_id}`

---

### 3.4 本体建模 (Ontology Modeling)

平台最核心的功能模块。

#### 3.4.1 Object Types（对象类型）

定义知识图谱中的**节点类型**，相当于关系数据库中的"表"。

```json
{
  "type_name": "string",
  "display_name": "string",
  "description": "string",
  "properties": [{
    "name": "string",
    "type": "string|number|datetime|boolean",
    "required": true|false,
    "unique": true|false,
    "indexed": true|false,
    "description": "string",
    "enum": null,
    "format": null,
    "metadata": null
  }],
  "fgac_config": null,
  "compute_logic": null,
  "source": null
}
```

**示例**（员工管理场景）：
- `YuanGong` (员工): ygbh, ygxm, rzrq, ssbm, sszw
- `JiNeng` (技能): jnbh, jnmc, jnlb
- `PeiXunKC` (培训课程): pxkcbh, pxkcmc, pxks
- `JiXiaoPG` (绩效评估): jxpgbh, jxpgrq, jxpgfs

#### 3.4.2 Link Types（链接类型）

节点之间的**有向边/关系**：

```json
{
  "link_name": "string",
  "display_name": "string",
  "description": "string",
  "source_type": "ObjectType",
  "target_type": "ObjectType",
  "directed": true,
  "properties": []
}
```

**示例**:
- `yg_jn` (拥有技能): YuanGong → JiNeng [yyrq, slcd(熟练程度)]
- `yg_jx` (获得绩效): YuanGong → JiXiaoPG
- `yg_pxkc` (参加培训): YuanGong → PeiXunKC [ksrq, jsrq, pxks, pxcj]

#### 3.4.3 Action Types（动作类型）

定义可执行的**操作/副作用**，通过 Webhook 触发：

```json
{
  "action_name": "string",
  "display_name": "string",
  "target_type": "ObjectType",
  "description": "string",
  "parameters": [],
  "webhook_url": "string",
  "method": "POST",
  "headers": {},
  "requires_confirmation": false,
  "timeout_seconds": 30,
  "effect_type": "create|update|delete"
}
```

#### 3.4.4 Objects & Links（实例数据）

知识图谱中的具体节点和关系，支持 CRUD 和批量操作。

---

### 3.5 Auto Modeling（LLM 辅助建模）

**核心差异化功能**。利用 LLM 自动发现数据库 Schema 并生成本体定义。

#### 本体建模总流程

完整的本体建模流程包括以下步骤：
1. **创建数据集** — 在 ONTOLOGY 概览页面创建新 Dataset，作为本体的容器。
2. **生成本体定义** — 进入**数据管理**页面，选择 LLM 建模（推荐）或快速建模。
3. **审核与调整类型定义** — 进入**类型定义**页面，审核自动生成的对象类型、链接类型和动作类型。
4. **数据同步** — 配置数据同步任务，将源数据库数据按本体定义导入知识图谱。
5. **图谱探索与验证** — 通过**本体图谱**可视化验证建模结果。
6. **持续迭代** — 数据源结构变更时，通过**结构变更检测**更新本体定义和数据。

#### LLM 建模（推荐）：三步向导式交互

LLM 建模采用三步向导，引导用户完成从数据库 Schema 到本体定义的自动生成与注册。

##### 步骤一：连接配置

配置数据源连接和 LLM 分析参数。数据库连接方式（三选一）：

| 连接方式 | 说明 | 适用场景 |
|---------|------|---------|
| 项目默认实例 | 使用后端配置的 PostgreSQL 集群，仅需选择**源数据库名**和**Schema**。 | 数据源与平台在同一集群中。 |
| 数据库连接参数 | 手动输入**主机地址**、**端口**、**数据库**、**用户名**与**密码**。 | 数据源为外部独立数据库。 |
| DSN 连接串 | 输入标准 PostgreSQL 连接串（`postgresql://user:pass@host:port/db`）。 | 已有连接串的场景。 |

> 使用**数据库连接参数**或**DSN 连接串**方式时，需先单击**测试连接**验证连通性。

**参数说明**：

| 参数 | 说明 |
|------|------|
| Schema | 要分析的数据库 Schema，默认为 `public`，系统自动列出可用 Schema。 |
| 业务背景（可选） | 用自然语言描述业务领域，帮助 LLM 更准确理解表结构的业务含义。 |
| 输出语言 | 生成的 display_name 和 description 使用的语言（中文/英文）。 |
| 生成 ActionType | 是否让 LLM 为每个实体推荐可执行的业务操作。 |
| **高级选项** | |
| 排除表 | 逗号分隔的表名模式（支持通配符），排除不需要建模的表。 |
| 自定义 LLM 配置 | 可指定自定义的 LLM 模型名称、API Key 和 Base URL。 |
| 宽表实体提取 | 对宽表中的字段进行实体拆分，生成独立的 ObjectType。 |
| 分析超时时间 | LLM 分析的超时时间设置（默认 5 分钟），复杂 Schema 可适当延长。 |

配置完成后，单击**开始分析**。系统依次执行：连接数据库 → 提取表和列元数据及样本数据 → 调用 LLM 分析生成类型定义。

> LLM 建模仅用于初次建模。如果当前数据集已存在 Ontology 定义，系统提示使用**结构变更检测**进行增量更新。

##### 步骤二：预览与精炼

LLM 分析完成后自动进入预览页面，展示生成的全部类型定义。

**查看方式**：
- **列表视图**：以卡片形式分标签展示 ObjectType、LinkType、ActionType。
- **图视图**：以可视化图谱方式展示类型之间的关系结构。

**编辑操作**：
- **编辑类型**：单击卡片上的编辑按钮，在 JSON 编辑器中直接修改类型定义。
- **删除类型**：支持级联删除。删除 ObjectType 时自动移除引用该类型的 LinkType 和 ActionType。
- **从图视图编辑**：在图视图模式下可直接选中节点或边进行编辑。

**编译检查**：单击**编译检查**对当前定义进行完整性验证，检查项包括类型名称唯一性、是否包含 `id` 属性、LinkType 引用的有效性等。验证支持**自动修复**功能，可一键修复部分常见问题。

##### 步骤三：注册与数据同步

确认本体定义无误后，执行注册和数据同步。

**注册本体定义**：
1. 系统在注册前自动执行验证，确保所有类型定义的格式和引用关系正确。
2. 确认验证通过后，单击**注册**将本体定义批量导入到系统中。
3. 系统按顺序创建 ObjectType、LinkType 和 ActionType，并在图数据库中创建对应的顶点标签和边标签。

**数据同步**：
注册完成后，系统自动触发数据同步任务，将源数据库中的数据按照本体定义导入到知识图谱中。数据同步使用 **merge（UPSERT）语义**：
- 如果目标实例不存在，则新建（INSERT）。
- 如果目标实例已存在，则更新（UPDATE）。

根据 ID 防止重复数据。数据量较小时同步执行，数据量较大时自动转为异步后台任务。

#### 快速建模

基于数据库表结构直接映射生成本体定义（每张表对应一个 ObjectType），适用于结构简单、映射明确的场景。无需 LLM 参与，速度快。

#### 结构变更检测与持续迭代

当数据源 Schema 发生变更时：
1. 进入**数据管理** > **结构变更检测**，系统自动对比当前 Schema 与已注册 Ontology 定义的差异。
2. 审核差异清单，选择需要应用变更的部分。
3. 增量更新本体定义和数据。

#### 暂存区 (Staging) 与版本管理

- **暂存区**: 类 Git 的变更管理，支持 staged / commit / discard / undo 操作。
- **版本管理**: 每次变更创建版本快照，支持版本对比分析和回滚到任意历史版本。

#### LLM Provider

Auto Modeling / RAG 问答 / Skills 执行均依赖 LLM Provider 抽象接口。系统默认使用 **DeepSeek**，管理员可在系统配置界面切换为其他 Provider。

---

### 3.6 图谱可视化 (Graph Visualization)

基于 AntV G6 实现，平台最核心的交互界面。

#### 功能特性:
- **双模式**: 2D / 3D 自由切换
- **布局算法**: 层次化、力导向、径向、圆形、网格、同心圆
- **搜索**: 图内节点搜索与定位
- **深度控制**: 滑块控制展开深度（1-5 层）
- **详情面板**: 右侧 280px 滑出面板显示节点属性、关联关系
- **工具栏**: 缩放、适应画布、布局切换、导出
- **全屏模式**: 一键全屏
- **状态栏**: 底部节点/边统计
- **Tab 切换**: 实体图谱 / 结构图谱
- **响应式**: 桌面端和移动端自适应

**图数据 API**:
- `GET /api/datasets/{id}/ontology/graph/stats` — 图谱统计
- `GET /api/datasets/{id}/ontology/graph/knowledge` — 知识图谱数据
- `GET /api/datasets/{id}/ontology/graph/neighbors/{obj_type}/{obj_id}` — 邻居节点
- `POST /api/datasets/{id}/ontology/graph/path` — 路径查询
- `POST /api/datasets/{id}/ontology/graph/traverse` — 图遍历
- `POST /api/datasets/{id}/ontology/query/objects/search` — 对象搜索

---

### 3.7 RAG 引擎

RAG（Retrieval-Augmented Generation）引擎通过 Provider 接口抽象，默认提供**自研 Builtin 实现**。功能涵盖管理员配置、知识库管理、文档导入与解析、检索测试、对话问答和 Skill 检索。

RAG 的典型使用流程如下：
1. **管理员配置** — 配置对象存储（OSS）、文档引擎和 AI 模型，完成平台初始化。
2. **创建知识库** — 创建知识库，定义文档集合的组织方式和切片参数。
3. **导入与解析** — 上传文档并触发解析，系统将文档切分为文本块（Chunk）并生成向量嵌入。
4. **检索与问答** — 通过检索测试验证召回效果，然后创建对话助手进行知识问答。
5. **Skill 检索** — 通过 AI 助手内置 Skill 直接检索知识库。

不同角色的操作权限：
| 操作 | 所需角色 |
|------|---------|
| 查询知识库、检索、问答 | VIEWER 及以上 |
| 创建知识库、上传或删除文档、触发解析 | DEVELOPER 及以上 |
| 配置模型、OSS、文档引擎、资源授权 | ADMIN |

#### 3.7.1 管理员配置

以下配置仅需管理员（ADMIN）在平台初次部署后执行一次，通过**系统管理 > 系统配置**完成：

**配置对象存储 (OSS / File Storage)**：
RAG 引擎使用 File Storage Provider（默认 `LocalFileStorage`）保存原始文件、解析中间产物和切片图片。管理员可在**服务配置**页面的**对象存储配置**面板中配置：
- Storage Type（本地 / MinIO / S3）
- Access Key / Secret Key
- Endpoint URL / Region / Bucket
- 单击**测试连接**验证配置，然后**保存配置**。

**配置文档引擎**：
文档引擎用于保存切片、向量和全文索引。支持两种引擎类型：
- **PostgreSQL**（默认，无需额外部署）：GIN 全文搜索 + pgvector 向量检索 + weighted_fusion 混合模式
- **OpenSearch**（可选，已购买时使用）

**配置 LLM 与 Embedding 模型**：
RAG 引擎至少需要 Embedding 模型（向量化切片）和 Chat LLM（对话问答）。通过**模型配置**页面：新增模型厂商 → 导入自定义模型 → 设置默认模型（LLM / Embedding / VLM 可选）。

> 配置完成后通过 API 验证各组件状态：`GET /api/ragflow/status`、`GET /api/ragflow/tenant_info`、`POST /api/oss/test`、`POST /api/doc-engine/pg/test`。

#### 3.7.2 创建知识库

1. 在左侧菜单中，选择**RAG 引擎 > 知识库管理**。
2. 单击**新建知识库**，配置名称、描述、切片方法（General/Manual/Paper/QA/Table）、嵌入模型（留空则跟随租户默认）和权限（me/team）。
3. 单击**创建**。列表中的 ID 即为后续 API 使用的 `dataset_id`（形如 `ds-abc123`）。

#### 3.7.3 导入文档与解析

**支持的文档格式**: PDF, Word (.doc/.docx), PPT (.ppt/.pptx), Excel (.xls/.xlsx), TXT, Markdown (.md), 图像 (JPG/PNG 等)

**上传文档**：
1. 在知识库列表中进入**文档管理**页面。
2. 单击**上传**，拖拽或选择文档文件。
3. 系统自动开始文档处理流程：解析 → 分块 → 图谱构建 → 状态更新。

**触发解析**：
1. 勾选需要解析的文档（支持全选）。
2. 单击**开始解析**。
3. 解析状态依次为：待解析 → 解析中 → 已完成（或失败）。

**查看与修正切片**：
1. 单击目标文档，查看分块后的文本块列表。
2. 对每条切片可执行：编辑纠错、启用/禁用、新增 chunk。

**文档处理状态**：
| 状态 | 说明 |
|------|------|
| `pending` | 文档已上传，等待系统处理。 |
| `processing` | 文档正在处理中（解析和分块操作）。 |
| `preprocessed` | 文档预处理完成，正在进行图谱构建。 |
| `processed` | 文档处理完成，实体和关系已提取到知识图谱中。 |
| `failed` | 文档处理失败，可查看日志了解原因并重新处理。 |

**参数设置**：
| 参数 | 可选值 | 默认值 | 说明 |
|------|-------|--------|------|
| 解析器 | `mineru`, `docling`, `paddleocr` | `mineru` | MinerU 适合复杂排版，Docling 适合结构化格式，PaddleOCR 适合纯图片文档。 |
| 解析方式 | `auto`, `txt`, `ocr` | `auto` | `auto` 自动识别，`txt` 纯文本提取，`ocr` 光学字符识别。 |
| 分块大小 | 整数 | 1200 | 每个文本块的最大字符数。 |
| 分块重叠 | 整数 | 100 | 相邻文本块之间的重叠字符数。 |

#### 3.7.4 检索测试

在创建对话助手前，先通过检索测试确认文档能被正确召回。

1. 选择**RAG 引擎 > 内容检索**。
2. 选择一个或多个知识库，输入问题，单击**检索**。
3. 调整检索参数：Top K（默认 10）、相似度阈值（默认 0.2）、向量权重（默认 0.3）、元数据过滤等。
4. **判读标准**：
   - Top-3 命中切片都能回答问题 → 质量合格，可创建对话助手。
   - Top-3 偏离但 Top-10 有正确结果 → 调高 Top K 或启用 Rerank。
   - 全部不相关 → 检查切片质量或调整切片参数。

#### 3.7.5 对话助手与问答

**创建助手**：
1. 选择**RAG 引擎 > 对话助手**，单击**新建助手**。
2. 配置基础信息（名称、头像、关联知识库）、模型参数（Temperature 0.1、Top-P 0.3、相似度阈值、Top N 6、空结果兜底回复）、系统提示词（使用 `{{knowledge}}` 变量引用检索结果）。
3. 单击**创建**。

**发起对话**：
1. 在助手列表中单击目标助手，进入对话视图。
2. 新建或选择历史会话。
3. 输入问题，系统以流式方式实时展示回答（Enter 发送，Shift+Enter 换行）。
4. 每条回答末尾的引用标记可展开查看命中切片与原文链接。

#### 3.7.6 通过 Skill 检索

平台内置两个预置 Skill，可让 AI 助手直接访问知识库：

| Skill 名称 | 能力 | 适用角色 |
|-----------|------|---------|
| 知识库检索智能代理（polardb-kb-search-agent） | 只读：列库、列文档、语义检索 | 普通用户 |
| 知识库智能代理（polardb-kb-agent） | 读写：管理知识库、上传/删除文档、修改切片、检索 | 管理员/运维 |

管理员在**SKILLS 管理 > 导入预设**中启用对应 Skill 后，AI 助手自动获得调用知识库检索的能力。

#### 3.7.7 BuiltinRAGProvider 实现架构

自研 RAG 引擎由以下组件协作完成：

```
┌──────────────────────────────────────────────────────────┐
│                   BuiltinRAGProvider                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ 文档解析      │  │ Chunk 策略   │  │ 检索/问答     │  │
│  │              │  │              │  │               │  │
│  │ ├─ PDF       │  │ ├─ 固定大小  │  │ ├─ 全文检索   │  │
│  │ ├─ Word      │  │ ├─ 按段落    │  │ ├─ 向量检索   │  │
│  │ ├─ Markdown  │  │ ├─ 按标题    │  │ ├─ 混合检索   │  │
│  │ ├─ TXT       │  │ ├─ 语义分块  │  │ └─ LLM 问答   │  │
│  │ ├─ HTML      │  │ └─ 自定义    │  │               │  │
│  │ └─ CSV/Excel │  │              │  │               │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│                                                          │
│  依赖: DocumentEngine + Embedding + LLM (全部可替换)      │
└──────────────────────────────────────────────────────────┘
```

#### 3.7.8 RAGFlowProvider（可选外部方案）

对接 [RAGFlow 开源版](https://github.com/infiniflow/ragflow)。远期可选，Phase 1-3 不实现。

### 3.8 GraphRAG

GraphRAG 是基于图结构的知识增强检索系统，将文档内容解析为实体-关系图谱，以图谱作为检索增强的基础，使 AI 能够回答跨文档、跨章节的复杂语义问题。

#### 核心概念

| 概念 | 说明 |
|------|------|
| Workspace（工作空间） | GraphRAG 的顶层组织单元，对应一套独立的文档集合和知识图谱，不同 Workspace 之间数据相互隔离。 |
| 实体（Entity） | 从文档中提取的具有特定类型的知识节点，例如人物、组织、地点、事件等。 |
| 关系（Relation） | 连接两个实体的语义边，描述实体之间的关联关系。 |
| 文本块（Chunk） | 文档经过分块处理后生成的文本片段，是图谱构建和检索的基础数据单元。 |

#### 处理流程

```
文档解析与分块 → 知识图谱构建 → 多模式检索与问答
```
1. **文档解析与分块**：上传文档后，系统通过解析引擎提取文字、表格和图像，并按分块参数将文本切分为多个文本块，每个文本块生成向量嵌入。
2. **知识图谱构建**：系统调用 LLM 对文本块进行实体抽取和关系抽取，写入知识图谱（基于 Apache AGE 图存储）。
3. **多模式检索与问答**：提问时根据选择的检索模式从知识图谱和向量库中召回相关上下文，由 LLM 生成回答。

#### 知识库

工作空间（Workspace）管理：
- **创建工作空间**：配置名称、解析参数（解析器类型、解析方式、分块大小、分块重叠）
- **切换工作空间**：将当前活跃工作空间切换为目标空间
- **删除工作空间**：同时删除该空间下所有文档、知识图谱和关联数据（不可恢复）
- **默认工作空间**：系统首次启动时自动创建名为 `default` 的默认工作空间

#### 文档处理

**支持的文档格式**：PDF, Word (.doc/.docx), PPT (.ppt/.pptx), Excel (.xls/.xlsx), TXT, Markdown (.md), 图像 (JPG/PNG 等)

**文档处理状态**：
| 状态 | 说明 |
|------|------|
| `pending` | 文档已上传，等待系统处理。 |
| `processing` | 文档正在处理中（解析和分块操作）。 |
| `preprocessed` | 文档预处理完成，正在进行图谱构建。 |
| `processed` | 文档处理完成，实体和关系已提取到知识图谱中。可用于知识问答。 |
| `failed` | 文档处理失败。可查看日志了解失败原因并重新处理。 |

**文档管理操作**: 查看执行日志、查看分块详情、重新处理失败文档、删除文档。

**解析器选择建议**:
| 解析器 | 适用场景 | 说明 |
|--------|---------|------|
| MinerU | 复杂排版文档 | 多栏布局、表格嵌套、图文混排，版面分析能力强。 |
| Docling | 结构化格式文档 | Word、PPT、Excel 等，保留文档层级和格式信息。 |
| PaddleOCR | 纯图片文档 | 扫描件、截图等，通过 OCR 识别文字内容。 |

#### 知识图谱可视化

以可视化方式展示文档中提取的实体和关系网络：

**默认实体类型**：
| 实体类型 | 说明 |
|----------|------|
| `organization` | 组织机构（公司、部门、团队等） |
| `person` | 人物（作者、负责人、参与者等） |
| `geo` | 地理位置（国家、城市、地区等） |
| `event` | 事件（项目启动、版本发布、会议等） |
| `category` | 类别（技术领域、产品分类等） |

**图谱交互操作**:
- **缩放**：鼠标滚轮调整显示比例
- **平移**：拖动画布移动可视区域
- **点击高亮**：单击实体节点高亮显示该实体及其直接关联的实体和关系
- **标签筛选**：按实体类型筛选显示的实体
- **调整显示规模**：深度（1-5 层）、节点数（建议 300 以内，保证流畅体验）
- **搜索实体**：输入实体名称定位并高亮匹配节点

#### 知识问答

提供基于图谱增强的对话式问答功能，支持多轮对话。

**6 种检索模式**：
| 模式 | 适用场景 | 说明 |
|------|---------|------|
| **本地模式** | 具体细节查询 | 基于局部图谱结构检索，查询特定实体的属性、关系等细节信息。 |
| **全局模式** | 宏观摘要类问题 | 基于全局图谱结构进行检索和汇总，适合跨文档综合分析的宏观问题。 |
| **混合模式** | 综合性问题 | 结合 local 和 global 两种模式的检索结果，兼顾细节和全局视角。 |
| **混合检索** | 通用场景（推荐） | 融合图谱检索和向量检索，在大多数问答场景下能获得最佳效果。 |
| **朴素模式** | 简单关键词匹配 | 纯向量检索模式，不使用图谱增强。适合简单关键词匹配，响应速度快。 |
| **绕过模式** | 纯大模型对话 | 跳过所有检索，直接使用大语言模型回答。适合与文档内容无关的通用问题。 |

**问答操作**：
1. 选择**GraphRAG > 知识问答**。
2. 确认当前工作空间并选择检索模式（推荐混合检索）。
3. 输入问题，系统以流式方式实时展示回答。
4. 支持多轮对话，系统结合上下文提供更准确的回答。
5. 单击**清空对话**清除当前会话上下文。

**引用来源**：每条回答标注引用标记，可展开查看原始文档内容。

#### 模型配置

GraphRAG 使用 **模型提供商 + 模型** 的两层配置架构，模型 ID 格式为 `模型名@提供商名`。

**4 种模型类型**：
| 模型类型 | 是否必选 | 说明 |
|----------|---------|------|
| LLM | 是 | 大语言模型，用于实体提取、关系识别、知识问答等核心任务。 |
| Embedding | 是 | 文本向量化模型，支持语义相似度检索。 |
| Rerank | 否 | 重排序模型，对初步检索结果精排，提升检索质量。 |
| VLM | 否 | 视觉语言模型，处理包含图像的文档内容。 |

**核心概念**:
- **模型提供商（Factory）**: 模型的来源平台，每个提供商持有 API Key 和可选的 Base URL。系统预置 30+ 主流提供商。
- **模型（Model）**: 挂载在提供商下的具体模型实例，包含名称、类型和最大 Token 数。
- **API Key 同步**: 修改提供商的 API Key 后，该提供商下所有已添加模型的密钥自动同步更新。

**主要的模型提供商**：Tongyi-Qianwen, OpenAI, DeepSeek, ZHIPU-AI, Ollama, Azure-OpenAI, Bedrock 等。

**常见问题排查**：
| 问题现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| 文档状态持续为 `pending` | 未配置默认 LLM 或 Embedding 模型 | 确认已正确配置并设置默认模型。 |
| API Key invalid | API 密钥无效或已过期 | 检查密钥并验证连接。 |
| Connection timeout | 网络连接超时 | 检查网络连通性。 |
| Model not found | 模型名称错误或不在支持列表中 | 确认拼写并在可用列表检查。 |

---

### 3.9 RAG 评测 (Evaluation)

评测框架用于衡量 RAG 回答质量。

**核心流程**:
1. 创建评测数据集（问题 + 参考答案）
2. 上传评测数据文件或手动创建
3. 发起评测运行
4. 获取评测结果（逐条 + 汇总）
5. 多次运行对比

**评测指标**: 答案准确性、召回率、引用准确率、响应时间

---

### 3.10 Skills 系统

可插拔的技能扩展框架，每个 Skill 是一个独立的自动化工作流包。用于定义和管理 AI Agent 可调用的操作技能。

**核心功能**:
- **技能 CRUD**：创建、编辑、删除和查询技能定义，支持搜索和分类过滤。
- **技能定义**：支持 Markdown 格式编写技能文档，定义技能参数、执行方式及与 Action 类型的关联。
- **预设技能**：导入系统内置的预设技能包，支持一键导入和版本管理。
- **技能包管理**：支持 Zip 格式的技能包上传与下载，便于技能的分发和复用。
- **技能生成**：从本体的 Action Types 自动生成对应的技能定义。

**Skill 结构**:
```
skill-name/
├── SKILL.md           # 技能描述与元数据
├── prompt.md          # LLM 提示词模板（可选）
├── schema.json        # 输入/输出 Schema（可选）
└── scripts/           # 自动化脚本（可选）
```

**内置预设 Skills**:

| Skill | 分类 | 说明 |
|-------|------|------|
| rdb-to-ontology | build | 关系数据库表结构 → 本体，支持 PostgreSQL/MySQL/Hive |
| csv-to-ontology | build | CSV 智能导入，LLM 推断列映射 |
| ontology-data-build | build | 通用数据导入 (JSON/CSV/Parquet) |
| ontology-subgraph-search | ops | 子图检索与定位 |
| ontology-ops-agent | ops | 运维故障排查（图遍历驱动） |
| polardb-kb-search-agent | integration | 知识库语义检索（只读） |
| polardb-kb-agent | integration | 知识库完整管理（读写） |

**API**:
- `GET/POST /api/skills` — 列表 / 创建
- `GET /api/skills/presets` — 预设列表
- `POST /api/skills/upload` — 上传 zip 包
- `GET/PATCH/DELETE /api/skills/{skill_id}`
- `POST /api/skills/{skill_id}/enable|disable|clone|regenerate`
- `GET /api/skills/{skill_id}/download`
- `POST /api/skills/datasets/{dataset_id}/generate` — 从本体自动生成

---

### 3.11 权限管控 (ACR — Access Control Rules)

细粒度行级和属性级安全控制。

**核心概念**:
- **ACR 规则**: 定义对特定对象类型的访问限制条件
- **规则组**: 将多条规则组织为策略组
- **规则组绑定**: 将规则组绑定到用户 / 组
- **比较运算符**: eq, ne, in, not_in, intersects
- **用户属性**: user_id, username, groups, roles, custom:*

**配置项**:
```json
{
  "acr_enabled": false,
  "row_level_security": false,
  "property_level_security": false,
  "userid_injection": true,
  "admin_bypass": true,
  "admin_roles": ["admin"],
  "public_data_allowed": true
}
```

---

### 3.12 系统管理

系统管理模块为管理员提供全局系统配置与运维管理功能，包含以下 6 个子模块：

#### 用户管理
- 创建和维护用户账户，支持用户启用/禁用和自定义属性存储。
- 管理员可查看所有用户、修改用户角色、重置密码。

#### 角色管理
- 定义和分配角色（管理员 admin、开发者 developer、查看者 viewer）。
- 支持角色层级体系，角色决定用户的基础权限级别。

#### 用户组管理
- 创建用户分组，管理组成员，实现组级权限分配。
- 支持父子层级嵌套（如子组可继承父组权限）。

#### 令牌管理
- **API Key（管理员级别）**: 管理员创建/撤销系统级 API Key。
- **个人令牌（用户级别）**: 用户自行创建/撤销个人令牌 (Personal Access Token)。
- **Token 黑名单**: 服务端可即时撤销 Access/Refresh Token，支持按 Token ID 或按用户批量撤销。
- 令牌均采用加密存储。

#### ACR 配置
- 定义和管理细粒度访问控制规则（Access Control Rules）。
- 配置规则与用户组的绑定关系。
- 支持比较运算符：eq, ne, in, not_in, intersects。
- 可引用的用户属性：user_id, username, groups, roles, custom:*。

#### 系统配置
全局系统设置，包括：
- **数据库连接**：主数据库连接参数。
- **文档引擎类型**：PostgreSQL / OpenSearch，支持连接测试与引擎切换。
- **对象存储（OSS）**：File Storage Provider 配置（本地 / MinIO / S3）。
- **LLM 配置**：LLM / Embedding Provider 配置与切换。
- **系统级参数**：如默认分页大小、会话超时时间等。
- 支持 `${env:VAR_NAME}` 语法从环境变量读取敏感值，UI 修改即时生效。

**API**:
- `GET/POST /api/admin/system-config` — 系统配置
- `GET/PUT/DELETE /api/admin/system-config/{key}` — 单项配置
- `GET/POST /api/admin/users` — 用户管理
- `GET/POST /api/admin/groups` — 用户组管理
- `GET/POST /api/api-keys` — API Key 管理（用户）
- `GET /api/admin/api-keys` — API Key 管理（管理员）
- `GET/POST /api/personal-tokens` — PAT 管理（用户）
- `GET /api/admin/tokens` — Token 黑名单

---

### 3.13 异步任务管理

所有耗时操作统一走异步任务队列：

- LLM Schema 分析
- 数据同步
- 文档解析
- GraphRAG 运行
- RAG 评测运行

**API**:
- `GET /api/tasks/{task_id}` — 任务状态
- `GET /api/tasks/{task_id}/logs` — 执行日志
- `POST /api/tasks/{task_id}/cancel` — 取消任务

**任务状态机**: `pending → running → completed | failed | cancelled`

---

## 4. 数据模型汇总

### 4.1 统一 API 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": "ISO 8601"
}
```

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

### 4.3 核心 Schema 清单

| 类别 | Schema |
|------|--------|
| 数据集 | DatasetCreate, DatasetResponse |
| 对象类型 | ObjectTypeCreate/Update, PropertyDefinition, FGACConfig |
| 链接类型 | LinkTypeCreate/Update |
| 动作类型 | ActionTypeCreate/Update, ActionExecuteRequest, ActionConfirmRequest |
| 对象实例 | ObjectCreate/Update, BatchObjectsRequest |
| 链接实例 | LinkCreate, BatchLinksRequest |
| LLM 建模 | SchemaAnalyzeRequest, QuickAnalyzeRequest, DetectChangesRequest |
| 暂存区 | StagedChangeRef, CommitStagingRequest, UndoStagedChangesRequest |
| 版本 | VersionSnapshot, UpdateVersionNotesRequest |
| 同步 | SyncRequest, SyncConfig |
| Skills | SkillCreate/Update, SkillGenerateRequest, SkillRegenerateRequest |
| ACR | AccessRuleCreate/Update, ACRConfigUpdate, AdminRolesUpdate |
| 用户组 | GroupCreateRequest/UpdateRequest |
| 认证 | PasswordChangeRequest, APIKeyCreateRequest/Response |
| 评测 | EvaluationConfig, EvaluationRunCreate, CompareRunsRequest |
| 系统 | SystemConfigItem, EngineConfig, StorageConfig, LLMConfig |

---

## 5. 前端页面清单

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录页 | 紫色渐变背景，居中卡片 |
| `/` | 概览 / 仪表盘 | 系统首页 |
| `/datasets` | 数据集列表 | 表格 + CRUD |
| `/ontology/graph` | 本体图谱 | G6 2D/3D 可视化 |
| `/ontology/types` | 类型定义 | Object / Link / Action Types 管理 (Tab 切换) |
| `/ontology/modeling` | LLM 建模 | 三步向导式 AI 辅助建模 |
| `/ontology/instances` | 实例管理 | 本体图中的数据实例增删改查 |
| `/ontology/data-management` | 数据管理 | 本体构建入口：LLM建模/快速建模/结构变更/数据同步 |
| `/ontology/versions` | 版本管理 | 本体定义的版本对比与回滚 |
| `/ontology/permissions` | FGAC 权限管理 | 对象级和属性级数据隔离 |
| `/ragflow/knowledge-base` | 知识库管理 | 知识库 CRUD |
| `/ragflow/chat` | 对话助手 | 多轮对话问答 |
| `/ragflow/retrieval` | 内容检索 | 知识检索 |
| `/ragflow/model-config` | 模型配置 | RAG 模型配置 |
| `/ragflow/service-config` | 服务配置 | OSS + 文档引擎配置 |
| `/rag-evaluation` | RAG 评测 | 评测管理 |
| `/graphrag/knowledge-base` | GraphRAG 知识库 | Workspace 管理 |
| `/graphrag/documents` | 文档处理 | 文档上传与管理 |
| `/graphrag/graph` | 知识图谱 | 实体-关系图谱可视化 |
| `/graphrag/qa` | 知识问答 | 图谱增强问答 |
| `/graphrag/model-config` | GraphRAG 模型配置 | 模型提供商 + 模型管理 |
| `/skills` | Skills 管理 | 技能列表 + 导入/导出 |
| `/admin/users` | 用户管理 | 用户 CRUD |
| `/admin/roles` | 角色管理 | 角色定义与分配 |
| `/admin/groups` | 用户组管理 | 用户组管理 |
| `/admin/tokens` | 令牌管理 | API Key / PAT 管理 |
| `/admin/acr` | ACR 配置 | 访问控制规则管理 |
| `/admin/system-config` | 系统配置 | 全局系统设置 |
| `/api-keys` | 我的 API Key | 用户自行管理 API Key |
| `/personal-tokens` | 我的 PAT | 用户自行管理个人令牌 |
| `/health` | 健康检查 | 系统健康状态 |
| `/profile` | 个人中心 | 用户信息 / 密码修改 |
| `/forbidden` | 403 页面 | 权限不足 |

---

## 6. UI / UX 设计规范

### 6.1 全局样式
- 字体: Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif
- 背景色: `#f4f5f7`
- 滚动条: 6px, 轨道 `#f4f5f7`, 滑块 `#d1d5db`, hover `#9ca3af`
- 侧边栏菜单: 多层级嵌套, 图标 + 文字

### 6.2 登录页
- 背景: `linear-gradient(135deg, #667eea, #764ba2)`
- 卡片: 400px, `box-shadow: 0 4px 12px rgba(0,0,0,0.15)`, `border-radius: 8px`
- 标题: 居中, 20px, font-weight 600
- 副标题: 居中, `#666`, margin-bottom 24px
- 页脚: 居中, `#999`, 12px, 上边框 `1px solid #f0f0f0`

### 6.3 图谱视图
- 3D 模式: 深色主题 (`#1a1a2e`)
- 2D 模式: 浅色主题 (`#f5f5f5`)
- 详情面板: 280px (响应式: <1200px → 240px, <900px → 浮动面板)
- 左侧工具栏: 44px
- 底部状态栏: 填充式

### 6.4 通用 UI 组件
Table(responsive + sort + filter), Form(validation), Modal(confirm), Upload(progress), Transfer(search + select), Popconfirm, Text(editable/copyable/expandable), Image(preview), QRCode, ColorPicker, Tour, DatePicker/TimePicker

---

## 7. 安全与认证

### 7.1 JWT Token
- Access Token: 15 分钟过期
- Refresh Token: 7 天过期
- 存储: localStorage
- 传输: `Authorization: Bearer <token>`
- 黑名单机制: 服务端可即时撤销

### 7.2 错误处理

| HTTP 状态码 | 处理策略 |
|------------|---------|
| 401 | 自动刷新 Token，失败跳转 `/login` |
| 403 | "权限不足，请联系管理员授权" |
| 404 | "Resource not found" |
| 409 | 静默忽略（乐观锁冲突） |
| 422 | 解析验证错误详情展示 |
| 500 | "Server error" |
| Network Error | "Network error - please check your connection" |

---

## 8. 部署与环境

### 8.1 最小部署（开发 / 小团队）

| 组件 | 部署方案 | 端口 |
|------|---------|------|
| PostgreSQL 14+ | 单实例 Docker | 5432 |
| pgvector 扩展 | PostgreSQL 插件 | — |
| Apache AGE 扩展 | PostgreSQL 插件（图存储） | — |
| FastAPI 后端 | 单实例 / Docker | 8080 |
| React 前端 | Nginx 静态文件或 Vite dev | 3000 |
| 文件存储 | 本地磁盘 `/data/files` | — |
| 任务队列 | 内存队列（开发） / Redis + Celery（生产） | — |

**仅需 PostgreSQL 一个数据库依赖**即可运行全部核心功能（含图存储、向量检索、全文搜索、文档引擎）。

### 8.2 生产部署（可扩展）

```
┌───────────────────────────────────────────────────────┐
│  Nginx / Traefik (反向代理 + 静态文件)                 │
├───────────────────────────────────────────────────────┤
│  FastAPI × N (水平扩展)                                │
├───────────────────────────────────────────────────────┤
│  Redis (任务队列 + 缓存)                               │
├──────────────┬──────────────┬─────────────────────────┤
│ PostgreSQL   │ 可选:        │ 可选:                    │
│ + pgvector   │ Milvus/Qdrant│ MinIO/S3                │
│ + AGE (图)   │ (独立向量库) │ (对象存储)               │
└──────────────┴──────────────┴─────────────────────────┘
```

### 8.3 默认 Provider 配置（可直接用于开发）

以下为系统启动时的默认配置，开发人员无需做任何选择即可开始开发：

```json
{
  "llm": {
    "provider": "deepseek",
    "config": {
      "api_base": "https://api.deepseek.com/v1",
      "api_key": "${env:DEEPSEEK_API_KEY}",
      "default_model": "deepseek-chat",
      "default_params": {
        "temperature": 0.1,
        "max_tokens": 4096
      }
    }
  },
  "embedding": {
    "provider": "deepseek",
    "config": {
      "api_base": "https://api.deepseek.com/v1",
      "api_key": "${env:DEEPSEEK_API_KEY}",
      "model": "text-embedding-adas-002-compatible"
    }
  },
  "rag": {
    "provider": "builtin"
  },
  "document_engine": {
    "provider": "postgresql",
    "config": {
      "host": "${env:DB_HOST}",
      "port": 5432,
      "username": "${env:DB_USER}",
      "password": "${env:DB_PASSWORD}",
      "database": "${env:DB_NAME}",
      "fts_language": "chinese",
      "hybrid_mode": "weighted_fusion"
    }
  },
  "file_storage": {
    "provider": "local",
    "config": {
      "base_path": "/data/ontology_files"
    }
  },
  "graph_db": {
    "provider": "age",
    "config": {
      "host": "${env:DB_HOST}",
      "port": 5432,
      "username": "${env:DB_USER}",
      "password": "${env:DB_PASSWORD}",
      "database": "${env:DB_NAME}"
    }
  }
}
```

> **开发指令**: 以上配置为系统出厂默认值。Phase 1 完成后，在管理后台提供可视化界面让管理员修改这些配置。${env:XXX} 占位符从环境变量读取，确保密钥不入库。

---

## 9. 实现路线图

### 9.1 复刻优先级

**Phase 1 — 核心基础**

| # | 任务 | 产出 |
|---|------|------|
| 1 | FastAPI 后端框架搭建 + 全部 Provider 接口及**默认实现** | 可运行的 API 骨架 |
| 2 | JWT 认证 + 用户 / 角色 / 组管理 | 登录 / Token 刷新 / 用户 CRUD |
| 3 | 数据集 CRUD | `/api/datasets` 完整可用 |
| 4 | Object Types / Link Types / Action Types 管理 | `/api/datasets/{id}/ontology/*` 完整可用 |
| 5 | Objects / Links 实例管理 | 实例数据 CRUD + 批量操作 |
| 6 | React 前端框架 + Ant Design 布局 + 侧边栏导航 | 可交互的前端骨架 |

**Phase 2 — 可视化与建模**

| # | 任务 | 产出 |
|---|------|------|
| 7 | AntV G6 图谱可视化 (2D/3D) | 图谱浏览 / 搜索 / 邻居展开 |
| 8 | LLM 辅助建模 | 数据库 Schema 自动分析 → 生成本体定义 |
| 9 | 暂存区 (Staging) + 版本管理 | commit / discard / undo / 回滚 |
| 10 | 图遍历与路径查询 | 邻居节点 / 最短路径 / 子图遍历 |
| 11 | BuiltinRAGProvider 实现 | 文档解析 + Chunk + 全文检索 + 向量检索 + LLM 问答 |

**Phase 3 — RAG 增强**

| # | 任务 | 产出 |
|---|------|------|
| 12 | RAG 评测框架 | 评测数据集 / 运行 / 结果对比 |
| 13 | GraphRAG | 知识图谱增强检索 |
| 14 | 对话助手 | 多轮对话 + 流式输出 |
| 15 | 数据源同步 | MySQL / Hive / HBase 数据源接入 |

**Phase 4 — 权限与扩展**

| # | 任务 | 产出 |
|---|------|------|
| 16 | RBAC + ACR 细粒度权限 | 行级 / 属性级安全控制 |
| 17 | Skills 系统 | 预设 Skills + 自定义上传 |
| 18 | API Key / PAT 管理 | 用户凭证自助管理 |
| 19 | 系统配置管理界面 | Provider 切换可视化、连接测试 |
| 20 | 补充 Provider 实现 (可选) | Ollama / MinIO / Neo4j / OpenSearch |

### 9.2 数据库设计要点
- 每个数据集独立 Schema: `{dataset_id}_ontology`
- 每个数据集独立图空间: `{dataset_id}_graph`
- 版本快照存储完整 Ontology 定义
- 暂存区使用 JSON 存储待提交变更
- Provider 配置存储在 `system_config` 表中

### 9.3 关键技术难点
- **Provider 抽象设计**: 接口粒度要适中，过细则实现复杂，过粗则无法发挥各 Provider 特性
- **G6 图可视化**: 自定义节点 / 边样式、布局算法、3D 渲染
- **LLM 建模 Prompt**: 需要让 LLM 理解数据库 Schema 语义，Prompt 模板需支持多模型适配
- **暂存区设计**: 类 Git 的 add / commit / discard / undo 机制
- **ACR**: 行级 / 属性级安全需要在 SQL 查询时动态注入条件
- **数据同步**: 增量同步 + 断点续传，多数据源适配
- **GraphRAG**: 图遍历结果与向量检索结果的融合策略

---

## 10. 附录

### A. 图可视化布局算法
- 层次化 (Hierarchical): 从上到下 / 从下到上 / 从左到右 / 从右到左
- 力导向 (Force-Directed)
- 径向 (Radial)
- 圆形 (Circular)
- 网格 (Grid)
- 同心圆 (Concentric)

### B. Provider 实现清单

以下为**本次开发需要实现的 Provider**，全部标记为 ★ 推荐方案。

| Provider 类型 | 需实现的类 | 依赖 | 优先级 |
|-------------|-----------|------|--------|
| LLM | **`DeepSeekProvider`** | DeepSeek API Key | P0 (Phase 1) |
| Embedding | **`DeepSeekEmbedding`** | DeepSeek API Key | P0 (Phase 1) |
| RAG | **`BuiltinRAGProvider`** | DocumentEngine + LLM + Embedding 三个 Provider | P0 (Phase 2) |
| Document Engine | **`PostgresDocumentEngine`** | PostgreSQL GIN + pgvector | P0 (Phase 1) |
| Graph DB | **`AGEGraphDB`** | PostgreSQL + Apache AGE 扩展 | P0 (Phase 1) |
| File Storage | **`LocalFileStorage`** | 本地磁盘 | P0 (Phase 1) |

**远期可选的额外 Provider**（本次不实现，仅供架构参考）:

| Provider | 说明 |
|----------|------|
| `OllamaProvider` | 本地 LLM，数据不出网 |
| `OllamaEmbedding` | 本地 Embedding |
| `MinIOStorage` | S3 兼容对象存储，生产环境横向扩展 |
| `Neo4jGraphDB` | 专用图数据库，复杂图查询场景 |
| `OpenSearchEngine` | 专业全文搜索引擎，大规模场景 |
| `RAGFlowProvider` | 成熟文档解析能力（需额外部署 RAGFlow） |

### C. 配置文件优先级
1. 环境变量 (`ONTOLOGY_LLM__PROVIDER`, `ONTOLOGY_DB__HOST` 等)
2. `.env` 文件
3. 数据库 `system_config` 表（管理员可在 UI 修改）
4. 代码默认值

UI 界面修改的配置即时生效，不依赖重启。

### D. Skills 开发规范
Skills 包含 `SKILL.md` 描述文件，支持:
- 分类标签 (build / ops / integration / analyze)
- LLM 配置（可指定模型、temperature 等）
- 数据集关联
- 版本管理
- 导入 / 导出 (zip 包)
