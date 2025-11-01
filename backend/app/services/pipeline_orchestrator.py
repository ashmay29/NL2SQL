"""
Pipeline orchestrator for NL2SQL processing
Coordinates all Phase 3 & 4 services in a clean, testable way
"""
from typing import Dict, Any, List, Tuple, Optional
import logging
import time
import json
from app.services.schema_service import SchemaService
from app.services.llm_service import LLMService
from app.services.feedback_service import FeedbackService
from app.services.context_service import ContextService
from app.services.complexity_service import ComplexityService, ComplexityMetrics
from app.services.corrector_service import CorrectorService
from app.services.clarification_service import ClarificationService
from app.services.prompt_templates import build_compact_schema_text, build_ir_prompt
from app.services.ir_models import QueryIR
from app.services.ir_validator import IRValidator
from app.services.ir_compiler import IRToMySQLCompiler
from app.core.config import settings

logger = logging.getLogger(__name__)


class PipelineContext:
    """Context object for pipeline execution"""
    def __init__(
        self,
        query_text: str,
        conversation_id: str,
        database_id: str,
        use_rag: bool = True
    ):
        self.query_text = query_text
        self.conversation_id = conversation_id
        self.database_id = database_id
        self.use_rag = use_rag
        self.start_time = time.time()
        
        # Populated during pipeline execution
        self.schema: Optional[Dict[str, Any]] = None
        self.schema_fingerprint: str = "default"
        self.resolved_query: str = query_text
        self.ir: Optional[QueryIR] = None
        self.sql: str = ""
        self.complexity_metrics: Optional[ComplexityMetrics] = None
        self.errors_found: List[str] = []
        self.corrections_applied: List[str] = []
        self.explanations: List[str] = []
        self.suggested_fixes: List[str] = []
        self.confidence: float = 1.0
        self.ambiguities: List[Dict[str, Any]] = []


