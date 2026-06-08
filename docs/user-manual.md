# User Manual

## Getting Started

### Login

Navigate to the platform URL (default `http://localhost:3000`). You'll see a login page with a centered card on a gradient background.

1. Enter your **username** and **password**.
2. Click **Login**.
3. On first use, an admin account should be created. Contact your administrator.

### Navigation

The sidebar provides access to all modules:

- **Dashboard** — Overview and platform statistics
- **Datasets** — Manage knowledge spaces (namespaces)
- **Ontology** — Define types, instances, and graph data
  - *Type Definitions* — Object, Link, and Action types
  - *LLM Modeling* — AI-assisted schema modeling wizard
  - *Instance Management* — CRUD for graph nodes and edges
  - *Data Management* — Quick modeling, structure change detection, data sync
  - *Version Management* — Git-like version history and rollback
  - *Permissions* — FGAC access control rules
- **RAGFlow** — RAG knowledge bases and QA
  - *Knowledge Base* — Manage KBs and upload documents
  - *Chat* — Conversational QA assistant
  - *Retrieval* — Search & retrieve from KB
  - *Model Config* — Configure LLM/Embedding settings
  - *Service Config* — Configure document engine and storage
- **GraphRAG** — Knowledge graph-enhanced RAG
  - *Knowledge Base* — Workspace management
  - *Documents* — Upload documents for graph construction
  - *Graph* — Visualize extracted entity-relationship graph
  - *QA* — Graph-enhanced question answering
  - *Model Config* — GraphRAG model settings
- **RAG Evaluation** — Evaluate and compare RAG performance
- **Skills** — Manage skill extensions
- **System Admin** — User/group/role management, API keys, system config
- **My Profile** — Personal settings, API keys, PATs

---

## Datasets

A **Dataset** is a namespace or knowledge space. Each dataset has independent ontology definitions, instance data, and a graph.

### Create a Dataset

1. Navigate to **Datasets** from the sidebar.
2. Click **+ New Dataset**.
3. Enter a display name and optional description.
4. Click **Create**.

### Switch Datasets

Click a dataset card to enter its ontology workspace. The active dataset is shown in the breadcrumb.

---

## Ontology — Type Definitions

### Object Types

Object Types define node types in the knowledge graph (e.g., "Person", "Company", "Product").

1. Go to **Ontology > Type Definitions**.
2. Select the **Object Types** tab.
3. Click **+ Add Object Type**.
4. Fill in:
   - **Name** — Unique type identifier
   - **Display Name** — Human-readable label
   - **Description**
   - **Properties** — Define attributes with type (`string`/`number`/`datetime`/`boolean`), required, unique, indexed flags
5. Click **Save**.

### Link Types

Link Types define directed relationships between Object Types (e.g., "WORKS_AT" from Person to Company).

1. Select the **Link Types** tab.
2. Click **+ Add Link Type**.
3. Specify **Source Type**, **Target Type**, and whether it's **Directed**.
4. Add properties if needed.
5. Click **Save**.

### Action Types

Action Types define executable operations (e.g., "Send Email", "Call Webhook").

1. Select the **Action Types** tab.
2. Configure the webhook URL, HTTP method, headers, and effect type.
3. Click **Save**.

---

## LLM Modeling (Three-Step Wizard)

Automatically generate ontology definitions from your database schema using AI.

### Step 1 — Connection

1. Go to **Ontology > LLM Modeling**.
2. Choose a connection configuration:
   - Project default instance
   - Manual database connection parameters
   - DSN connection string
3. Click **Test Connection** to verify.
4. Configure **Schema**, **Business Background**, **Output Language**, and **Advanced Options**.
5. Click **Next: Analyze**.

### Step 2 — Preview

1. The LLM analyzes your schema and proposes Object Types, Link Types, and properties.
2. Switch between **List View** and **Graph View** to review.
3. Edit definitions inline (JSON editor available).
4. Delete unwanted types (cascading deletes related links).
5. Click **Compile** to validate. Fix any errors.
6. Click **Next: Register**.

### Step 3 — Register

1. Review the final set of definitions.
2. Click **Register** to create them in the dataset.
3. Optionally trigger a data sync.

---

## Graph Visualization

### 2D/3D Graph View

1. Go to **Ontology > Instance Management** and click the **Graph** tab.
2. Toggle between **2D** (light theme) and **3D** (dark theme) modes.
3. Use the layout switcher to choose from 6 algorithms:
   - Hierarchical, Force-Directed, Radial, Circular, Grid, Concentric

### Interaction

