"""
NL2SQL endpoints: NL->IR, IR->SQL, NL->SQL
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.models.schemas import (
    NL2IRRequest, NL2IRResponse,
    IR2SQLRequest, IR2SQLResponse,
    NL2SQLRequest, NL2SQLResponse,
)
from app.core.dependencies import get_schema_service, get_llm_service
from app.services.schema_service import SchemaService
from app.services.llm_service import LLMService
from app.services.ir_models import QueryIR
from app.services.ir_validator import IRValidator
from app.services.ir_compiler import IRToMySQLCompiler
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def build_ir_prompt(schema_text: str, user_query: str, examples: str = "") -> str:
    """Prompt template to request IR JSON only"""
    return f"""
You are an expert NL2SQL assistant. Convert the user's question into a JSON Intermediate Representation (IR) for MySQL.

Return ONLY valid JSON. Do not include explanations.

Schema:
{schema_text}

Examples (IR JSON):
{examples}

User Question:
{user_query}

Constraints:
- Use fields: ctes, select, from_table, joins, where, group_by, having, order_by, limit, offset, parameters
- Use column references as table.column when ambiguous
- Prefer safe parameters in 'parameters' for literal values
- If ambiguity exists, include an 'ambiguities' array with notes and set 'confidence' < 0.8
"""


@router.post("/nl2ir", response_model=NL2IRResponse)
async def nl2ir(
    req: NL2IRRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    llm: LLMService = Depends(get_llm_service),
):
    try:
        # Get schema
        schema = schema_service.get_cached_schema(req.database_id or "nl2sql_target")
        if not schema:
            schema = schema_service.extract_schema(req.database_id or "nl2sql_target")
            schema_service.cache_schema(schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
        schema_text = schema_service.get_schema_text(schema)

        # Build prompt
        prompt = build_ir_prompt(schema_text, req.query_text)

        # Generate IR JSON via Ollama (provider default is configured to ollama)
        ir_json: Dict[str, Any] = llm.generate_json(prompt, provider_override="ollama")

        # Validate IR
        ir = QueryIR(**ir_json)
        errors = IRValidator(schema).validate(ir)
        ambiguities = ir_json.get("ambiguities", [])
        questions = []
        if errors:
            questions = [f"Please clarify: {e}" for e in errors]

        confidence = float(ir_json.get("confidence", 1.0))
        return NL2IRResponse(
            ir=ir.dict(),
            confidence=confidence,
            ambiguities=ambiguities,
            questions=questions,
            conversation_id=req.conversation_id or "default",
        )
    except Exception as e:
        logger.error(f"NL->IR failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ir2sql", response_model=IR2SQLResponse)
async def ir2sql(req: IR2SQLRequest):
    try:
        ir = QueryIR(**req.ir)
        sql, params = IRToMySQLCompiler().compile(ir)
        return IR2SQLResponse(sql=sql, params=params)
    except Exception as e:
        logger.error(f"IR->SQL failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/nl2sql", response_model=NL2SQLResponse)
async def nl2sql(
    req: NL2SQLRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    llm: LLMService = Depends(get_llm_service),
):
    try:
        # NL -> IR
        ir_resp = await nl2ir(
            NL2IRRequest(
                query_text=req.query_text,
                conversation_id=req.conversation_id,
                database_id=req.database_id,
            ),
            schema_service=schema_service,
            llm=llm,
        )

        # IR -> SQL
        ir = QueryIR(**ir_resp.ir)
        sql, params = IRToMySQLCompiler().compile(ir)

        return NL2SQLResponse(
            original_question=req.query_text,
            resolved_question=req.query_text,
            sql=sql,
            ir=ir.dict(),
            confidence=ir_resp.confidence,
            ambiguities=ir_resp.ambiguities,
            explanations=ir_resp.questions,
            suggested_fixes=[],
            cache_hit=False,
            execution_time=0.0,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NL->SQL failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
