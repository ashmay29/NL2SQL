"""
IR Validator: validates QueryIR against schema and SQL rules
"""
from typing import List, Dict
from .ir_models import QueryIR, Expression, Predicate, OrderBy


class IRValidator:
    """Validates IR and returns list of errors"""

    def __init__(self, schema: Dict):
        self.schema = schema or {"tables": {}, "relationships": []}

    def validate(self, ir: QueryIR) -> List[str]:
        errors: List[str] = []

        # Validate FROM table
        if ir.from_table not in self.schema.get("tables", {}):
            errors.append(f"Table '{ir.from_table}' does not exist")

        # Collect available tables from joins and CTEs
        available_tables = [ir.from_table] + [j.table for j in ir.joins] + [cte.name for cte in ir.ctes]
        cte_names = {cte.name for cte in ir.ctes}

        # Validate SELECT
        for expr in ir.select:
            errors.extend(self._validate_expression(expr, available_tables))

        # Validate JOINs
        for join in ir.joins:
            # Skip validation for CTE references (they're virtual tables)
            if join.table not in cte_names and join.table not in self.schema.get("tables", {}):
                errors.append(f"JOIN table '{join.table}' does not exist")
            for pred in join.on:
                errors.extend(self._validate_predicate(pred, available_tables))

        # Validate WHERE
        for pred in ir.where:
            errors.extend(self._validate_predicate(pred, available_tables))

        # Validate GROUP BY
        if ir.group_by:
            for col in ir.group_by:
                errors.extend(self._validate_column_reference(col, available_tables))

        # Validate HAVING
        for pred in ir.having:
            errors.extend(self._validate_predicate(pred, available_tables))

        # Validate ORDER BY
        for ob in ir.order_by:
            # ORDER BY can reference columns or expressions like COUNT(*), SUM(col), etc.
            # Only validate if it looks like a simple column reference (no parentheses)
            if '(' not in ob.column:
                errors.extend(self._validate_column_reference(ob.column, available_tables))
            else:
                # If ORDER BY uses an aggregate, warn if it's not in SELECT (SQL requires it)
                # Extract the aggregate expression (simplified check)
                order_expr = ob.column.strip()
                select_exprs = []
                for s in ir.select:
                    if s.type in ('aggregate', 'function') and s.function:
                        # Reconstruct the expression
                        args_str = ', '.join([a.value if a.type == 'column' else str(a.value) for a in (s.args or [])])
                        select_exprs.append(f"{s.function}({args_str})")
                    elif s.alias:
                        select_exprs.append(s.alias)
                
                # Check if the ORDER BY expression matches any SELECT expression or alias
                if order_expr not in select_exprs and not any(order_expr == s.alias for s in ir.select if s.alias):
                    errors.append(f"ORDER BY expression '{order_expr}' must appear in SELECT when using aggregates")

        # Validate CTEs recursively
        for cte in ir.ctes:
            errors.extend([f"CTE '{cte.name}': {e}" for e in IRValidator(self.schema).validate(cte.query)])

        return errors

    def _validate_expression(self, expr: Expression, available_tables: List[str]) -> List[str]:
        errors: List[str] = []
        if expr.type == "column":
            errors.extend(self._validate_column_reference(expr.value, available_tables))
        elif expr.type in ("function", "aggregate"):
            for a in expr.args or []:
                errors.extend(self._validate_expression(a, available_tables))
        elif expr.type == "window":
            if expr.window:
                for col in expr.window.partition_by:
                    errors.extend(self._validate_column_reference(col, available_tables))
                for ob in expr.window.order_by:
                    errors.extend(self._validate_column_reference(ob.column, available_tables))
        elif expr.type == "subquery" and expr.subquery:
            errors.extend(IRValidator(self.schema).validate(expr.subquery))
        return errors

    def _validate_predicate(self, pred: Predicate, available_tables: List[str]) -> List[str]:
        errors: List[str] = []
        errors.extend(self._validate_expression(pred.left, available_tables))
        if pred.right:
            errors.extend(self._validate_expression(pred.right, available_tables))
        return errors

    def _validate_column_reference(self, ref: str, available_tables: List[str]) -> List[str]:
        errors: List[str] = []
        tables = self.schema.get("tables", {})
        if "." in ref:
            table, column = ref.split(".", 1)
            if table not in available_tables:
                errors.append(f"Table '{table}' not in query")
            # Skip column validation for CTEs (they're not in schema tables)
            elif table not in tables:
                # CTE reference - skip column validation as CTE columns aren't in schema
                pass
            elif column != "*" and column not in [c["name"] for c in tables[table]["columns"]]:
                errors.append(f"Column '{column}' not in table '{table}'")
        else:
            # Unqualified column must exist in exactly one table to be unambiguous
            found_in = []
            for t in available_tables:
                if t in tables and ref in [c["name"] for c in tables[t]["columns"]]:
                    found_in.append(t)
            if len(found_in) == 0:
                errors.append(f"Column '{ref}' not found in any table")
            elif len(found_in) > 1:
                errors.append(f"Ambiguous column '{ref}' found in tables {found_in}; qualify with table name")
        return errors
