"""
Query complexity analyzer
"""
from typing import Dict, Any, List
import logging
from app.services.ir_models import QueryIR

logger = logging.getLogger(__name__)


class ComplexityMetrics:
    """Complexity metrics for a query"""
    def __init__(
        self,
        score: float,
        level: str,
        factors: Dict[str, Any],
        warnings: List[str] = None
    ):
        self.score = score  # 0-100
        self.level = level  # simple | moderate | complex | very_complex
        self.factors = factors
        self.warnings = warnings or []


class ComplexityService:
    """Service for analyzing query complexity"""
    
    def __init__(self):
        logger.info("ComplexityService initialized")
    
    def analyze(self, ir: QueryIR, schema: Dict[str, Any]) -> ComplexityMetrics:
        """
        Analyze query complexity based on IR structure
        Returns: ComplexityMetrics
        """
        try:
            factors = {}
            score = 0
            warnings = []
            
            # Factor 1: Number of tables (joins)
            num_tables = 1  # from_table
            if ir.joins:
                num_tables += len(ir.joins)
            factors["num_tables"] = num_tables
            score += min(num_tables * 10, 30)  # Max 30 points
            
            if num_tables > 5:
                warnings.append(f"Query involves {num_tables} tables - consider breaking into smaller queries")
            
            # Factor 2: Aggregations
            has_aggregation = any(
                col.get("aggregation") for col in ir.select
            ) if ir.select else False
            factors["has_aggregation"] = has_aggregation
            if has_aggregation:
                score += 10
            
            # Factor 3: GROUP BY
            if ir.group_by:
                factors["has_group_by"] = True
                score += 10
                
                # Check for complex grouping
                if len(ir.group_by) > 3:
                    warnings.append(f"Grouping by {len(ir.group_by)} columns - may be slow")
                    score += 5
            
            # Factor 4: HAVING clause
            if ir.having:
                factors["has_having"] = True
                score += 10
            
            # Factor 5: Subqueries (CTEs)
            if ir.ctes:
                factors["num_ctes"] = len(ir.ctes)
                score += len(ir.ctes) * 15  # 15 points per CTE
                
                if len(ir.ctes) > 2:
                    warnings.append(f"Query uses {len(ir.ctes)} CTEs - may be difficult to optimize")
            
            # Factor 6: WHERE complexity
            if ir.where:
                where_complexity = self._analyze_condition_complexity(ir.where)
                factors["where_complexity"] = where_complexity
                score += where_complexity * 5
                
                if where_complexity > 5:
                    warnings.append("Complex WHERE clause with many conditions")
            
            # Factor 7: Window functions (if supported in future)
            # TODO: Add window function detection
            
            # Factor 8: Nested aggregations
            if has_aggregation and ir.having:
                factors["nested_aggregation"] = True
                score += 10
                warnings.append("Nested aggregation (HAVING with GROUP BY) - ensure indexes exist")
            
            # Determine complexity level
            if score < 20:
                level = "simple"
            elif score < 40:
                level = "moderate"
            elif score < 70:
                level = "complex"
            else:
                level = "very_complex"
            
            factors["total_score"] = score
            
            logger.info(f"Complexity analysis: level={level}, score={score}")
            return ComplexityMetrics(score, level, factors, warnings)
        
        except Exception as e:
            logger.error(f"Failed to analyze complexity: {e}")
            # Return default simple complexity
            return ComplexityMetrics(0, "simple", {}, [])
    
    def _analyze_condition_complexity(self, condition: Dict[str, Any]) -> int:
        """
        Recursively analyze WHERE/HAVING condition complexity
        Returns: complexity score (0-10)
        """
        try:
            if not condition:
                return 0
            
            complexity = 0
            
            # Check for logical operators
            if "and" in condition:
                complexity += 1 + sum(
                    self._analyze_condition_complexity(c)
                    for c in condition["and"]
                )
            
            if "or" in condition:
                complexity += 2 + sum(  # OR is more complex than AND
                    self._analyze_condition_complexity(c)
                    for c in condition["or"]
                )
            
            # Check for operators
            if "operator" in condition:
                op = condition["operator"]
                if op in ["IN", "NOT IN"]:
                    complexity += 2
                elif op in ["LIKE", "NOT LIKE"]:
                    complexity += 1
                elif op in ["BETWEEN"]:
                    complexity += 1
                else:
                    complexity += 0.5
            
            return min(complexity, 10)  # Cap at 10
        
        except Exception as e:
            logger.error(f"Failed to analyze condition complexity: {e}")
            return 0
    
    def suggest_optimizations(self, metrics: ComplexityMetrics) -> List[str]:
        """
        Suggest query optimizations based on complexity
        Returns: List of optimization suggestions
        """
        suggestions = []
        
        try:
            factors = metrics.factors
            
            # Suggest indexes for multi-table queries
            if factors.get("num_tables", 0) > 2:
                suggestions.append(
                    "Consider adding indexes on JOIN columns for better performance"
                )
            
            # Suggest materialized views for complex aggregations
            if factors.get("has_aggregation") and factors.get("num_tables", 0) > 3:
                suggestions.append(
                    "For frequently run aggregations, consider creating a materialized view"
                )
            
            # Suggest query breakdown for very complex queries
            if metrics.level == "very_complex":
                suggestions.append(
                    "Consider breaking this query into smaller, simpler queries"
                )
            
            # Suggest CTE optimization
            if factors.get("num_ctes", 0) > 2:
                suggestions.append(
                    "Review CTEs - some may be candidates for temporary tables"
                )
            
            # Suggest WHERE clause simplification
            if factors.get("where_complexity", 0) > 5:
                suggestions.append(
                    "Simplify WHERE clause or ensure all filter columns are indexed"
                )
            
            return suggestions
        
        except Exception as e:
            logger.error(f"Failed to suggest optimizations: {e}")
            return []