- **Pan** — Click and drag canvas
- **Zoom** — Scroll wheel or toolbar buttons
- **Click node** — Opens detail panel on the right (280px, responsive)
- **Search** — Use the search bar to locate nodes by name
- **Neighbor expansion** — Adjust the depth slider (1-5 layers)

### Detail Panel

Shows:
- Node properties (key-value pairs)
- Connected relationships
- Related nodes with clickable links

### Toolbar

- Zoom in/out
- Fit to canvas
- Layout switcher
- Export (PNG/SVG)
- Fullscreen mode

### Tabs

- **Entity Graph** — Shows object-level nodes and links
- **Structure Graph** — Shows type-level schema structure

---

## RAG — Knowledge Base & Chat

### Create a Knowledge Base

1. Go to **RAGFlow > Knowledge Base**.
2. Click **+ New KB**.
3. Enter name and description.
4. Configure chunking strategy (fixed size / paragraph / heading / semantic).

### Upload Documents

1. Click into a knowledge base.
2. Click **Upload** and select files.
   - Supported formats: PDF, Word, Markdown, TXT, HTML, CSV, Excel
3. Documents are automatically parsed, chunked, embedded, and indexed.

### Chat with Knowledge Base

1. Go to **RAGFlow > Chat**.
2. Select a knowledge base from the dropdown.
3. Configure model parameters (Temperature, Top-P, Similarity Threshold, Top N).
4. Type your question and press **Enter** (Shift+Enter for new line).
5. The response streams in real time with source citations.
6. Click citations to expand and view the referenced chunk and source document.

### Retrieve

1. Go to **RAGFlow > Retrieval**.
2. Search across a knowledge base.
3. View ranked results with relevance scores.

---

## GraphRAG

GraphRAG combines knowledge graphs with RAG for enhanced retrieval.

### Workflow

1. **Create Workspace** — Go to GraphRAG > Knowledge Base, create a workspace.
2. **Upload Documents** — Upload text documents.
3. **Build Graph** — The system uses LLM to extract entities and relationships, writing them to the AGE graph database.
4. **Visualize** — View the extracted entity-relationship network in G6.
5. **QA** — Ask questions that leverage both graph structure and document content.

### Search Modes

- **Local** — Retrieve from local subgraph around relevant entities
- **Global** — Retrieve from the full graph with community summarization
- **Hybrid** — Combine local + global
- **Naive** — Pure vector search (no graph)
- **Mix** — Blend of multiple strategies

---

## RAG Evaluation

1. Go to **RAG Evaluation**.
2. Create an evaluation dataset (questions + reference answers).
3. Start an evaluation run against a knowledge base.
4. Review per-question metrics and aggregate scores:
   - Answer Accuracy
   - Recall
   - Citation Accuracy
   - Response Time

---

## Skills

Skills are pluggable extensions written in Markdown + prompt templates.

### Browse & Install

1. Go to **Skills**.
2. Browse available skills.
3. Click **Enable** to activate a skill.
4. Import preset skill packs (rdb-to-ontology, csv-to-ontology, etc.).

### Create Custom Skills

1. Click **+ New Skill**.
2. Write a `SKILL.md` (metadata), `prompt.md` (LLM instructions), and optional `schema.json`.
3. Upload supporting scripts.

---

## Administration

### User Management

Navigate to **System Admin > Users** to:
- Create, edit, disable users
- Assign roles (`admin`, `developer`, `viewer`)
- Assign group memberships

### Groups

Hierarchical groups with parent-child nesting (e.g., `admins > developers > viewers`).

### ACR (Access Control Rules)

Fine-grained row-level and property-level security:

1. Go to **Ontology > Permissions** or **System Admin > ACR**.
2. Create rules with conditions like:
   - `user_id eq "current_user"`
   - `groups in ["developers"]`
3. Bind rules to users or groups.
4. Enable `row_level_security` and `property_level_security` in ACR config.

### System Configuration

1. Go to **System Admin > System Config**.
2. Configure database connections, document engine type, LLM/Embedding providers.
3. Set system-level parameters (pagination size, session timeout).
4. Use `${env:VAR_NAME}` syntax for secrets.

### API Keys & Personal Tokens

- **API Keys** — System-level keys for external integrations (admin only).
- **Personal Access Tokens (PATs)** — Per-user tokens for API access.
- **Token Blacklist** — Revoke tokens immediately from the admin panel.

---

## Keyboard Shortcuts (Frontend)

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message (in chat) |
| `Shift+Enter` | New line (in chat) |
| `Ctrl+F` | Search within graph |
| `Esc` | Close modal / exit fullscreen |
