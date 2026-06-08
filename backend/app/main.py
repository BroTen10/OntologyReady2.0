from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.acr import router as acr_router
from .api.auth import router as auth_router
from .api.datasets import router as datasets_router
from .api.graphrag import router as graphrag_router
from .api.instances import router as instances_router
from .api.modeling import router as modeling_router
from .api.ontology import router as ontology_router
from .api.rag import router as rag_router
from .api.rag_evaluation import router as rag_eval_router
from .api.router import health_check
from .api.skills import router as skills_router
from .api.sync import router as sync_router
from .api.system_config import router as system_config_router
from .api.tasks import router as tasks_router
from .api.tokens import router as tokens_router
from .api.versioning import router as versioning_router
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from .database import init_db
        await init_db()
    except Exception:
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(acr_router)
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(ontology_router)
app.include_router(graphrag_router)
app.include_router(instances_router)
app.include_router(modeling_router)
app.include_router(rag_router)
app.include_router(rag_eval_router)
app.include_router(sync_router)
app.include_router(versioning_router)
app.include_router(skills_router)
app.include_router(system_config_router)
app.include_router(tasks_router)
app.include_router(tokens_router)


@app.get("/api/health")
async def health():
    return await health_check()
