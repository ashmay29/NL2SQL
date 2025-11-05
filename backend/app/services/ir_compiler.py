"""
IR to MySQL compiler
"""
from typing import Tuple, Dict, List
from .ir_models import QueryIR, Expression, Predicate, Join, OrderBy


class IRToMySQLCompiler:
    """Compiles IR to parameterized MySQL SQL"""

    def __init__(self, mysql_version: str = "8.0"):
        self.mysql_version = mysql_version

    def compile(self, ir: QueryIR) -> Tuple[str, Dict]:
        params: Dict = ir.parameters.copy() if ir.parameters else {}
        sql_parts: List[str] = []

        # CTEs - each CTE gets its own WITH keyword
        if ir.ctes:
            for i, cte in enumerate(ir.ctes):
                cte_sql, _ = self.compile(cte.query)
                sql_parts.append(f"WITH {cte.name} AS ({cte_sql})")

        # SELECT
        select_items = [self._compile_expression(expr, params, inline_literals=True) for expr in ir.select]
        if len(select_items) == 1:
            # Single column - keep on same line
            select_clause = "SELECT " + ("DISTINCT " if ir.distinct else "") + select_items[0]
        else:
            # Multiple columns - put each on new line with indentation
            distinct_keyword = "DISTINCT " if ir.distinct else ""
            select_clause = "SELECT " + distinct_keyword + "\n    " + ",\n    ".join(select_items)
        sql_parts.append(select_clause)

        # FROM
        if ir.from_table:
            from_clause = f"FROM `{ir.from_table}`" + (f" AS {ir.from_alias}" if ir.from_alias else "")
            sql_parts.append(from_clause)

        # JOINs
        for j in ir.joins or []:
            on_clause = self._compile_predicates(j.on, params)
            sql_parts.append(f"{j.type.value} JOIN `{j.table}`" + (f" AS {j.alias}" if j.alias else "") + f" ON {on_clause}")

        # WHERE
        if ir.where:
            sql_parts.append("WHERE " + self._compile_predicates(ir.where, params))

        # GROUP BY
        if ir.group_by:
            sql_parts.append("GROUP BY " + ", ".join([self._quote_column(c) for c in ir.group_by]))

        # HAVING
        if ir.having:
            sql_parts.append("HAVING " + self._compile_predicates(ir.having, params))

        # ORDER BY
        if ir.order_by:
            order_parts = []
            for o in ir.order_by:
                # If column contains function call (e.g., COUNT(*), SUM(col)), use as-is
                # Otherwise quote it as a column reference
                if '(' in o.column:
                    order_parts.append(f"{o.column} {o.direction.value}")
                else:
                    order_parts.append(f"{self._quote_column(o.column)} {o.direction.value}")
            sql_parts.append("ORDER BY " + ", ".join(order_parts))

        # LIMIT/OFFSET
        if ir.limit is not None:
            sql_parts.append(f"LIMIT {ir.limit}")
            if ir.offset is not None:
                sql_parts.append(f"OFFSET {ir.offset}")

        sql = "\n".join(sql_parts)
        return sql, params

    def _compile_expression(self, expr: Expression, params: Dict, inline_literals: bool = False) -> str:
        t = expr.type
        
        # Handle CASE expressions first (can appear anywhere)
        if t == "case":
            case_parts = ["CASE"]
            
            # Get when clauses - support both nested and direct format
            when_clauses = []
            else_clause = None
            
            if expr.case:
                # Nested format: expr.case contains CaseExpression
                when_clauses = expr.case.when_clauses
                else_clause = expr.case.else_clause
            elif expr.conditions:
                # Direct format: conditions are on Expression itself
                when_clauses = expr.conditions
                else_clause = expr.else_ or getattr(expr, 'else', None)
            else:
                raise ValueError("CASE expression missing 'case' or 'conditions' field")
            
            # Compile WHEN clauses
            for when in when_clauses:
                if when.condition:
                    cond_sql = self._compile_predicates([when.condition], params)
                    # Handle NULL in THEN clause
                    if when.result is None:
                        result_sql = "NULL"
                    else:
                        result_sql = self._compile_expression(when.result, params, inline_literals=True)
                    case_parts.append(f"WHEN {cond_sql} THEN {result_sql}")
            
            # Compile ELSE clause if present
            if else_clause:
                else_sql = self._compile_expression(else_clause, params, inline_literals=True)
                case_parts.append(f"ELSE {else_sql}")
            
            case_parts.append("END")
            return " ".join(case_parts) + (f" AS {expr.alias}" if expr.alias else "")
        
        if t == "column":
            return self._quote_column(expr.value) + (f" AS {expr.alias}" if expr.alias else "")
        if t == "literal":
            # Always inline all literals directly in SQL (no parameterization)
            data_type = getattr(expr, 'data_type', None)
            if data_type == "string" or isinstance(expr.value, str):
                # Escape single quotes in strings
                escaped_value = str(expr.value).replace("'", "''")
                return f"'{escaped_value}'" + (f" AS {expr.alias}" if expr.alias else "")
            elif expr.value is None:
                return "NULL" + (f" AS {expr.alias}" if expr.alias else "")
            elif isinstance(expr.value, bool):
                return ("TRUE" if expr.value else "FALSE") + (f" AS {expr.alias}" if expr.alias else "")
            else:
                return str(expr.value) + (f" AS {expr.alias}" if expr.alias else "")
        if t in ("function", "aggregate"):
            # Handle CAST specially: CAST(expr AS type)
            if expr.function == "CAST":
                if expr.args and len(expr.args) >= 2:
                    expr_sql = self._compile_expression(expr.args[0], params, inline_literals=True)
                    # Second arg is the data type (should be a literal string)
                    data_type = expr.args[1].value if expr.args[1].type == "literal" else "DECIMAL"
                    return f"CAST({expr_sql} AS {data_type})" + (f" AS {expr.alias}" if expr.alias else "")
                elif expr.args and len(expr.args) == 1:
                    # Default to DECIMAL if type not specified
                    expr_sql = self._compile_expression(expr.args[0], params, inline_literals=True)
                    return f"CAST({expr_sql} AS DECIMAL)" + (f" AS {expr.alias}" if expr.alias else "")
            
            # Handle math operations as infix operators
            if expr.function in ("MULTIPLY", "DIVIDE", "ADD", "SUBTRACT", "MODULO"):
                if expr.args and len(expr.args) >= 2:
                    ops = {"MULTIPLY": "*", "DIVIDE": "/", "ADD": "+", "SUBTRACT": "-", "MODULO": "%"}
                    left_sql = self._compile_expression(expr.args[0], params, inline_literals=True)
                    right_sql = self._compile_expression(expr.args[1], params, inline_literals=True)
                    result = f"({left_sql} {ops[expr.function]} {right_sql})"
                    # Handle additional args for chained operations
                    for arg in expr.args[2:]:
                        arg_sql = self._compile_expression(arg, params, inline_literals=True)
                        result = f"({result} {ops[expr.function]} {arg_sql})"
                    return result + (f" AS {expr.alias}" if expr.alias else "")
            
            # Regular function/aggregate - always inline literals in function args
            args = ", ".join([self._compile_expression(a, params, inline_literals=True) for a in (expr.args or [])])
            return f"{expr.function}({args})" + (f" AS {expr.alias}" if expr.alias else "")
        
        if t == "window":
            # Window function support: ROW_NUMBER, RANK, DENSE_RANK, LEAD, LAG, NTILE, etc.
            # Compile function arguments
            args = ", ".join([self._compile_expression(a, params, inline_literals=True) for a in (expr.args or [])])
            inner = f"{expr.function}({args})"
            
            # Build OVER clause
            over_parts = []
            
            # Handle both nested expr.window and direct partition_by/order_by on expr
            partition_by = expr.partition_by if hasattr(expr, 'partition_by') else (expr.window.partition_by if expr.window else [])
            order_by = expr.order_by if hasattr(expr, 'order_by') else (expr.window.order_by if expr.window else [])
            
            if partition_by:
                partition_cols = ", ".join([self._quote_column(c) if isinstance(c, str) else self._compile_expression(c, params, inline_literals=True) for c in partition_by])
                over_parts.append(f"PARTITION BY {partition_cols}")
            
            if order_by:
                order_items = []
                for o in order_by:
                    if isinstance(o, dict):
                        # Dict format: {"column": "...", "direction": "ASC|DESC"}
                        col = self._quote_column(o.get("column"))
                        direction = o.get("direction", "ASC")
                        order_items.append(f"{col} {direction}")
                    else:
                        # Object format (OrderBy model)
                        col = self._quote_column(o.column)
                        direction = o.direction.value if hasattr(o.direction, 'value') else o.direction
                        order_items.append(f"{col} {direction}")
                over_parts.append(f"ORDER BY {', '.join(order_items)}")
            
            over_clause = " OVER (" + " ".join(over_parts) + ")" if over_parts else " OVER ()"
            return inner + over_clause + (f" AS {expr.alias}" if expr.alias else "")
        
        if t == "subquery" and expr.subquery:
            sub_sql, _ = self.compile(expr.subquery)
            return f"({sub_sql})" + (f" AS {expr.alias}" if expr.alias else "")
        raise ValueError(f"Unsupported expression type: {t}")

    def _compile_predicates(self, preds: List[Predicate], params: Dict) -> str:
        parts = []
        for i, p in enumerate(preds):
            left = self._compile_expression(p.left, params, inline_literals=True)
            if p.right is None:
                # Unary operator (e.g., IS NULL)
                parts.append(f"{left} {p.operator}")
            else:
                # Always inline literals directly (no parameterization)
                right = self._compile_expression(p.right, params, inline_literals=True)
                parts.append(f"{left} {p.operator} {right}")
            if i < len(preds) - 1:
                parts.append(preds[i + 1].conjunction if preds[i + 1].conjunction else "AND")
        return " ".join(parts)

    def _quote_column(self, ref: str) -> str:
        if "." in ref:
            t, c = ref.split(".", 1)
            return f"`{t}`.`{c}`"
        return f"`{ref}`"
