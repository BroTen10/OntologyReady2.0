# Task ID: 2

**Title:** JWT 认证 + 用户/角色/组管理

**Status:** pending

**Dependencies:** None

**Priority:** high

**Description:** 实现 JWT Bearer Token 认证（Access Token 15min + Refresh Token 7天），用户 CRUD，角色管理（admin/developer/viewer），用户组管理（admins/developers/viewers 支持父子层级嵌套），Token 黑名单机制，401 自动刷新。

**Details:**

用户模型: id/UUID, username, email, full_name, is_active, is_superuser, roles, groups, custom_attributes, created_at, updated_at, last_login。登录 POST /api/auth/login (form-urlencoded)，刷新 POST /api/auth/refresh。

**Test Strategy:**

No test strategy provided.
