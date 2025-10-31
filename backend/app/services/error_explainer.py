"""
Error explainer service for SQL execution errors
"""
from typing import Dict, Any, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


class ErrorExplanation:
    """Explanation for an error"""
    def __init__(
        self,
        error_type: str,
        user_friendly_message: str,
        technical_details: str,
        suggestions: List[str],
        sql_snippet: Optional[str] = None
    ):
        self.error_type = error_type
        self.user_friendly_message = user_friendly_message
        self.technical_details = technical_details
        self.suggestions = suggestions
        self.sql_snippet = sql_snippet


class ErrorExplainer:
    """Service for explaining SQL errors in user-friendly terms"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        logger.info(f"ErrorExplainer initialized with verbose={verbose}")
    
    def explain(
        self,
        error_message: str,
        sql: str,
        ir: Optional[Dict[str, Any]] = None
    ) -> ErrorExplanation:
        """
        Explain an error in user-friendly terms
        Returns: ErrorExplanation
        """
        try:
            error_lower = error_message.lower()
            
            # Pattern matching for common errors
            
            # 1. Syntax errors
            if "syntax error" in error_lower or "you have an error in your sql syntax" in error_lower:
                return self._explain_syntax_error(error_message, sql)
            
            # 2. Unknown column
            if "unknown column" in error_lower or "column" in error_lower and "doesn't exist" in error_lower:
                return self._explain_unknown_column(error_message, sql)
            
            # 3. Unknown table
            if "unknown table" in error_lower or "table" in error_lower and "doesn't exist" in error_lower:
                return self._explain_unknown_table(error_message, sql)
            
            # 4. Ambiguous column
            if "ambiguous" in error_lower:
                return self._explain_ambiguous_column(error_message, sql)
            
            # 5. Division by zero
            if "division by zero" in error_lower:
                return self._explain_division_by_zero(error_message, sql)
            
            # 6. Data type mismatch
            if "data type" in error_lower or "invalid" in error_lower and "type" in error_lower:
                return self._explain_type_mismatch(error_message, sql)
            
            # 7. Aggregate function errors
            if "invalid use of group function" in error_lower:
                return self._explain_aggregate_error(error_message, sql)
            
            # 8. Subquery errors
            if "subquery" in error_lower:
                return self._explain_subquery_error(error_message, sql)
            
            # 9. Timeout
            if "timeout" in error_lower or "lock wait timeout" in error_lower:
                return self._explain_timeout(error_message, sql)
            
            # 10. Permission denied
            if "access denied" in error_lower or "permission" in error_lower:
                return self._explain_permission_error(error_message, sql)
            
            # Default: Generic explanation
            return self._explain_generic(error_message, sql)
        
        except Exception as e:
            logger.error(f"Failed to explain error: {e}")
            return ErrorExplanation(
                error_type="unknown",
                user_friendly_message="An error occurred while executing your query.",
                technical_details=error_message,
                suggestions=["Please check your query and try again."]
            )
    
    def _explain_syntax_error(self, error: str, sql: str) -> ErrorExplanation:
        """Explain SQL syntax error"""
        # Try to extract position
        position_match = re.search(r"at line (\d+)", error)
        line_num = position_match.group(1) if position_match else "unknown"
        
        return ErrorExplanation(
            error_type="syntax_error",
            user_friendly_message="There's a syntax error in the generated SQL query.",
            technical_details=error,
            suggestions=[
                "The SQL query has invalid syntax. This is likely a bug in the query generator.",
                f"Error appears near line {line_num}.",
                "Try rephrasing your question or report this issue."
            ],
            sql_snippet=sql
        )
    
    def _explain_unknown_column(self, error: str, sql: str) -> ErrorExplanation:
        """Explain unknown column error"""
        # Extract column name
        col_match = re.search(r"'([^']+)'", error)
        column_name = col_match.group(1) if col_match else "unknown"
        
        return ErrorExplanation(
            error_type="unknown_column",
            user_friendly_message=f"The column '{column_name}' doesn't exist in the database.",
            technical_details=error,
            suggestions=[
                f"Check if '{column_name}' is spelled correctly.",
                "The column might have been renamed or removed.",
                "Try asking about available columns first."
            ],
            sql_snippet=sql
        )
    
    def _explain_unknown_table(self, error: str, sql: str) -> ErrorExplanation:
        """Explain unknown table error"""
        # Extract table name
        table_match = re.search(r"table '([^']+)'", error, re.IGNORECASE)
        table_name = table_match.group(1) if table_match else "unknown"
        
        return ErrorExplanation(
            error_type="unknown_table",
            user_friendly_message=f"The table '{table_name}' doesn't exist in the database.",
            technical_details=error,
            suggestions=[
                f"Check if '{table_name}' is the correct table name.",
                "The table might not exist in this database.",
                "Try asking 'What tables are available?' first."
            ],
            sql_snippet=sql
        )
    
    def _explain_ambiguous_column(self, error: str, sql: str) -> ErrorExplanation:
        """Explain ambiguous column error"""
        col_match = re.search(r"'([^']+)'", error)
        column_name = col_match.group(1) if col_match else "unknown"
        
        return ErrorExplanation(
            error_type="ambiguous_column",
            user_friendly_message=f"The column '{column_name}' appears in multiple tables and needs clarification.",
            technical_details=error,
            suggestions=[
                f"Specify which table's '{column_name}' you want (e.g., 'customers.{column_name}').",
                "This happens when joining multiple tables with columns of the same name.",
                "The query generator should have added table prefixes automatically."
            ],
            sql_snippet=sql
        )
    
    def _explain_division_by_zero(self, error: str, sql: str) -> ErrorExplanation:
        """Explain division by zero error"""
        return ErrorExplanation(
            error_type="division_by_zero",
            user_friendly_message="The query attempted to divide by zero.",
            technical_details=error,
            suggestions=[
                "Some of your data has zero values in the denominator.",
                "Add a WHERE clause to filter out zero values.",
                "Use NULLIF to handle division by zero: NULLIF(denominator, 0)"
            ],
            sql_snippet=sql
        )
    
    def _explain_type_mismatch(self, error: str, sql: str) -> ErrorExplanation:
        """Explain data type mismatch error"""
        return ErrorExplanation(
            error_type="type_mismatch",
            user_friendly_message="There's a data type mismatch in the query.",
            technical_details=error,
            suggestions=[
                "You might be comparing incompatible data types (e.g., text vs number).",
                "Check if date/time values are in the correct format.",
                "Use CAST() to convert between types if needed."
            ],
            sql_snippet=sql
        )
    
    def _explain_aggregate_error(self, error: str, sql: str) -> ErrorExplanation:
        """Explain aggregate function error"""
        return ErrorExplanation(
            error_type="aggregate_error",
            user_friendly_message="There's an issue with aggregate functions (SUM, COUNT, AVG, etc.).",
            technical_details=error,
            suggestions=[
                "You can't mix aggregated and non-aggregated columns without GROUP BY.",
                "All non-aggregated columns in SELECT must appear in GROUP BY.",
                "Check if you're using aggregate functions correctly."
            ],
            sql_snippet=sql
        )
    
    def _explain_subquery_error(self, error: str, sql: str) -> ErrorExplanation:
        """Explain subquery error"""
        return ErrorExplanation(
            error_type="subquery_error",
            user_friendly_message="There's an issue with a subquery in the generated SQL.",
            technical_details=error,
            suggestions=[
                "Subqueries might be returning multiple rows when only one is expected.",
                "Check if the subquery is properly correlated with the outer query.",
                "Try simplifying your question to avoid complex subqueries."
            ],
            sql_snippet=sql
        )
    
    def _explain_timeout(self, error: str, sql: str) -> ErrorExplanation:
        """Explain timeout error"""
        return ErrorExplanation(
            error_type="timeout",
            user_friendly_message="The query took too long to execute and timed out.",
            technical_details=error,
            suggestions=[
                "The query might be too complex or the dataset is very large.",
                "Try adding more specific filters to reduce the data size.",
                "Consider breaking the query into smaller parts.",
                "Database indexes might be missing on key columns."
            ],
            sql_snippet=sql
        )
    
    def _explain_permission_error(self, error: str, sql: str) -> ErrorExplanation:
        """Explain permission error"""
        return ErrorExplanation(
            error_type="permission_denied",
            user_friendly_message="You don't have permission to access this data.",
            technical_details=error,
            suggestions=[
                "Contact your database administrator for access.",
                "You might not have SELECT permission on certain tables.",
                "Try querying different tables that you have access to."
            ],
            sql_snippet=sql
        )
    
    def _explain_generic(self, error: str, sql: str) -> ErrorExplanation:
        """Generic error explanation"""
        return ErrorExplanation(
            error_type="unknown",
            user_friendly_message="An error occurred while executing the query.",
            technical_details=error,
            suggestions=[
                "The error details are shown above.",
                "Try rephrasing your question.",
                "If the error persists, please report it."
            ],
            sql_snippet=sql if self.verbose else None
        )
