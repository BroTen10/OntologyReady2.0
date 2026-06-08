from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.response import error, ok
from ..models import modeling_store
from ..models.modeling import (
    CompileRequest,
    DetectChangesRequest,
    QuickModelRequest,
    RegisterRequest,
    SchemaAnalyzeRequest,
    TestConnectionRequest,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/datasets/{dataset_id}/ontology/modeling", tags=["modeling"])


@router.post("/test-connection")
async def test_connection(body: TestConnectionRequest, _: dict = Depends(get_current_user)):
    result = await modeling_store.test_connection(body.model_dump())
    return ok(result)


@router.post("/analyze-schema")
async def analyze_schema(dataset_id: str, body: SchemaAnalyzeRequest, _: dict = Depends(get_current_user)):
    result = await modeling_store.analyze_schema(body.model_dump())
    return ok(result)


@router.post("/compile")
async def compile_ontology(dataset_id: str, body: CompileRequest, _: dict = Depends(get_current_user)):
    result = await modeling_store.compile_ontology(body.analysis_result)
    return ok(result)


@router.post("/register")
async def register_ontology(dataset_id: str, body: RegisterRequest, _: dict = Depends(get_current_user)):
    result = await modeling_store.register_ontology(dataset_id, body.compiled_ontology)
    return ok(result)


@router.post("/detect-changes")
async def detect_changes(dataset_id: str, body: DetectChangesRequest, _: dict = Depends(get_current_user)):
    result = await modeling_store.detect_changes(dataset_id, body.model_dump())
    return ok(result)


@router.post("/quick-model")
async def quick_model(dataset_id: str, body: QuickModelRequest, _: dict = Depends(get_current_user)):
    result = await modeling_store.quick_model(body.model_dump())
    return ok(result)
