"""
NL2SQL endpoints: NL->IR, IR->SQL, NL->SQL with Phase 3 & 4 enhancements
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from app.models.schemas import (
    NL2IRRequest, NL2IRResponse,
    IR2SQLRequest, IR2SQLResponse,
    NL2SQLRequest, NL2SQLResponse,
)
from app.core.dependencies import (
    get_schema_service, get_llm_service, get_feedback_service,
    get_context_service, get_complexity_service, get_corrector_service,
    get_clarification_service
)
from app.services.schema_service import SchemaService
from app.services.llm_service import LLMService
from app.services.feedback_service import FeedbackService
from app.services.context_service import ContextService
from app.services.complexity_service import ComplexityService
from app.services.corrector_service import CorrectorService
from app.services.clarification_service import ClarificationService
from app.services.ir_models import QueryIR
from app.services.ir_validator import IRValidator
from app.services.ir_compiler import IRToMySQLCompiler
from app.core.config import settings
import json
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter()


def build_compact_schema_text(schema: Dict[str, Any], max_columns_per_table: int = 12) -> str:
    """Build a compact schema string: only table and column names to minimize context size."""
    lines = [f"Database: {schema.get('database', 'unknown')}"]
    tables: Dict[str, Any] = schema.get("tables", {})
    for tname, tinfo in tables.items():
        cols = [c.get("name") for c in tinfo.get("columns", [])]
        if len(cols) > max_columns_per_table:
            shown = cols[:max_columns_per_table]
            shown.append(f"... (+{len(cols) - max_columns_per_table} more)")
            cols = shown
        lines.append(f"- {tname}: {', '.join(cols)}")
    return "\n".join(lines)


def build_ir_prompt(
    schema_text: str,
    user_query: str,
    rag_examples: str = "",
    context: str = ""
) -> str:
    """Prompt template to request IR JSON with RAG and context"""
    prompt_parts = [
        "You are an expert NL2SQL assistant. Convert the user's question into a JSON Intermediate Representation (IR) for MySQL.",
        "",
        "Return ONLY valid JSON. Do not include explanations.",
        "",
        "Schema:",
        schema_text,
    ]
    
    if rag_examples:
        prompt_parts.extend([
            "",
            "Similar past queries (for reference):",
            rag_examples,
        ])
    
    if context:
        prompt_parts.extend([
            "",
            context,
        ])
    
    prompt_parts.extend([
        "",
        "User Question:",
        user_query,
        "",
        "Constraints:",
        "- Use fields: ctes, select, from_table, joins, where, group_by, having, order_by, limit, offset, parameters",
        "- Use column references as table.column when ambiguous",
        "- Prefer safe parameters in 'parameters' for literal values",
        "- If ambiguity exists, include an 'ambiguities' array with notes and set 'confidence' < 0.8",
        "- Return IR as JSON with structure: {\"select\": [...], \"from_table\": \"...\", ...}",
    ])
    
    return "\n".join(prompt_parts)


@router.post("/nl2ir", response_model=NL2IRResponse)
async def nl2ir(
    req: NL2IRRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    llm: LLMService = Depends(get_llm_service),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    context_service: ContextService = Depends(get_context_service),
    use_rag: bool = True
):
    try:
        # Get schema
        schema = schema_service.get_cached_schema(req.database_id or "nl2sql_target")
        if not schema:
            schema = schema_service.extract_schema(req.database_id or "nl2sql_target")
            schema_service.cache_schema(schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
        
        schema_fingerprint = schema.get("version", "default")
        
        # Use compact schema to avoid model context overflows/timeouts
        schema_text = build_compact_schema_text(schema, max_columns_per_table=settings.MAX_COLUMNS_IN_PROMPT)

        # Phase 4: Resolve references from conversation context
        conversation_id = req.conversation_id or "default"
        resolved_query = context_service.resolve_references(req.query_text, conversation_id)
        
        # Phase 3: Get RAG examples from feedback
        rag_examples = ""
        if use_rag:
            rag_examples = await feedback_service.build_rag_examples(
                resolved_query,
                schema_fingerprint,
                max_examples=3
            )
        
        # Phase 4: Build context from conversation history
        context = context_service.build_context_prompt(conversation_id, max_turns=2)

        # Build prompt with RAG and context
        prompt = build_ir_prompt(schema_text, resolved_query, rag_examples, context)

        # Generate IR JSON (use configured provider)
        ir_json: Dict[str, Any] = llm.generate_json(prompt)

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
            conversation_id=conversation_id,
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
    feedback_service: FeedbackService = Depends(get_feedback_service),
    context_service: ContextService = Depends(get_context_service),
    complexity_service: ComplexityService = Depends(get_complexity_service),
    corrector_service: CorrectorService = Depends(get_corrector_service),
    clarification_service: ClarificationService = Depends(get_clarification_service),
):
    """
    Full NL2SQL pipeline with Phase 3 & 4 enhancements:
    - Phase 3: RAG feedback integration
    - Phase 4: Context, complexity analysis, correction, clarification
    """
    start_time = time.time()
    
    try:
        conversation_id = req.conversation_id or "default"
        database_id = req.database_id or "nl2sql_target"
        
        # Get schema
        schema = schema_service.get_cached_schema(database_id)
        if not schema:
            schema = schema_service.extract_schema(database_id)
            schema_service.cache_schema(schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
        
        schema_fingerprint = schema.get("version", "default")
        
        # Phase 3 & 4: NL -> IR with RAG and context
        ir_resp = await nl2ir(
            NL2IRRequest(
                query_text=req.query_text,
                conversation_id=conversation_id,
                database_id=database_id,
            ),
            schema_service=schema_service,
            llm=llm,
            feedback_service=feedback_service,
            context_service=context_service,
            use_rag=True
        )

        # Phase 4: Check if clarification is needed
        ir = QueryIR(**ir_resp.ir)
        needs_clarification = clarification_service.needs_clarification(
            ir,
            ir_resp.confidence,
            ir_resp.ambiguities
        )
        
        if needs_clarification and settings.IR_ADVANCED_FEATURES_ENABLED:
            # Generate clarification questions
            clarification_questions = clarification_service.generate_questions(
                req.query_text,
                ir,
                schema,
                ir_resp.ambiguities
            )
            
            if clarification_questions:
                formatted_questions = clarification_service.format_questions_for_user(
                    clarification_questions
                )
                
                logger.info(f"Clarification needed for query: {req.query_text[:50]}...")
                
                # Return response with clarification questions
                return NL2SQLResponse(
                    original_question=req.query_text,
                    resolved_question=req.query_text,
                    sql="",  # No SQL yet, need clarification
                    ir=ir.dict(),
                    confidence=ir_resp.confidence,
                    ambiguities=ir_resp.ambiguities,
                    explanations=formatted_questions,
                    suggested_fixes=["Please answer the clarification questions above"],
                    cache_hit=False,
                    execution_time=time.time() - start_time,
                )

        # IR -> SQL
        sql, params = IRToMySQLCompiler().compile(ir)

        # Phase 4: Analyze complexity
        complexity_metrics = complexity_service.analyze(ir, schema)
        optimization_suggestions = complexity_service.suggest_optimizations(complexity_metrics)
        
        # Phase 4: Check and correct SQL
        corrected_sql, errors_found, corrections_applied = corrector_service.check_and_correct(
            sql,
            ir,
            schema
        )
        
        # Use corrected SQL if corrections were applied
        if corrections_applied:
            sql = corrected_sql
            logger.info(f"Applied {len(corrections_applied)} corrections to SQL")
        
        # Extract tables used for context tracking
        tables_used = [ir.from_table]
        if ir.joins:
            tables_used.extend([j.get("table") for j in ir.joins])
        
        # Phase 4: Add to conversation context
        context_service.add_turn(
            conversation_id,
            req.query_text,
            sql,
            ir.dict(),
            tables_used
        )
        
        # Build explanations
        explanations = []
        if ir_resp.questions:
            explanations.extend(ir_resp.questions)
        if complexity_metrics.warnings:
            explanations.extend([f"Performance note: {w}" for w in complexity_metrics.warnings])
        if errors_found:
            explanations.extend([f"Note: {e}" for e in errors_found])
        
        # Build suggested fixes
        suggested_fixes = []
        if corrections_applied:
            suggested_fixes.extend(corrections_applied)
        if optimization_suggestions:
            suggested_fixes.extend(optimization_suggestions)
        
        execution_time = time.time() - start_time
        
        logger.info(
            f"NL2SQL completed: query='{req.query_text[:50]}...', "
            f"confidence={ir_resp.confidence:.2f}, "
            f"complexity={complexity_metrics.level}, "
            f"time={execution_time:.2f}s"
        )
        
        return NL2SQLResponse(
            original_question=req.query_text,
            resolved_question=context_service.resolve_references(req.query_text, conversation_id),
            sql=sql,
            ir=ir.dict(),
            confidence=ir_resp.confidence,
            ambiguities=ir_resp.ambiguities,
            explanations=explanations,
            suggested_fixes=suggested_fixes,
            cache_hit=False,
            execution_time=execution_time,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NL->SQL failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
