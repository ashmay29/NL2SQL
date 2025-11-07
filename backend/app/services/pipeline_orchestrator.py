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
        self.params: Dict[str, Any] = {}  # SQL parameters for parameterized queries
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
            # Get schema from cache first
            ctx.schema = self.schema_service.get_cached_schema(ctx.database_id)
            
            # If not cached and MySQL is available, extract from database
            if not ctx.schema and self.schema_service.inspector:
                try:
                    ctx.schema = self.schema_service.extract_schema(ctx.database_id)
                    self.schema_service.cache_schema(ctx.schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
                except Exception as db_error:
                    logger.warning(f"MySQL schema extraction failed for {ctx.database_id}: {db_error}")
                    raise RuntimeError(
                        f"No schema found for database '{ctx.database_id}'. "
                        "Please upload a CSV/Excel file first using /api/v1/data/upload/csv endpoint, "
                        "or ensure the MySQL database exists and is accessible."
                    )
            elif not ctx.schema:
                # MySQL not available and no cached schema
                raise RuntimeError(
                    f"No schema found for database '{ctx.database_id}'. "
                    "Please upload a CSV/Excel file first using /api/v1/data/upload/csv endpoint. "
                    "After upload, use database_id='uploaded_data' in your NL2SQL request."
                )
            
            ctx.schema_fingerprint = ctx.schema.get("version") or ctx.schema.get("fingerprint", "default")
            
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
            # Get GNN ranker service if available (local GNN model)
            gnn_top_nodes = None
            try:
                from app.core.dependencies import get_gnn_ranker_service
                from app.core.config import settings
                
                if settings.USE_LOCAL_GNN:
                    gnn_service = get_gnn_ranker_service()
                    # Score schema nodes using GNN with increased top-k
                    gnn_top_nodes = await gnn_service.score_schema_nodes(
                        query=ctx.resolved_query,
                        backend_schema=ctx.schema,
                        top_k=50  # Increased to 50 for better coverage
                    )
                    logger.info(f"GNN scored {len(gnn_top_nodes)} relevant schema nodes for query")
                    
                    # HYBRID APPROACH: Add keyword fallback for critical tables/columns
                    gnn_top_nodes = self._apply_keyword_fallback(
                        ctx.resolved_query, 
                        ctx.schema, 
                        gnn_top_nodes
                    )
                    
                    # Log detailed GNN scores for visibility
                    print("\n" + "="*80)
                    print("🧠 GNN SCHEMA NODE SCORES (with Intelligent Fallback)")
                    print("="*80)
                    for i, node in enumerate(gnn_top_nodes, 1):
                        node_type = "📊 TABLE" if node['node_type'] == 'table' else "📝 COLUMN"
                        auto_added = "🤖" if node.get('auto_added', False) else "  "
                        reason = f" | {node.get('reason', '')}" if node.get('auto_added', False) else ""
                        print(f"#{i:2d} {auto_added} [{node_type}] {node['node_name']:30s} | Score: {node['score']:.10f}{reason}")
                    print("="*80 + "\n")
                    
            except Exception as e:
                logger.warning(f"GNN schema pruning failed, using full schema: {e}")
                gnn_top_nodes = None
            
            # Build compact schema text (pruned by GNN if available)
            schema_text = build_compact_schema_text(
                ctx.schema, 
                max_columns_per_table=settings.MAX_COLUMNS_IN_PROMPT,
                gnn_top_nodes=gnn_top_nodes  # NEW: Pass GNN results for pruning
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
            
            # Log the final IR prompt for visibility
            print("\n" + "="*80)
            print("📋 FINAL IR PROMPT SENT TO LLM")
            print("="*80)
            print(prompt)
            print("="*80 + "\n")
            
            logger.debug(f"IR Prompt: {prompt[:500]}")  # Log first 500 chars
            ir_json = self.llm_service.generate_json(prompt)

            # Log raw IR for debugging
            logger.info(f"📋 Raw IR from LLM: {json.dumps(ir_json, indent=2)}")

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
                            # Normalize args for aggregates/functions
                            if item["type"] in ("aggregate", "function"):
                                args = item.get("args", [])
                                if isinstance(args, list):
                                    normalized_args = []
                                    for arg in args:
                                        if isinstance(arg, str):
                                            normalized_args.append({"type": "column", "value": arg})
                                        elif isinstance(arg, dict):
                                            normalized_args.append(arg)
                                        else:
                                            normalized_args.append({"type": "literal", "value": arg})
                                    item["args"] = normalized_args
                            normalized_select.append(item)
                        else:
                            # For items with type already set or inferred from function field
                            # Infer type if missing but function field exists
                            if "type" not in item and item.get("function"):
                                item["type"] = "aggregate"
                            
                            # For aggregate/function types, ensure args are Expression objects
                            if item.get("type") in ("aggregate", "function"):
                                # Add value field if missing (required by Expression model)
                                if "value" not in item:
                                    item["value"] = item.get("function", "")
                                # Normalize args: convert strings to Expression dicts
                                args = item.get("args", [])
                                if isinstance(args, list):
                                    normalized_args = []
                                    for arg in args:
                                        if isinstance(arg, str):
                                            # Handle special case for '*' in COUNT(*)
                                            if arg == "*":
                                                normalized_args.append({"type": "column", "value": "*"})
                                            else:
                                                normalized_args.append({"type": "column", "value": arg})
                                        elif isinstance(arg, dict):
                                            normalized_args.append(arg)
                                        else:
                                            normalized_args.append({"type": "literal", "value": arg})
                                    item["args"] = normalized_args
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
            
            # Normalize WHERE clause - handle OR/AND compound conditions
            where = ir_json.get("where")
            if where:
                # If WHERE is a single dict with type='or' or type='and', expand it
                if isinstance(where, dict) and where.get("type") in ("or", "and"):
                    # Convert compound condition to list of predicates with proper conjunction
                    conjunction = where.get("type").upper()  # 'OR' or 'AND'
                    args = where.get("args", [])
                    
                    # Convert args to proper predicate format
                    predicates = []
                    for arg in args:
                        if isinstance(arg, dict) and "left" in arg and "operator" in arg:
                            # Already a predicate
                            if "conjunction" not in arg and len(predicates) > 0:
                                arg["conjunction"] = conjunction
                            predicates.append(arg)
                    
                    ir_json["where"] = predicates
                elif not isinstance(where, list):
                    # Single predicate, wrap in list
                    ir_json["where"] = [where]
            
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
            ctx.sql, ctx.params = IRToMySQLCompiler().compile(ctx.ir)
            
            # Log parameters for visibility
            if ctx.params:
                print("\n" + "="*80)
                print("📋 SQL PARAMETERS")
                print("="*80)
                for key, value in ctx.params.items():
                    value_display = f'"{value}"' if isinstance(value, str) else str(value)
                    print(f"  {key}: {value_display}")
                print("="*80 + "\n")
            
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
            
            logger.debug(f"SQL compiled with {len(ctx.params)} parameters, complexity: {ctx.complexity_metrics.level}")
            
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
    
    def _apply_keyword_fallback(
        self, 
        query: str, 
        schema: Dict[str, Any], 
        gnn_nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        INTELLIGENT SCHEMA-AWARE FALLBACK: Automatically detects missing critical nodes
        based on schema structure, column types, and query patterns WITHOUT manual keywords.
        
        Strategy:
        1. Detect tables already included by GNN
        2. Find related tables via foreign keys that are missing
        3. For aggregation queries, ensure critical calculation columns (dates, numbers)
        4. For grouping queries ("per X"), ensure JOIN columns and dimensions
        
        Args:
            query: User's natural language query
            schema: Full database schema
            gnn_nodes: GNN-ranked nodes
        
        Returns:
            Enhanced node list with intelligently added critical nodes
        """
        query_lower = query.lower()
        tables_dict = schema.get('tables', {})
        
        # Get currently included tables and columns
        included_tables = set()
        included_columns = {}  # {table: [columns]}
        existing_node_ids = {node.get('node_id') for node in gnn_nodes}
        
        for node in gnn_nodes:
            node_id = node.get('node_id', '')
            if node_id.startswith('table:'):
                table = node_id.replace('table:', '')
                included_tables.add(table)
            elif node_id.startswith('column:'):
                parts = node_id.replace('column:', '').split('.')
                if len(parts) == 2:
                    table, col = parts
                    included_tables.add(table)
                    if table not in included_columns:
                        included_columns[table] = []
                    included_columns[table].append(col)
        
        additional_nodes = []
        
        # STRATEGY 1: Add related tables via foreign key relationships
        additional_nodes.extend(self._add_related_tables_via_fk(
            included_tables, schema, existing_node_ids, tables_dict
        ))
        
        # STRATEGY 2: For aggregation/calculation queries, ensure measurement columns
        if any(word in query_lower for word in ['average', 'avg', 'mean', 'sum', 'total', 'count', 'duration', 'length', 'period', 'stay']):
            additional_nodes.extend(self._add_calculation_columns(
                included_tables, included_columns, schema, existing_node_ids, tables_dict, query_lower
            ))
        
        # STRATEGY 3: For grouping queries, ensure grouping dimension columns and JOIN keys
        if any(word in query_lower for word in ['per', 'by', 'each', 'group']):
            additional_nodes.extend(self._add_grouping_dimensions(
                included_tables, included_columns, schema, existing_node_ids, tables_dict, query_lower
            ))
        
        # Combine and sort
        if additional_nodes:
            combined_nodes = gnn_nodes + additional_nodes
            combined_nodes.sort(key=lambda x: x.get('score', 0), reverse=True)
            logger.info(f"🧠 Intelligent fallback added {len(additional_nodes)} critical nodes")
            return combined_nodes
        
        return gnn_nodes
    
    def _add_related_tables_via_fk(
        self, 
        included_tables: set, 
        schema: Dict[str, Any], 
        existing_node_ids: set,
        tables_dict: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Add tables related via foreign key relationships"""
        additional = []
        relationships = schema.get('relationships', [])
        
        for rel in relationships:
            from_table = rel.get('from_table')
            to_table = rel.get('to_table')
            
            # If one table is included but not the other, add the missing one
            if from_table in included_tables and to_table not in included_tables:
                node_id = f"table:{to_table}"
                if node_id not in existing_node_ids and to_table in tables_dict:
                    additional.append({
                        'node_id': node_id,
                        'node_name': to_table,
                        'node_type': 'table',
                        'score': 0.82,
                        'auto_added': True,
                        'reason': f'FK relationship with {from_table}'
                    })
                    logger.info(f"🔗 Auto-added related table: {to_table} (FK from {from_table})")
            
            elif to_table in included_tables and from_table not in included_tables:
                node_id = f"table:{from_table}"
                if node_id not in existing_node_ids and from_table in tables_dict:
                    additional.append({
                        'node_id': node_id,
                        'node_name': from_table,
                        'node_type': 'table',
                        'score': 0.82,
                        'auto_added': True,
                        'reason': f'FK relationship with {to_table}'
                    })
                    logger.info(f"🔗 Auto-added related table: {from_table} (FK to {to_table})")
        
        return additional
    
    def _add_calculation_columns(
        self,
        included_tables: set,
        included_columns: Dict[str, List[str]],
        schema: Dict[str, Any],
        existing_node_ids: set,
        tables_dict: Dict[str, Any],
        query_lower: str
    ) -> List[Dict[str, Any]]:
        """Add critical columns for calculations (dates for duration, numbers for aggregation)"""
        additional = []
        
        # For each included table, find calculation-critical columns
        for table in included_tables:
            if table not in tables_dict:
                continue
            
            table_info = tables_dict[table]
            columns = table_info.get('columns', [])
            current_cols = set(included_columns.get(table, []))
            
            for col in columns:
                col_name = col.get('name', '')
                col_type = col.get('type', '').upper()
                
                # Skip if already included
                if col_name in current_cols:
                    continue
                
                should_add = False
                reason = ""
                
                # DATE/TIMESTAMP columns for duration calculations
                if 'DATE' in col_type or 'TIME' in col_type:
                    if any(word in query_lower for word in ['duration', 'length', 'period', 'stay', 'time']):
                        should_add = True
                        reason = "Date/time column for duration calculation"
                
                # NUMERIC columns for aggregations
                elif any(numeric in col_type for numeric in ['INT', 'DECIMAL', 'FLOAT', 'DOUBLE', 'NUMERIC']):
                    if any(word in query_lower for word in ['average', 'avg', 'sum', 'total', 'count', 'mean']):
                        should_add = True
                        reason = "Numeric column for aggregation"
                
                if should_add:
                    node_id = f"column:{table}.{col_name}"
                    if node_id not in existing_node_ids:
                        additional.append({
                            'node_id': node_id,
                            'node_name': f"{table}.{col_name}",
                            'node_type': 'column',
                            'col_type': col.get('type', 'TEXT'),
                            'score': 0.85,
                            'auto_added': True,
                            'reason': reason
                        })
                        logger.info(f"📊 Auto-added calculation column: {table}.{col_name} ({reason})")
        
        return additional
    
    def _add_grouping_dimensions(
        self,
        included_tables: set,
        included_columns: Dict[str, List[str]],
        schema: Dict[str, Any],
        existing_node_ids: set,
        tables_dict: Dict[str, Any],
        query_lower: str
    ) -> List[Dict[str, Any]]:
        """Add dimension columns for GROUP BY operations and ensure JOIN keys"""
        additional = []
        
        # Common dimension patterns: name, type, category, status, etc.
        dimension_patterns = ['name', 'type', 'category', 'status', 'level', 'grade', 'class', 'department']
        
        # First, ensure we have grouping dimension columns in included tables
        for table in included_tables:
            if table not in tables_dict:
                continue
            
            table_info = tables_dict[table]
            columns = table_info.get('columns', [])
            current_cols = set(included_columns.get(table, []))
            
            for col in columns:
                col_name = col.get('name', '').lower()
                col_type = col.get('type', '').upper()
                
                # Skip if already included
                if col.get('name', '') in current_cols:
                    continue
                
                # Check if this looks like a dimension column
                is_dimension = (
                    any(pattern in col_name for pattern in dimension_patterns) or
                    ('VARCHAR' in col_type or 'CHAR' in col_type or 'TEXT' in col_type)
                )
                
                if is_dimension:
                    node_id = f"column:{table}.{col.get('name')}"
                    if node_id not in existing_node_ids:
                        additional.append({
                            'node_id': node_id,
                            'node_name': f"{table}.{col.get('name')}",
                            'node_type': 'column',
                            'col_type': col.get('type', 'TEXT'),
                            'score': 0.80,
                            'auto_added': True,
                            'reason': 'Potential grouping dimension'
                        })
                        logger.info(f"📁 Auto-added grouping column: {table}.{col.get('name')}")
        
        # Second, ensure JOIN keys (foreign keys) for multi-table queries
        # Look for relationships between included tables
        relationships = schema.get('relationships', [])
        for rel in relationships:
            from_table = rel.get('from_table')
            to_table = rel.get('to_table')
            from_col = rel.get('from_column')
            to_col = rel.get('to_column')
            
            # If both tables are included, ensure the FK columns are too
            if from_table in included_tables and to_table in included_tables:
                # Add from column
                if from_col and from_col not in included_columns.get(from_table, []):
                    node_id = f"column:{from_table}.{from_col}"
                    if node_id not in existing_node_ids:
                        additional.append({
                            'node_id': node_id,
                            'node_name': f"{from_table}.{from_col}",
                            'node_type': 'column',
                            'col_type': 'INT',  # FKs are usually INT
                            'score': 0.88,
                            'auto_added': True,
                            'reason': f'JOIN key to {to_table}'
                        })
                        logger.info(f"🔑 Auto-added JOIN key: {from_table}.{from_col}")
                
                # Add to column
                if to_col and to_col not in included_columns.get(to_table, []):
                    node_id = f"column:{to_table}.{to_col}"
                    if node_id not in existing_node_ids:
                        additional.append({
                            'node_id': node_id,
                            'node_name': f"{to_table}.{to_col}",
                            'node_type': 'column',
                            'col_type': 'INT',
                            'score': 0.88,
                            'auto_added': True,
                            'reason': f'JOIN key from {from_table}'
                        })
                        logger.info(f"🔑 Auto-added JOIN key: {to_table}.{to_col}")
        
        return additional
    
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
