# Task ID: 16

**Title:** RBAC + ACR 细粒度权限管控

**Status:** pending

**Dependencies:** 2

**Priority:** high

**Description:** 细粒度行级和属性级安全控制。ACR 规则定义（比较运算符 eq/ne/in/not_in/intersects，用户属性 user_id/username/groups/roles/custom:*）、规则组管理、规则组绑定到用户/组。ACR 配置: acr_enabled, row_level_security, property_level_security, userid_injection, admin_bypass, admin_roles, public_data_allowed。SQL 查询时动态注入条件。

**Details:**

API: AccessRuleCreate/Update, ACRConfigUpdate, AdminRolesUpdate。前端: /admin/acr ACR配置页面。

**Test Strategy:**

No test strategy provided.
