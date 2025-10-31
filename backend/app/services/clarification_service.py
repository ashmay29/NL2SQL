"""
Clarification service for ambiguous queries
"""
from typing import List, Dict, Any, Optional
import logging
from app.services.ir_models import QueryIR

logger = logging.getLogger(__name__)


class ClarificationQuestion:
    """A clarification question"""
    def __init__(
        self,
        question: str,
        options: List[str],
        reason: str,
        field: str
    ):
        self.question = question
        self.options = options
        self.reason = reason
        self.field = field  # Which IR field this affects


class ClarificationService:
    """Service for generating clarification questions"""
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        logger.info(f"ClarificationService initialized with threshold={confidence_threshold}")
    
    def needs_clarification(
        self,
        ir: QueryIR,
        confidence: float,
        ambiguities: List[Dict[str, Any]]
    ) -> bool:
        """
        Determine if query needs clarification
        Returns: True if clarification is needed
        """
        try:
            # Check confidence score
            if confidence < self.confidence_threshold:
                return True
            
            # Check for explicit ambiguities
            if ambiguities and len(ambiguities) > 0:
                return True
            
            # Check for incomplete IR
            if not ir.select or len(ir.select) == 0:
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to check clarification need: {e}")
            return False
    
    def generate_questions(
        self,
        query_text: str,
        ir: QueryIR,
        schema: Dict[str, Any],
        ambiguities: List[Dict[str, Any]] = None
    ) -> List[ClarificationQuestion]:
        """
        Generate clarification questions based on ambiguities
        Returns: List of ClarificationQuestion
        """
        questions = []
        
        try:
            # Question 1: Ambiguous table references
            table_questions = self._check_ambiguous_tables(query_text, schema)
            questions.extend(table_questions)
            
            # Question 2: Ambiguous column references
            column_questions = self._check_ambiguous_columns(query_text, ir, schema)
            questions.extend(column_questions)
            
            # Question 3: Missing aggregation specification
            agg_questions = self._check_missing_aggregation(query_text, ir)
            questions.extend(agg_questions)
            
            # Question 4: Ambiguous time ranges
            time_questions = self._check_ambiguous_time_range(query_text, ir)
            questions.extend(time_questions)
            
            # Question 5: Ambiguous sorting
            sort_questions = self._check_ambiguous_sorting(query_text, ir)
            questions.extend(sort_questions)
            
            # Question 6: From explicit ambiguities
            if ambiguities:
                for amb in ambiguities:
                    questions.append(
                        ClarificationQuestion(
                            question=amb.get("question", "Please clarify"),
                            options=amb.get("options", []),
                            reason=amb.get("reason", "Ambiguity detected"),
                            field=amb.get("field", "unknown")
                        )
                    )
            
            logger.info(f"Generated {len(questions)} clarification questions")
            return questions
        
        except Exception as e:
            logger.error(f"Failed to generate clarification questions: {e}")
            return []
    
    def _check_ambiguous_tables(
        self,
        query_text: str,
        schema: Dict[str, Any]
    ) -> List[ClarificationQuestion]:
        """Check for ambiguous table references"""
        questions = []
        
        try:
            query_lower = query_text.lower()
            
            # Check for generic terms that could map to multiple tables
            generic_terms = {
                "user": ["users", "customers", "accounts"],
                "product": ["products", "items", "inventory"],
                "order": ["orders", "purchases", "transactions"],
                "sale": ["sales", "orders", "transactions"]
            }
            
            tables = schema.get("tables", {}).keys()
            
            for term, possible_tables in generic_terms.items():
                if term in query_lower:
                    # Check which possible tables exist in schema
                    matching = [t for t in possible_tables if t in tables]
                    
                    if len(matching) > 1:
                        questions.append(
                            ClarificationQuestion(
                                question=f"Which table did you mean by '{term}'?",
                                options=matching,
                                reason=f"Multiple tables match '{term}'",
                                field="from_table"
                            )
                        )
            
            return questions
        
        except Exception as e:
            logger.error(f"Failed to check ambiguous tables: {e}")
            return []
    
    def _check_ambiguous_columns(
        self,
        query_text: str,
        ir: QueryIR,
        schema: Dict[str, Any]
    ) -> List[ClarificationQuestion]:
        """Check for ambiguous column references"""
        questions = []
        
        try:
            # Check if query mentions generic column names
            generic_columns = ["name", "id", "date", "status", "type"]
            query_lower = query_text.lower()
            
            for col in generic_columns:
                if col in query_lower:
                    # Find all tables that have this column
                    tables_with_col = []
                    for table_name, table_info in schema.get("tables", {}).items():
                        columns = [c["name"] for c in table_info.get("columns", [])]
                        if col in columns:
                            tables_with_col.append(f"{table_name}.{col}")
                    
                    if len(tables_with_col) > 1:
                        questions.append(
                            ClarificationQuestion(
                                question=f"Which '{col}' column did you mean?",
                                options=tables_with_col,
                                reason=f"Multiple tables have a '{col}' column",
                                field="select"
                            )
                        )
            
            return questions
        
        except Exception as e:
            logger.error(f"Failed to check ambiguous columns: {e}")
            return []
    
    def _check_missing_aggregation(
        self,
        query_text: str,
        ir: QueryIR
    ) -> List[ClarificationQuestion]:
        """Check if aggregation type is ambiguous"""
        questions = []
        
        try:
            query_lower = query_text.lower()
            
            # Check for ambiguous aggregation keywords
            if "total" in query_lower or "sum" in query_lower:
                # Could mean SUM or COUNT
                if not any(col.get("aggregation") == "SUM" for col in ir.select if ir.select):
                    questions.append(
                        ClarificationQuestion(
                            question="Did you mean SUM (total value) or COUNT (total number)?",
                            options=["SUM", "COUNT"],
                            reason="'total' can mean sum or count",
                            field="select"
                        )
                    )
            
            if "average" in query_lower or "avg" in query_lower:
                # Check if AVG is applied correctly
                if not any(col.get("aggregation") == "AVG" for col in ir.select if ir.select):
                    questions.append(
                        ClarificationQuestion(
                            question="Which column should be averaged?",
                            options=[],  # Would need to extract from schema
                            reason="Average aggregation not clearly specified",
                            field="select"
                        )
                    )
            
            return questions
        
        except Exception as e:
            logger.error(f"Failed to check missing aggregation: {e}")
            return []
    
    def _check_ambiguous_time_range(
        self,
        query_text: str,
        ir: QueryIR
    ) -> List[ClarificationQuestion]:
        """Check for ambiguous time ranges"""
        questions = []
        
        try:
            query_lower = query_text.lower()
            
            # Check for vague time references
            vague_times = {
                "recent": ["last 7 days", "last 30 days", "last 90 days"],
                "this month": ["current calendar month", "last 30 days"],
                "this year": ["current calendar year", "last 365 days"]
            }
            
            for term, options in vague_times.items():
                if term in query_lower:
                    questions.append(
                        ClarificationQuestion(
                            question=f"What do you mean by '{term}'?",
                            options=options,
                            reason=f"'{term}' is ambiguous",
                            field="where"
                        )
                    )
            
            return questions
        
        except Exception as e:
            logger.error(f"Failed to check ambiguous time range: {e}")
            return []
    
    def _check_ambiguous_sorting(
        self,
        query_text: str,
        ir: QueryIR
    ) -> List[ClarificationQuestion]:
        """Check for ambiguous sorting"""
        questions = []
        
        try:
            query_lower = query_text.lower()
            
            # Check for "top" without clear sorting
            if "top" in query_lower or "best" in query_lower or "highest" in query_lower:
                if not ir.order_by:
                    questions.append(
                        ClarificationQuestion(
                            question="What should the results be sorted by?",
                            options=[],  # Would extract from context
                            reason="'top/best/highest' requires sorting specification",
                            field="order_by"
                        )
                    )
            
            return questions
        
        except Exception as e:
            logger.error(f"Failed to check ambiguous sorting: {e}")
            return []
    
    def format_questions_for_user(
        self,
        questions: List[ClarificationQuestion]
    ) -> List[str]:
        """Format questions as user-friendly strings"""
        try:
            formatted = []
            for i, q in enumerate(questions, 1):
                if q.options:
                    options_str = ", ".join(q.options)
                    formatted.append(f"{i}. {q.question} Options: {options_str}")
                else:
                    formatted.append(f"{i}. {q.question}")
            
            return formatted
        
        except Exception as e:
            logger.error(f"Failed to format questions: {e}")
            return []
