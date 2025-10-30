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

        # CTEs
        if ir.ctes:
            cte_sqls = []
            for i, cte in enumerate(ir.ctes):
                cte_sql, _ = self.compile(cte.query)
                cte_sqls.append(f"{cte.name} AS ({cte_sql})")
            sql_parts.append("WITH " + ", ".join(cte_sqls))

        # SELECT
        select_items = [self._compile_expression(expr, params) for expr in ir.select]
        select_clause = "SELECT " + ("DISTINCT " if ir.distinct else "") + ", ".join(select_items)
        sql_parts.append(select_clause)

        # FROM
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
            order_parts = [f"{self._quote_column(o.column)} {o.direction.value}" for o in ir.order_by]
            sql_parts.append("ORDER BY " + ", ".join(order_parts))

        # LIMIT/OFFSET
        if ir.limit is not None:
            sql_parts.append("LIMIT :limit")
            params["limit"] = ir.limit
            if ir.offset is not None:
                sql_parts.append("OFFSET :offset")
                params["offset"] = ir.offset

        sql = "\n".join(sql_parts)
        return sql, params

    def _compile_expression(self, expr: Expression, params: Dict) -> str:
        t = expr.type
        if t == "column":
            return self._quote_column(expr.value) + (f" AS {expr.alias}" if expr.alias else "")
        if t == "literal":
            # Parameterize literal
            key = f"p_{len(params)}"
            params[key] = expr.value
            return f":{key}" + (f" AS {expr.alias}" if expr.alias else "")
        if t in ("function", "aggregate"):
            args = ", ".join([self._compile_expression(a, params) for a in (expr.args or [])])
            return f"{expr.function}({args})" + (f" AS {expr.alias}" if expr.alias else "")
        if t == "window" and expr.window:
            # Basic window support
            inner = f"{expr.function}({', '.join([self._compile_expression(a, params) for a in (expr.args or [])])})"
            parts = ["PARTITION BY " + ", ".join([self._quote_column(c) for c in expr.window.partition_by]) if expr.window.partition_by else ""]
            if expr.window.order_by:
                parts.append("ORDER BY " + ", ".join([f"{self._quote_column(o.column)} {o.direction.value}" for o in expr.window.order_by]))
            over = " OVER (" + " ".join([p for p in parts if p]) + ")"
            return inner + over + (f" AS {expr.alias}" if expr.alias else "")
        if t == "subquery" and expr.subquery:
            sub_sql, _ = self.compile(expr.subquery)
            return f"({sub_sql})" + (f" AS {expr.alias}" if expr.alias else "")
        raise ValueError(f"Unsupported expression type: {t}")

    def _compile_predicates(self, preds: List[Predicate], params: Dict) -> str:
        parts = []
        for i, p in enumerate(preds):
            left = self._compile_expression(p.left, params)
            if p.right is None:
                # Unary operator (e.g., IS NULL)
                parts.append(f"{left} {p.operator}")
            else:
                if p.right.type == "literal":
                    key = f"p_{len(params)}"
                    params[key] = p.right.value
                    right = f":{key}"
                else:
                    right = self._compile_expression(p.right, params)
                parts.append(f"{left} {p.operator} {right}")
            if i < len(preds) - 1:
                parts.append(preds[i + 1].conjunction if preds[i + 1].conjunction else "AND")
        return " ".join(parts)

    def _quote_column(self, ref: str) -> str:
        if "." in ref:
            t, c = ref.split(".", 1)
            return f"`{t}`.`{c}`"
        return f"`{ref}`"
