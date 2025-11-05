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
    get_clarification_service, get_pipeline_orchestrator
)
from app.services.pipeline_orchestrator import PipelineOrchestrator, PipelineContext
from app.services.prompt_templates import build_compact_schema_text, build_ir_prompt
from app.core.logging_utils import api_logger
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


# Prompt building functions moved to app.services.prompt_templates


@router.post("/nl2ir", response_model=NL2IRResponse)
async def nl2ir(
    req: NL2IRRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    llm: LLMService = Depends(get_llm_service),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    context_service: ContextService = Depends(get_context_service),
    orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator),
    use_rag: bool = True
):
    try:
        # Get schema
        schema = schema_service.get_cached_schema(req.database_id or "nl2sql_target")
        if not schema:
            schema = schema_service.extract_schema(req.database_id or "nl2sql_target")
            schema_service.cache_schema(schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
        
        schema_fingerprint = schema.get("version", "default")
        
        # Phase 4: Resolve references from conversation context
        conversation_id = req.conversation_id or "default"
        resolved_query = context_service.resolve_references(req.query_text, conversation_id)
        
        # NEW: Use GNN to prune schema (like your training code)
        gnn_top_nodes = None
        try:
            from app.core.dependencies import get_gnn_ranker_service
            
            if settings.USE_LOCAL_GNN:
                gnn_service = get_gnn_ranker_service()
                gnn_top_nodes = await gnn_service.score_schema_nodes(
                    query=resolved_query,
                    backend_schema=schema,
                    top_k=15  # Top 15 relevant nodes
                )
                logger.info(f"GNN scored {len(gnn_top_nodes)} relevant schema nodes")
        except Exception as e:
            logger.warning(f"GNN schema pruning failed, using full schema: {e}")
            gnn_top_nodes = None
        
        # Use compact schema to avoid model context overflows/timeouts
        schema_text = build_compact_schema_text(
            schema, 
            max_columns_per_table=settings.MAX_COLUMNS_IN_PROMPT,
            gnn_top_nodes=gnn_top_nodes  # NEW: GNN-pruned schema
        )

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
        # Sanitize/normalize provider IR to match our schema (reuse pipeline sanitizer)
        try:
            orchestrator._sanitize_ir_json(ir_json)  # type: ignore[attr-defined]
        except Exception as _e:
            logger.debug(f"IR sanitization skipped/failed with: {_e}")

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
async def ir2sql(req: IR2SQLRequest, orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator)):
    try:
        # Make a mutable copy and sanitize before validation/compilation
        ir_payload: Dict[str, Any] = dict(req.ir)
        try:
            orchestrator._sanitize_ir_json(ir_payload)  # type: ignore[attr-defined]
        except Exception as _e:
            logger.debug(f"IR sanitization skipped/failed with: {_e}")

        ir = QueryIR(**ir_payload)
        sql, params = IRToMySQLCompiler().compile(ir)
        return IR2SQLResponse(sql=sql, params=params)
    except Exception as e:
        logger.error(f"IR->SQL failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/nl2sql", response_model=NL2SQLResponse)
async def nl2sql(
    req: NL2SQLRequest,
    orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator),
):
    """
    Full NL2SQL pipeline with Phase 3 & 4 enhancements:
    - Phase 3: RAG feedback integration
    - Phase 4: Context, complexity analysis, correction, clarification
    
    For CSV/Excel uploads, use database_id='uploaded_data'
    For MySQL databases, use database_id='your_database_name'
    """
    conversation_id = req.conversation_id or "default"
    database_id = req.database_id or "uploaded_data"  # Changed default from nl2sql_target
    
    try:
        # Create pipeline context
        ctx = PipelineContext(
            query_text=req.query_text,
            conversation_id=conversation_id,
            database_id=database_id,
            use_rag=req.use_cache  # Reuse cache flag for RAG
        )
        
        # Execute pipeline
        ctx, clarification_questions = await orchestrator.execute_pipeline(ctx)
        
        # Handle clarification if needed
        if clarification_questions:
            api_logger.info(
                "Clarification needed",
                conversation_id=conversation_id,
                database_id=database_id,
                confidence=ctx.confidence
            )
            return NL2SQLResponse(
                original_question=req.query_text,
                resolved_question=req.query_text,
                sql="",  # No SQL yet, need clarification
                ir=ctx.ir.dict() if ctx.ir else {},
                confidence=ctx.confidence,
                ambiguities=ctx.ambiguities,
                explanations=clarification_questions,
                suggested_fixes=["Please answer the clarification questions above"],
                cache_hit=False,
                execution_time=time.time() - ctx.start_time,
            )
        
        # Build final response
        execution_time = time.time() - ctx.start_time
        
        api_logger.info(
            "NL2SQL completed",
            conversation_id=conversation_id,
            database_id=database_id,
            confidence=ctx.confidence,
            complexity=ctx.complexity_metrics.level if ctx.complexity_metrics else "unknown",
            execution_time=execution_time,
            params_count=len(ctx.params)
        )
        
        return NL2SQLResponse(
            original_question=req.query_text,
            resolved_question=ctx.resolved_query,
            sql=ctx.sql,
            params=ctx.params,  # Use params from context
            ir=ctx.ir.dict() if ctx.ir else {},
            confidence=ctx.confidence,
            ambiguities=ctx.ambiguities,
            explanations=ctx.explanations,
            suggested_fixes=ctx.suggested_fixes,
            cache_hit=False,
            execution_time=execution_time,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(
            "NL2SQL pipeline failed",
            error=e,
            conversation_id=conversation_id,
            database_id=database_id
        )
        raise HTTPException(status_code=400, detail=str(e))
