# OntologyReady 2.0 — API Reference

## Overview

**Base URL:** `/api`
**OpenAPI Spec:** `/api/openapi.json`
**Swagger UI:** `/api/docs`
**Health Check:** `GET /api/health`

### Response Format

All endpoints return a unified JSON structure:

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... },
  "timestamp": "2026-06-08T12:00:00.000Z"
}
```

- `code=0` indicates success; non-zero indicates an error.
- `message` provides a human-readable summary.
- `data` holds the payload (nullable for error responses).

### Pagination

List endpoints support `?page=1&page_size=20` query params and return:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [ ... ],
    "page_info": {
      "page": 1,
      "page_size": 20,
      "total": 95,
      "total_pages": 5
    }
  }
}
```

### Authentication

All endpoints except `/api/auth/login`, `/api/auth/refresh`, and `/api/health` require:

```
Authorization: Bearer <access_token>
```

- Access tokens expire in **15 minutes**.
- Refresh tokens expire in **7 days**.
- On 401, the frontend interceptor automatically calls `/api/auth/refresh`.

---

## Auth — `/api/auth`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login (form-urlencoded: `username` + `password`) |
| `POST` | `/api/auth/refresh` | Refresh access token (body: `{"refresh_token":"..."}`) |
| `GET`  | `/api/auth/me` | Get current user profile |
| `PUT`  | `/api/auth/me` | Update current user profile |

---

## Datasets — `/api/datasets`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/datasets` | List datasets (paginated) |
| `POST`   | `/api/datasets` | Create dataset |
| `GET`    | `/api/datasets/{dataset_id}` | Get dataset detail |
| `PUT`    | `/api/datasets/{dataset_id}` | Update dataset |
| `DELETE` | `/api/datasets/{dataset_id}` | Delete dataset |

---

## Ontology — `/api/datasets/{id}/ontology`

### Object Types

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `.../object-types` | List object types |
| `POST`   | `.../object-types` | Create object type |
| `GET`    | `.../object-types/{type_id}` | Get type detail |
| `PUT`    | `.../object-types/{type_id}` | Update type |
| `DELETE` | `.../object-types/{type_id}` | Delete type |

### Link Types

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `.../link-types` | List link types |
| `POST`   | `.../link-types` | Create link type |
| `GET`    | `.../link-types/{type_id}` | Get type detail |
| `PUT`    | `.../link-types/{type_id}` | Update type |
| `DELETE` | `.../link-types/{type_id}` | Delete type |

### Action Types

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `.../action-types` | List action types |
| `POST`   | `.../action-types` | Create action type |
| `GET`    | `.../action-types/{type_id}` | Get type detail |
| `PUT`    | `.../action-types/{type_id}` | Update type |
| `DELETE` | `.../action-types/{type_id}` | Delete type |

---

## Instances — `/api/datasets/{id}/ontology`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `.../objects?type={type}` | List objects (paginated) |
| `POST`   | `.../objects` | Create object |
| `PUT`    | `.../objects/{obj_id}` | Update object |
| `DELETE` | `.../objects/{obj_id}` | Delete object |
| `POST`   | `.../objects/search` | Search objects (full-text) |
| `GET`    | `.../links?from={id}` | List links |
| `POST`   | `.../links` | Create link |
| `DELETE` | `.../links/{link_id}` | Delete link |
| `POST`   | `.../objects/batch` | Batch create objects |
| `POST`   | `.../links/batch` | Batch create links |

---

## Graph — `/api/datasets/{id}/ontology/graph`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `.../stats` | Graph statistics (node/edge counts) |
| `GET`    | `.../knowledge?limit=n` | Get graph nodes & edges |
| `GET`    | `.../neighbors/{obj_type}/{obj_id}?depth=3` | Get neighbor subgraph |
| `POST`   | `.../path` | Find shortest path between two nodes |
| `POST`   | `.../traverse` | Traverse graph from start node |

---

## LLM Modeling — `/api/datasets/{id}/ontology/modeling`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `.../analyze-schema` | LLM schema analysis (async) |
| `POST` | `.../compile` | Compile & validate proposed definitions |
| `POST` | `.../register` | Register compiled definitions |
| `POST` | `.../quick-modeling` | Quick modeling (no LLM) |
| `POST` | `.../detect-changes` | Detect structural changes |

---

## Versioning — `/api/datasets/{id}/ontology/versions`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `.../` | List version history |
| `GET`    | `.../{version_id}` | Get version snapshot |
| `POST`   | `.../{version_id}/rollback` | Rollback to version |
| `PUT`    | `.../{version_id}/notes` | Update version notes |
| `POST`   | `.../compare` | Compare two versions |

### Staging — `/api/datasets/{id}/ontology/staging`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `.../` | View staged changes |
| `POST`   | `.../commit` | Commit staged changes |
| `POST`   | `.../discard` | Discard staged changes |
| `POST`   | `.../undo` | Undo last stage operation |

---

## Data Sync — `/api/datasets/{id}/sync`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `.../` | Trigger data sync |
| `GET`  | `.../config` | Get sync configuration |
| `PUT`  | `.../config` | Update sync configuration |
| `POST` | `.../test-connection` | Test data source connection |

---

## RAG — `/api/rag`

