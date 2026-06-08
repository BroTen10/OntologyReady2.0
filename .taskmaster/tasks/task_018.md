# Task ID: 18

**Title:** API Key / PAT 管理 + Token 黑名单

**Status:** pending

**Dependencies:** 2

**Priority:** high

**Description:** API Key（管理员级别系统级 API Key）+ Personal Access Token（用户级别个人令牌）的完整管理。创建/撤销/列表查询。Token 黑名单（按 Token ID 或按用户批量撤销、即时生效）。令牌加密存储。

**Details:**

API: GET/POST /api/api-keys (用户), GET /api/admin/api-keys (管理员), GET/POST /api/personal-tokens (用户), GET /api/admin/tokens (黑名单)。前端: /admin/tokens, /api-keys, /personal-tokens。

**Test Strategy:**

No test strategy provided.
