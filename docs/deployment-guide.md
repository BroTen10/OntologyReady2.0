# Deployment & Operations Manual

## Architecture Overview

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Browser    │───▶│  Nginx (:3000)│───▶│ FastAPI (:8080)│
│   (React)    │    │  Static + API │    │  Backend      │
└──────────────┘    │  Proxy        │    └──────┬───────┘
                    └──────────────┘           │
                                        ┌──────▼───────┐
                                        │ PostgreSQL 14 │
                                        │ + pgvector    │
                                        │ + Apache AGE  │
                                        └──────────────┘
                                               │
                                        ┌──────▼───────┐
                                        │ Redis (opt.)  │
                                        │ for Celery    │
                                        └──────────────┘
```

## Prerequisites

- Docker 24+ & Docker Compose v2+
- 4 GB RAM minimum (8 GB recommended)
- 10 GB disk space

## Quick Start (Docker Compose)

### 1. Clone & Configure

```bash
cd ontology-platform

# Create .env from template
cat > .env << 'EOF'
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme
POSTGRES_DB=ontology
POSTGRES_PORT=5432
BACKEND_PORT=8080
FRONTEND_PORT=3000
REDIS_PORT=6379
SECRET_KEY=your-random-secret-key-at-least-32-chars
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
EOF
```

### 2. Provider Configuration

Create `backend/config/providers.json`:

```json
{
  "llm": {"provider": "deepseek", "config": {"api_key": "${env:DEEPSEEK_API_KEY}"}},
  "embedding": {"provider": "deepseek_embedding", "config": {"api_key": "${env:DEEPSEEK_API_KEY}"}},
  "rag": {"provider": "builtin", "config": {}},
  "document_engine": {"provider": "postgres", "config": {}},
  "file_storage": {"provider": "local", "config": {"root": "/data/files"}},
  "graph_db": {"provider": "age", "config": {}}
}
```

### 3. Start Services

```bash
# Core services (PostgreSQL + Backend + Frontend)
docker compose up -d

# With Redis for async task queue
docker compose --profile full up -d
```

### 4. Verify

```bash
# Health check
curl http://localhost:8080/api/health

# Open frontend
open http://localhost:3000

# API docs
open http://localhost:8080/api/docs
```

## Service Details

| Service | Port | Container Name | Image |
|---------|------|----------------|-------|
| PostgreSQL 14 | 5432 | `ontology-postgres` | `postgres:14` |
| FastAPI Backend | 8080 | `ontology-backend` | Built from `Dockerfile.backend` |
| React/Nginx Frontend | 3000 | `ontology-frontend` | Built from `Dockerfile.frontend` |
| Redis (optional) | 6379 | `ontology-redis` | `redis:7-alpine` |

## Database

PostgreSQL 14 with two critical extensions:

- **pgvector** — Vector similarity search for RAG embeddings
- **Apache AGE** — Graph database (Cypher queries on PostgreSQL)

The init script at `docker/postgres/init.sql` creates these extensions automatically.

### Connection String

```
postgresql://postgres:changeme@localhost:5432/ontology
```

### Backup & Restore

```bash
# Backup
docker exec ontology-postgres pg_dump -U postgres ontology > backup.sql

# Restore
docker exec -i ontology-postgres psql -U postgres ontology < backup.sql
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `POSTGRES_DB` | `ontology` | Database name |
| `POSTGRES_PORT` | `5432` | Database port |
| `BACKEND_PORT` | `8080` | Backend API port |
| `FRONTEND_PORT` | `3000` | Frontend web port |
| `REDIS_PORT` | `6379` | Redis port |
| `SECRET_KEY` | (required) | JWT signing secret |
| `DEEPSEEK_API_KEY` | (required) | DeepSeek API key for LLM/Embedding |

Backend-specific (set in `.env` or Docker Compose `environment`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | Full database DSN |
| `FILE_STORAGE_ROOT` | `/data/files` | File storage root path |
| `PROVIDER_CONFIG` | `config/providers.json` | Provider config path |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token TTL |
| `DEBUG` | `false` | Debug mode |

## Production Deployment

### Reverse Proxy (Traefik / Nginx)

Add an external reverse proxy for TLS termination:

```nginx
server {
    listen 443 ssl;
    server_name ontology.example.com;

    ssl_certificate     /etc/ssl/certs/example.com.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

### Horizontal Scaling

FastAPI is stateless — scale horizontally:

```yaml
# docker-compose.prod.yml
backend:
  build: ...
  deploy:
    replicas: 3
```

Add a load balancer (Traefik/Nginx) in front.

### Redis + Celery for Async Tasks

For production workloads (large file processing, batch sync):

```bash
docker compose --profile full up -d
```

Then start Celery workers:

```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

## Health Monitoring

```
GET /api/health
```

Response:
```json
{
  "code": 0,
  "data": {
    "status": "healthy",
    "database": "ok",
    "version": "0.1.0"
  }
}
```

## Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f postgres

# Last 100 lines
docker compose logs --tail=100 backend
```

## Troubleshooting

### PostgreSQL won't start

```bash
# Check if port 5432 is in use
lsof -i :5432

# Reset PostgreSQL data
docker compose down -v
docker compose up -d
```

### Backend can't connect to PostgreSQL

Check that `.env` has the correct `POSTGRES_PASSWORD` and that the `DATABASE_URL` in the backend service matches.

### File uploads fail

Ensure the `file_storage` volume is mounted and writable:

```bash
docker compose exec backend ls -la /data/files
```

### API returns 401

- Access tokens expire in 15 minutes. The frontend should auto-refresh.
- If refresh also fails, re-login at `/login`.

### Provider API key issues

Verify in `backend/config/providers.json` that `${env:VAR_NAME}` matches the variable set in `.env`.

## Directory Layout

```
ontology-platform/
├── backend/
│   ├── app/              # FastAPI application
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Security, response helpers
│   │   ├── models/       # Data models & stores
│   │   ├── providers/    # Provider interfaces + implementations
│   │   ├── rag/          # RAG pipeline (parsers, chunkers)
│   │   └── graphrag/     # GraphRAG pipeline
│   ├── config/           # Provider configuration JSON
│   ├── tests/            # Pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # Axios API client
│   │   ├── components/   # Shared React components
│   │   ├── pages/        # Page components (30+)
│   │   ├── stores/       # Zustand state stores
│   │   └── styles/       # Global CSS
│   └── package.json
├── docker/
│   ├── nginx.conf        # Nginx reverse proxy config
│   └── postgres/         # PostgreSQL init scripts
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── .env
```