### Knowledge Bases

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/rag/knowledge-bases` | List KBs |
| `POST`   | `/api/rag/knowledge-bases` | Create KB |
| `GET`    | `/api/rag/knowledge-bases/{kb_id}` | Get KB detail |
| `DELETE` | `/api/rag/knowledge-bases/{kb_id}` | Delete KB |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/rag/knowledge-bases/{kb_id}/documents` | List documents |
| `POST`   | `/api/rag/knowledge-bases/{kb_id}/documents` | Upload document |
| `GET`    | `/api/rag/documents/{doc_id}` | Get document |
| `DELETE` | `/api/rag/documents/{doc_id}` | Delete document |
| `GET`    | `/api/rag/documents/{doc_id}/chunks` | List chunks |
| `POST`   | `/api/rag/documents/{doc_id}/parse` | Trigger parse & embed |

### Search & Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/rag/knowledge-bases/{kb_id}/search` | Search knowledge base |
| `POST` | `/api/rag/knowledge-bases/{kb_id}/chat` | QA chat (non-streaming) |
| `POST` | `/api/rag/knowledge-bases/{kb_id}/chat/stream` | QA chat (SSE streaming) |

---

## RAG Evaluation — `/api/rag-evaluation`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/rag-evaluation/datasets` | List evaluation datasets |
| `POST`   | `/api/rag-evaluation/datasets` | Create evaluation dataset |
| `GET`    | `/api/rag-evaluation/runs` | List evaluation runs |
| `POST`   | `/api/rag-evaluation/runs` | Start evaluation run |
| `GET`    | `/api/rag-evaluation/runs/{run_id}` | Get run results |
| `POST`   | `/api/rag-evaluation/runs/compare` | Compare two runs |

---

## GraphRAG — `/api/graphrag`

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/graphrag/workspaces` | List workspaces |
| `POST` | `/api/graphrag/workspaces` | Create workspace |
| `GET`  | `/api/graphrag/workspaces/{id}` | Get workspace detail |
| `DELETE`| `/api/graphrag/workspaces/{id}` | Delete workspace |
| `POST` | `/api/graphrag/workspaces/{id}/documents` | Upload document |
| `POST` | `/api/graphrag/workspaces/{id}/build` | Build knowledge graph (async) |
| `GET`  | `/api/graphrag/workspaces/{id}/graph` | Get workspace graph |
| `POST` | `/api/graphrag/workspaces/{id}/qa` | GraphRAG QA |
| `GET`  | `/api/graphrag/model-config` | Get model config |
| `PUT`  | `/api/graphrag/model-config` | Update model config |

---

## Skills — `/api/skills`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/skills` | List skills |
| `POST`   | `/api/skills` | Create skill |
| `GET`    | `/api/skills/{skill_id}` | Get skill |
| `PUT`    | `/api/skills/{skill_id}` | Update skill |
| `DELETE` | `/api/skills/{skill_id}` | Delete skill |
| `POST`   | `/api/skills/{skill_id}/enable` | Enable skill |
| `POST`   | `/api/skills/{skill_id}/disable` | Disable skill |
| `POST`   | `/api/skills/{skill_id}/clone` | Clone skill |
| `POST`   | `/api/skills/upload` | Upload skill zip |
| `GET`    | `/api/skills/{skill_id}/download` | Download skill zip |
| `GET`    | `/api/skills/presets` | List preset skills |
| `POST`   | `/api/skills/presets/import` | Import preset skill |
| `POST`   | `/api/skills/generate-from-dataset/{dataset_id}` | Generate skills from Action Types |

---

## Tasks (Async) — `/api/tasks`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/tasks` | List tasks |
| `GET`    | `/api/tasks/{task_id}` | Get task status |
| `GET`    | `/api/tasks/{task_id}/logs` | Get task logs |
| `POST`   | `/api/tasks/{task_id}/cancel` | Cancel task |

---

## Token Management

### API Keys — `/api/api-keys`

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/api-keys` | List my API keys |
| `POST` | `/api/api-keys` | Create API key |

### Personal Access Tokens — `/api/personal-tokens`

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/personal-tokens` | List my PATs |
| `POST` | `/api/personal-tokens` | Create PAT |

### Admin Token Blacklist — `/api/admin/tokens`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/admin/tokens` | List all tokens/blacklist |
| `DELETE` | `/api/admin/tokens/{token_id}` | Revoke token |
| `POST`   | `/api/admin/tokens/revoke-user/{user_id}` | Revoke all tokens for user |

---

## ACR (Access Control) — `/api/admin/acr`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/admin/acr/rules` | List ACR rules |
| `POST`   | `/api/admin/acr/rules` | Create rule |
| `PUT`    | `/api/admin/acr/rules/{rule_id}` | Update rule |
| `DELETE` | `/api/admin/acr/rules/{rule_id}` | Delete rule |
| `GET`    | `/api/admin/acr/config` | Get ACR config |
| `PUT`    | `/api/admin/acr/config` | Update ACR config |

---

## System Config — `/api/admin/system-config`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/admin/system-config` | List all config items |
| `POST`   | `/api/admin/system-config` | Create config item |
| `GET`    | `/api/admin/system-config/{key}` | Get config item |
| `PUT`    | `/api/admin/system-config/{key}` | Update config item |
| `DELETE` | `/api/admin/system-config/{key}` | Delete config item |

---

## Users & Groups — `/api/admin`

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/admin/users` | List users (paginated) |
| `POST`   | `/api/admin/users` | Create user |
| `PUT`    | `/api/admin/users/{id}` | Update user |
| `DELETE` | `/api/admin/users/{id}` | Delete user |
| `GET`    | `/api/admin/groups` | List groups |
| `POST`   | `/api/admin/groups` | Create group |
| `PUT`    | `/api/admin/groups/{id}` | Update group |
| `DELETE` | `/api/admin/groups/{id}` | Delete group |
| `GET`    | `/api/admin/roles` | List roles |
