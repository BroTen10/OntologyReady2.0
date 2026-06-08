# Task ID: 22

**Title:** Docker 部署与环境配置

**Status:** pending

**Dependencies:** 1

**Priority:** high

**Description:** Docker 部署支持。编写 Dockerfile（FastAPI 后端 + React 前端 Nginx 静态文件）、docker-compose.yml（PostgreSQL 14+ 含 pgvector 和 Apache AGE 扩展 + FastAPI + Nginx + Redis可选 + 本地文件存储卷挂载）。环境变量管理（.env 文件模板）。健康检查端点 /api/health。

**Details:**

端口: PostgreSQL 5432, FastAPI 8080, React/Nginx 3000。生产部署可选 Nginx/Traefik 反向代理+FastAPI水平扩展+Redis+Celery。

**Test Strategy:**

No test strategy provided.
