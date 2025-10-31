"""
SQL corrector service for common errors
"""
from typing import Dict, Any, List, Tuple
import logging
import sqlparse
from app.services.ir_models import QueryIR, Expression, OrderBy, Join

logger = logging.getLogger(__name__)


class CorrectorService:
    """Service for detecting and correcting common SQL errors"""
    
    def __init__(self):
        logger.info("CorrectorService initialized")
    
    def check_and_correct(
        self,
        sql: str,
        ir: QueryIR,
        schema: Dict[str, Any]
    ) -> Tuple[str, List[str], List[str]]:
        """
        Check SQL for common errors and suggest corrections
        Returns: (corrected_sql, errors_found, corrections_applied)
        """
        try:
            errors = []
            corrections = []
            corrected_sql = sql
            
            # Parse SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                return sql, ["Failed to parse SQL"], []
            
            # Check 1: Missing table aliases in multi-table queries
            if ir.joins and len(ir.joins) > 0:
                has_ambiguous_columns = self._check_ambiguous_columns(sql, ir, schema)
                if has_ambiguous_columns:
                    errors.append("Potential ambiguous column references in multi-table query")
                    # Try to add table prefixes
                    corrected = self._add_table_prefixes(sql, ir, schema)
                    if corrected != sql:
                        corrected_sql = corrected
                        corrections.append("Added table prefixes to disambiguate columns")
            
            # Check 2: Missing GROUP BY columns
            if ir.group_by:
                missing_group_by = self._check_group_by_completeness(ir)
                if missing_group_by:
                    errors.append(f"Non-aggregated columns in SELECT should be in GROUP BY: {', '.join(missing_group_by)}")
            
            # Check 3: Invalid aggregation usage
            if any((isinstance(col, Expression) and col.type == "aggregate") for col in (ir.select or [])):
                agg_errors = self._check_aggregation_validity(ir)
                errors.extend(agg_errors)
            
            # Check 4: ORDER BY on non-selected columns (MySQL strict mode)
            if ir.order_by:
                order_errors = self._check_order_by_validity(ir)
                if order_errors:
                    errors.extend(order_errors)
            
            # Check 5: LIMIT without ORDER BY (non-deterministic)
            if ir.limit and not ir.order_by:
                errors.append("LIMIT without ORDER BY may produce non-deterministic results")
                corrections.append("Consider adding ORDER BY clause for consistent results")
            
            # Check 6: Cartesian product (missing JOIN condition)
            if ir.joins:
                cartesian_risk = self._check_cartesian_product(ir)
                if cartesian_risk:
                    errors.append("Potential cartesian product - verify JOIN conditions")
            
            logger.info(f"Corrector found {len(errors)} issues, applied {len(corrections)} corrections")
            return corrected_sql, errors, corrections
        
        except Exception as e:
            logger.error(f"Failed to check and correct SQL: {e}")
            return sql, [f"Corrector error: {str(e)}"], []
    
    def _check_ambiguous_columns(
        self,
        sql: str,
        ir: QueryIR,
        schema: Dict[str, Any]
    ) -> bool:
        """Check if query has ambiguous column references"""
        try:
            # Get all tables in query
            tables = [ir.from_table]
            if ir.joins:
                tables.extend([j.table for j in ir.joins if isinstance(j, Join)])
            
            # Get all columns from these tables
            table_columns = {}
            for table in tables:
                if table in schema.get("tables", {}):
                    cols = [c["name"] for c in schema["tables"][table].get("columns", [])]
                    table_columns[table] = cols
            
            # Check for duplicate column names across tables
            all_columns = []
            for cols in table_columns.values():
                all_columns.extend(cols)
            
            duplicates = [col for col in set(all_columns) if all_columns.count(col) > 1]
            
            if duplicates:
                # Check if SQL uses unqualified column names
                sql_lower = sql.lower()
                for dup in duplicates:
                    # Simple check: if column appears without table prefix
                    if f" {dup.lower()} " in sql_lower or f" {dup.lower()}," in sql_lower:
                        return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to check ambiguous columns: {e}")
            return False
    
    def _add_table_prefixes(
        self,
        sql: str,
        ir: QueryIR,
        schema: Dict[str, Any]
    ) -> str:
        """
        Attempt to add table prefixes to ambiguous columns
        This is a simplified version - production would need more sophisticated parsing
        """
        # For now, return original SQL
        # TODO: Implement proper column qualification
        return sql
    
    def _check_group_by_completeness(self, ir: QueryIR) -> List[str]:
        """Check if all non-aggregated SELECT columns are in GROUP BY"""
        try:
            if not ir.select or not ir.group_by:
                return []
            
            # Get non-aggregated columns from SELECT
            non_agg_columns = []
            for expr in ir.select:
                if not isinstance(expr, Expression):
                    continue
                if expr.type != "aggregate":
                    # Column name: for simple column expressions, value holds table.column or column
                    if expr.type == "column" and isinstance(expr.value, str):
                        non_agg_columns.append(expr.value)
                    elif expr.alias:
                        non_agg_columns.append(expr.alias)
            
            # Get GROUP BY columns
            group_by_cols = list(ir.group_by)
            
            # Find missing columns
            missing = [col for col in non_agg_columns if col not in group_by_cols]
            
            return missing
        
        except Exception as e:
            logger.error(f"Failed to check GROUP BY completeness: {e}")
            return []
    
    def _check_aggregation_validity(self, ir: QueryIR) -> List[str]:
        """Check for invalid aggregation usage"""
        errors = []
        
        try:
            # Check: Aggregation without GROUP BY on non-aggregated columns
            has_agg = any((isinstance(col, Expression) and col.type == "aggregate") for col in (ir.select or []))
            has_non_agg = any((isinstance(col, Expression) and col.type != "aggregate") for col in (ir.select or []))
            
            if has_agg and has_non_agg and not ir.group_by:
                errors.append(
                    "Mixing aggregated and non-aggregated columns without GROUP BY"
                )
            
            # Check: Nested aggregations (not supported in MySQL)
            for expr in (ir.select or []):
                if not isinstance(expr, Expression):
                    continue
                if expr.type == "aggregate" and isinstance(expr.value, str):
                    inner = expr.value.upper()
                    agg_functions = ["COUNT", "SUM", "AVG", "MAX", "MIN"]
                    if any(f"{agg}(" in inner for agg in agg_functions):
                        errors.append(f"Nested aggregation detected in: {expr.value}")
            
            return errors
        
        except Exception as e:
            logger.error(f"Failed to check aggregation validity: {e}")
            return []
    
    def _check_order_by_validity(self, ir: QueryIR) -> List[str]:
        """Check if ORDER BY columns are valid"""
        errors = []
        
        try:
            if not ir.order_by or not ir.select:
                return []
            
            # Get selected columns (including aliases)
            selected = []
            for expr in ir.select:
                if not isinstance(expr, Expression):
                    continue
                if expr.alias:
                    selected.append(expr.alias)
                elif expr.type == "column" and isinstance(expr.value, str):
                    selected.append(expr.value)
            
            # Check if ORDER BY columns are in SELECT (MySQL strict mode requirement)
            for ob in ir.order_by:
                if isinstance(ob, OrderBy):
                    col_name = ob.column
                else:
                    continue
                if col_name and col_name not in selected:
                    # This is actually allowed in MySQL, but may cause issues in strict mode
                    pass  # Not an error, just a note
            
            return errors
        
        except Exception as e:
            logger.error(f"Failed to check ORDER BY validity: {e}")
            return []
    
    def _check_cartesian_product(self, ir: QueryIR) -> bool:
        """Check if query might produce a cartesian product"""
        try:
            if not ir.joins:
                return False
            
            # Check if all joins have conditions
            for join in ir.joins:
                if isinstance(join, Join):
                    if not join.on or len(join.on) == 0:
                        return True  # JOIN without ON clause
                else:
                    # Unknown structure: be conservative
                    return True  # JOIN without ON clause
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to check cartesian product: {e}")
            return False