class PipelineOrchestrator:
    """Orchestrates the complete NL2SQL pipeline"""
    
    def __init__(
        self,
        schema_service: SchemaService,
        llm_service: LLMService,
        feedback_service: FeedbackService,
        context_service: ContextService,
        complexity_service: ComplexityService,
        corrector_service: CorrectorService,
        clarification_service: ClarificationService
    ):
        self.schema_service = schema_service
        self.llm_service = llm_service
        self.feedback_service = feedback_service
        self.context_service = context_service
        self.complexity_service = complexity_service
        self.corrector_service = corrector_service
        self.clarification_service = clarification_service
        logger.info("PipelineOrchestrator initialized")
    
    async def prepare_schema_and_context(self, ctx: PipelineContext) -> None:
        """Step 1: Load schema and prepare context"""
        try:
            # Get schema
            ctx.schema = self.schema_service.get_cached_schema(ctx.database_id)
            if not ctx.schema:
                ctx.schema = self.schema_service.extract_schema(ctx.database_id)
                self.schema_service.cache_schema(ctx.schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
            
            ctx.schema_fingerprint = ctx.schema.get("version", "default")
            
            # Resolve references from conversation context
            ctx.resolved_query = self.context_service.resolve_references(
                ctx.query_text, 
                ctx.conversation_id
            )
            
            logger.debug(f"Schema loaded for {ctx.database_id}, fingerprint: {ctx.schema_fingerprint[:12]}")
            
        except Exception as e:
            logger.error(f"Failed to prepare schema/context: {e}")
            raise
    
    async def generate_ir(self, ctx: PipelineContext) -> Dict[str, Any]:
        """Step 2: Generate IR with RAG and context"""
        try:
            # Build compact schema text
            schema_text = build_compact_schema_text(
                ctx.schema, 
                max_columns_per_table=settings.MAX_COLUMNS_IN_PROMPT
            )
            
            # Get RAG examples
            rag_examples = ""
            if ctx.use_rag:
                rag_examples = await self.feedback_service.build_rag_examples(
                    ctx.resolved_query,
                    ctx.schema_fingerprint,
                    max_examples=3
                )
            
            # Build conversation context
            context = self.context_service.build_context_prompt(
                ctx.conversation_id, 
                max_turns=2
            )
            
            # Build and execute prompt
            prompt = build_ir_prompt(schema_text, ctx.resolved_query, rag_examples, context)
            ir_json = self.llm_service.generate_json(prompt)

            # Log raw IR for debugging
            logger.debug(f"Raw IR from LLM: {json.dumps(ir_json, indent=2)[:500]}")

            # Sanitize/normalize IR JSON from provider to match our schema
            self._sanitize_ir_json(ir_json)
            logger.debug(f"Sanitized IR: {json.dumps(ir_json, indent=2)[:500]}")
            
            # Validate IR
            ctx.ir = QueryIR(**ir_json)
            errors = IRValidator(ctx.schema).validate(ctx.ir)
            
            ctx.confidence = float(ir_json.get("confidence", 1.0))
            ctx.ambiguities = ir_json.get("ambiguities", [])
            
            if errors:
                ctx.explanations.extend([f"Please clarify: {e}" for e in errors])
            
            logger.debug(f"IR generated with confidence: {ctx.confidence:.2f}")
            return ir_json
            
        except Exception as e:
            logger.error(f"Failed to generate IR: {e}")
            raise

    def _sanitize_ir_json(self, ir_json: Dict[str, Any]) -> None:
        """
        Normalize provider output to conform to QueryIR expectations.
        - order_by[].column: map from 'value' if provider used a different key
        - order_by[].column: also map from 'field' if provider used that key
        - order_by[].column: also map from 'col' if provider used that key
        - order_by[].direction: uppercase and coerce to 'ASC'|'DESC' (default 'ASC')
        - select: if list contains strings, convert to Expression dicts {type:'column', value:str}
        - ctes[]: map 'cte_name' -> 'name', 'cte_query' -> 'query'
        - joins[]: map 'join_type' -> 'type'; if 'on' is a string like "a = b", coerce into Predicate list
        - future: add more normalizations as needed
        Modifies ir_json in place.
        """
        try:
            # Normalize SELECT list
            select = ir_json.get("select")
            if isinstance(select, list):
                normalized_select = []
                for item in select:
                    if isinstance(item, str):
                        normalized_select.append({"type": "column", "value": item})
                    elif isinstance(item, dict):
                        # If provider used {'column': 't.col', 'alias': '...'} shape
                        if "type" not in item and "column" in item:
                            expr = {"type": "column", "value": item.get("column")}
                            if "alias" in item:
                                expr["alias"] = item["alias"]
                            normalized_select.append(expr)
                        # If provider used {'value': '...', 'alias': '...'} but forgot 'type'
                        elif "type" not in item and "value" in item:
                            # Infer type based on other fields
                            if item.get("function") or item.get("aggregation"):
                                item["type"] = "aggregate"
                            elif item.get("window"):
                                item["type"] = "window"
                            elif item.get("subquery"):
                                item["type"] = "subquery"
                            else:
                                item["type"] = "column"
                            normalized_select.append(item)
                        else:
                            normalized_select.append(item)
                    else:
                        normalized_select.append(item)
                ir_json["select"] = normalized_select

            order_by = ir_json.get("order_by")
            if isinstance(order_by, list):
                for item in order_by:
                    if isinstance(item, dict):
                        # Map 'value' -> 'column' if necessary
                        if "column" not in item and "value" in item:
                            item["column"] = item.pop("value")
                        # Or map 'field' -> 'column'
                        if "column" not in item and "field" in item:
                            item["column"] = item.pop("field")
                        # Or map 'col' -> 'column'
                        if "column" not in item and "col" in item:
                            item["column"] = item.pop("col")
                        # Uppercase direction and validate
                        direction = item.get("direction")
                        if isinstance(direction, str):
                            up = direction.upper()
                            item["direction"] = "DESC" if up == "DESC" else "ASC"
                        else:
                            # Default to ASC if missing/invalid
                            item["direction"] = "ASC"
            
            # Normalize CTEs
            ctes = ir_json.get("ctes")
            if isinstance(ctes, list):
                for cte in ctes:
                    if isinstance(cte, dict):
                        # Map name variants
                        if "name" not in cte and "cte_name" in cte:
                            cte["name"] = cte.pop("cte_name")
                        # Map query variants
                        if "query" not in cte:
                            if "cte_query" in cte:
                                cte["query"] = cte.pop("cte_query")
                            elif "cte_definition" in cte:
                                cte["query"] = cte.pop("cte_definition")
                            elif "definition" in cte:
                                cte["query"] = cte.pop("definition")

            # Normalize JOINs
            joins = ir_json.get("joins")
            if isinstance(joins, list):
                for j in joins:
                    if isinstance(j, dict):
                        # Map type variants
                        if "type" not in j and "join_type" in j:
                            raw = str(j.pop("join_type"))
                            up = raw.upper().replace(" JOIN", "").replace("JOIN", "").strip()
                            if up not in {"INNER", "LEFT", "RIGHT", "FULL", "CROSS"}:
                                up = "INNER"
                            j["type"] = up
                        # Map table variants
                        if "table" not in j:
                            if "target_table" in j:
                                j["table"] = j.pop("target_table")
                            elif "join_table" in j:
                                j["table"] = j.pop("join_table")
                        # Map on/condition variants
                        if "on" not in j:
                            if "condition" in j:
                                j["on"] = j.pop("condition")
                            elif "join_condition" in j:
                                j["on"] = j.pop("join_condition")
                        # Coerce 'on' from string into a Predicate list when possible
                        on_clause = j.get("on")
                        if isinstance(on_clause, str):
                            pred = self._parse_simple_on_clause(on_clause)
                            if pred:
                                j["on"] = [pred]
                        # Ensure 'on' is at least a list
                        if isinstance(j.get("on"), dict):
                            j["on"] = [j["on"]]
        except Exception as e:
            # Non-fatal: log and continue; validator may still catch issues
            logger.warning(f"IR sanitize step encountered an issue: {e}")
        
    def _parse_simple_on_clause(self, clause: str) -> Optional[Dict[str, Any]]:
        """
        Parse very simple ON clauses like "a.col = b.col" or "a.col>=b.col" into
        a Predicate dict compatible with IR schema. Best-effort only.
        """
        try:
            # Supported operators ordered by length to avoid partial splits
            operators = [
                ">=",
                "<=",
                "!=",
                "=",
                ">",
                "<",
            ]
            clause_no_spaces = clause.strip()
            for op in operators:
                if op in clause_no_spaces:
                    left, right = clause_no_spaces.split(op, 1)
                    left = left.strip()
                    right = right.strip()
                    if left and right:
                        return {
                            "left": {"type": "column", "value": left},
                            "operator": op,
                            "right": {"type": "column", "value": right},
                            "conjunction": "AND",
                        }
            return None
        except Exception:
            return None

    def check_clarification_needed(self, ctx: PipelineContext) -> Optional[List[str]]:
        """Step 3: Check if clarification is needed"""
        try:
            if not settings.IR_ADVANCED_FEATURES_ENABLED:
                return None
            
            needs_clarification = self.clarification_service.needs_clarification(
                ctx.ir,
                ctx.confidence,
                ctx.ambiguities
            )
            
            if needs_clarification:
                clarification_questions = self.clarification_service.generate_questions(
                    ctx.query_text,
                    ctx.ir,
                    ctx.schema,
                    ctx.ambiguities
                )
                
                if clarification_questions:
                    formatted_questions = self.clarification_service.format_questions_for_user(
                        clarification_questions
                    )
                    logger.info(f"Clarification needed for query: {ctx.query_text[:50]}...")
                    return formatted_questions
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check clarification: {e}")
            return None
    
    def compile_and_analyze_sql(self, ctx: PipelineContext) -> None:
        """Step 4: Compile IR to SQL and analyze"""
        try:
            # Compile IR to SQL
            ctx.sql, params = IRToMySQLCompiler().compile(ctx.ir)
            
            # Analyze complexity
            ctx.complexity_metrics = self.complexity_service.analyze(ctx.ir, ctx.schema)
            optimization_suggestions = self.complexity_service.suggest_optimizations(ctx.complexity_metrics)
            
            # Check and correct SQL
            corrected_sql, ctx.errors_found, ctx.corrections_applied = self.corrector_service.check_and_correct(
                ctx.sql,
                ctx.ir,
                ctx.schema
            )
            
            # Use corrected SQL if corrections were applied
            if ctx.corrections_applied:
                ctx.sql = corrected_sql
                logger.info(f"Applied {len(ctx.corrections_applied)} corrections to SQL")
            
            # Build explanations and suggestions
            if ctx.complexity_metrics.warnings:
                ctx.explanations.extend([f"Performance note: {w}" for w in ctx.complexity_metrics.warnings])
            if ctx.errors_found:
                ctx.explanations.extend([f"Note: {e}" for e in ctx.errors_found])
            
            if ctx.corrections_applied:
                ctx.suggested_fixes.extend(ctx.corrections_applied)
            if optimization_suggestions:
                ctx.suggested_fixes.extend(optimization_suggestions)
            
            logger.debug(f"SQL compiled, complexity: {ctx.complexity_metrics.level}")
            
        except Exception as e:
            logger.error(f"Failed to compile/analyze SQL: {e}")
            raise
    
    def save_context(self, ctx: PipelineContext) -> None:
        """Step 5: Save conversation context"""
        try:
            # Extract tables used for context tracking
            tables_used = [ctx.ir.from_table]
            if ctx.ir.joins:
                # ctx.ir.joins is a list of Join objects
                tables_used.extend([j.table for j in ctx.ir.joins])
            
            # Add to conversation context
            self.context_service.add_turn(
                ctx.conversation_id,
                ctx.query_text,
                ctx.sql,
                ctx.ir.dict(),
                tables_used
            )
            
            logger.debug(f"Context saved for conversation: {ctx.conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save context: {e}")
            # Non-critical error, don't raise
    
    async def execute_pipeline(self, ctx: PipelineContext) -> Tuple[PipelineContext, Optional[List[str]]]:
        """
        Execute the complete NL2SQL pipeline
        
        Returns:
            (context, clarification_questions)
            If clarification_questions is not None, pipeline stopped for clarification
        """
        try:
            # Step 1: Prepare schema and context
            await self.prepare_schema_and_context(ctx)
            
            # Step 2: Generate IR
            await self.generate_ir(ctx)
            
            # Step 3: Check clarification
            clarification_questions = self.check_clarification_needed(ctx)
            if clarification_questions:
                return ctx, clarification_questions
            
            # Step 4: Compile and analyze SQL
            self.compile_and_analyze_sql(ctx)
            
            # Step 5: Save context
            self.save_context(ctx)
            
            execution_time = time.time() - ctx.start_time
            logger.info(
                f"Pipeline completed: query='{ctx.query_text[:50]}...', "
                f"confidence={ctx.confidence:.2f}, "
                f"complexity={ctx.complexity_metrics.level}, "
                f"time={execution_time:.2f}s"
            )
            
            return ctx, None
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            raise
