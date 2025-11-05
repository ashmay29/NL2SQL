"""
Centralized prompt templates for NL2SQL system
"""
from typing import Dict, Any, List, Optional
from app.core.config import settings


def build_compact_schema_text(
    schema: Dict[str, Any], 
    max_columns_per_table: int = None,
    gnn_top_nodes: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Build a compact schema string: only table and column names to minimize context size.
    
    Args:
        schema: Database schema dictionary
        max_columns_per_table: Maximum columns to show per table (uses settings if None)
        gnn_top_nodes: Optional list of GNN-ranked schema nodes to include only relevant schema
                       Format: [{"node_id": "table:Customers", "score": 0.95}, ...]
    
    Returns:
        Formatted schema text
    """
    if max_columns_per_table is None:
        max_columns_per_table = settings.MAX_COLUMNS_IN_PROMPT
    
    lines = [f"Database: {schema.get('database', 'unknown')}"]
    tables: Dict[str, Any] = schema.get("tables", {})
    
    # If GNN provided top-K nodes, build pruned schema (like your training code)
    if gnn_top_nodes:
        return _build_gnn_pruned_schema(schema, gnn_top_nodes)
    
    # Build enhanced schema with types and sample data
    for tname, tinfo in tables.items():
        columns = tinfo.get("columns", [])
        
        # Table header
        lines.append(f"\nTable: {tname}")
        lines.append("Columns:")
        
        # Show columns with types (limit if too many)
        cols_to_show = columns[:max_columns_per_table] if len(columns) > max_columns_per_table else columns
        
        for col in cols_to_show:
            col_name = col.get("name")
            col_type = col.get("type", "TEXT")
            nullable = "" if col.get("nullable", True) else " NOT NULL"
            pk = " (PRIMARY KEY)" if col.get("primary_key", False) else ""
            
            # Add statistics hint for low-cardinality columns (likely categorical)
            stats = col.get("statistics", {})
            unique_count = stats.get("unique_count", 0)
            sample_hint = ""
            if 0 < unique_count < 20:
                sample_hint = f" [~{unique_count} distinct values]"
            
            lines.append(f"  - {col_name}: {col_type}{nullable}{pk}{sample_hint}")
        
        if len(columns) > max_columns_per_table:
            lines.append(f"  ... (+{len(columns) - max_columns_per_table} more columns)")
        
        # Include sample rows if available (helps LLM understand data patterns)
        if "sample_rows" in tinfo and tinfo["sample_rows"]:
            sample_rows = tinfo["sample_rows"][:2]  # Show 2 examples
            lines.append("Sample data:")
            for row in sample_rows:
                # Show only first few columns to save tokens
                sample_cols = list(row.keys())[:5]
                sample_data = {k: str(row[k])[:50] for k in sample_cols if k in row}  # Truncate long values
                lines.append(f"  {sample_data}")
    
    return "\n".join(lines)


def _build_gnn_pruned_schema(schema: Dict[str, Any], gnn_nodes: List[Dict[str, Any]]) -> str:
    """
    Build pruned schema based on GNN top-K ranked nodes.
    Matches your training code's create_llm_prompt() logic.
    
    Args:
        schema: Full database schema
        gnn_nodes: Top-K nodes from GNN ranker
                   [{"node_id": "table:Customers", "score": 0.95, "metadata": {...}}, ...]
    
    Returns:
        CREATE TABLE statements for only relevant tables/columns
    """
    # Extract relevant tables and columns from GNN results
    pruned_tables = set()
    pruned_cols = {}  # {table_name: [(col_name, col_type), ...]}
    
    for node in gnn_nodes:
        node_id = node.get("node_id", "")
        col_type = node.get("col_type")  # Get actual column type from GNN result
        
        # Skip global/wildcard nodes
        if node_id == "global" or "*" in node_id:
            continue
        
        # Handle table:column format
        if node_id.startswith("column:"):
            # Format: "column:table_name.column_name"
            parts = node_id.replace("column:", "").split(".")
            if len(parts) == 2:
                table, col = parts
                pruned_tables.add(table)
                if table not in pruned_cols:
                    pruned_cols[table] = []
                # Use actual column type from GNN result, fallback to TEXT
                actual_type = col_type if col_type else "TEXT"
                pruned_cols[table].append((col, actual_type))
        
        # Handle table-only nodes
        elif node_id.startswith("table:"):
            table = node_id.replace("table:", "")
            pruned_tables.add(table)
    
    # Build CREATE TABLE statements (like your training code)
    schema_lines = [f"-- Database: {schema.get('database', 'unknown')}"]
    schema_lines.append("-- GNN-Pruned Schema (Top-K Relevant Nodes)")
    schema_lines.append("")
    
    tables_dict = schema.get("tables", {})
    
    for table in sorted(pruned_tables):
        if table not in tables_dict:
            continue
        
        table_info = tables_dict[table]
        
        # Get columns for this table
        if table in pruned_cols and pruned_cols[table]:
            # Use GNN-selected columns
            cols_str = ", ".join([f"{col} {col_type.upper()}" for col, col_type in pruned_cols[table]])
        else:
            # No specific columns selected, include all columns from schema
            all_cols = table_info.get("columns", [])
            cols_str = ", ".join([f"{c.get('name')} {c.get('type', 'TEXT').upper()}" for c in all_cols])
        
        schema_lines.append(f"CREATE TABLE {table} ({cols_str});")
    
    return "\n".join(schema_lines)


def build_ir_prompt(
    schema_text: str,
    user_query: str,
    rag_examples: str = "",
    context: str = ""
) -> str:
    """
    Build flexible NL2SQL prompt that allows full SQL creativity while maintaining structure.
    
    Args:
        schema_text: Formatted database schema (GNN-pruned if available)
        user_query: User's natural language query
        rag_examples: Similar past queries for reference
        context: Conversation history context
    
    Returns:
        Complete prompt for IR generation
    """
    prompt_parts = [
        "You are an expert SQL database assistant. Your task is to convert natural language questions into accurate SQL queries.",
        "",
        "=== DATABASE SCHEMA ===",
        schema_text,
        "",
    ]
    
    if rag_examples:
        prompt_parts.extend([
            "=== SIMILAR EXAMPLES (for reference) ===",
            rag_examples,
            "",
        ])
    
    if context:
        prompt_parts.extend([
            "=== CONVERSATION HISTORY ===",
            context,
            "",
        ])
    
    prompt_parts.extend([
        "=== USER QUESTION ===",
        user_query,
        "",
        "=== INSTRUCTIONS ===",
        "Generate a SQL query that answers the user's question. You have full access to ALL SQL features:",
        "",
        "✓ Basic: SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT",
        "✓ Joins: INNER, LEFT, RIGHT, FULL OUTER, CROSS JOIN",
        "✓ Aggregates: COUNT, SUM, AVG, MIN, MAX, COUNT(DISTINCT ...)",
        "✓ Conditionals: CASE WHEN ... THEN ... ELSE ... END",
        "✓ String functions: CONCAT, SUBSTRING, UPPER, LOWER, TRIM, LIKE",
        "✓ Date functions: DATE, YEAR, MONTH, DAY, DATE_ADD, DATE_SUB, DATEDIFF",
        "✓ Math: +, -, *, /, %, ROUND, CEIL, FLOOR, ABS",
        "✓ Subqueries: IN, EXISTS, scalar subqueries, correlated subqueries",
        "✓ CTEs: WITH cte_name AS (SELECT ...)",
        "✓ Window functions: ROW_NUMBER(), RANK(), DENSE_RANK(), NTILE(), LAG(), LEAD(), SUM() OVER(), etc.",
        "✓ Set operations: UNION, UNION ALL, INTERSECT, EXCEPT",
        "✓ NULL handling: COALESCE, IFNULL, IS NULL, IS NOT NULL",
        "",
        "IMPORTANT GUIDELINES:",
        "1. Use the EXACT table and column names from the schema above - DO NOT invent or modify column names",
        "2. When referencing columns, ALWAYS use the full table.column format (e.g., 'employees.salary', NOT just 'salary')",
        "3. Table aliases in CTEs and JOINs:",
        "   - If you use an alias (e.g., FROM employees AS e), you MUST define it in the from_alias or join.alias field",
        "   - Then use the alias consistently in all column references (e.g., 'e.salary', NOT 'employees.salary')",
        "   - PREFERRED: Don't use aliases unless necessary - use full table names for clarity",
        "4. For percentage calculations, use: (COUNT(CASE WHEN condition THEN 1 END) * 100.0) / COUNT(*)",
        "5. When using aggregates with non-aggregated columns, include all non-aggregated columns in GROUP BY",
        "6. For 'top N' queries, use ORDER BY with LIMIT",
        "7. Use meaningful aliases for calculated columns (in the 'alias' field of select expressions)",
        "8. Prefer explicit JOIN syntax over comma-separated tables",
        "9. GROUP BY must reference the ACTUAL column names, not aliases from SELECT",
        "",
        "OUTPUT FORMAT:",
        "CRITICAL: Return your ENTIRE response as ONE COMPLETE JSON object. Do NOT split into multiple parts.",
        "Return ONLY a valid JSON object (no markdown, no explanations, no commentary) with this structure:",
        "{",
        "  \"select\": [{\"type\": \"column|aggregate|function|case\", \"value\": \"...\", \"alias\": \"...\", ...}],",
        "  \"from_table\": \"table_name\",",
        "  \"joins\": [{\"type\": \"INNER|LEFT|RIGHT|FULL\", \"table\": \"table_name\", \"on\": [...]}],",
        "  \"where\": [{\"left\": {...}, \"operator\": \"=\", \"right\": {...}, \"conjunction\": \"AND|OR\"}],",
        "  \"group_by\": [\"column1\", \"column2\"],",
        "  \"order_by\": [{\"column\": \"column_name\", \"direction\": \"ASC|DESC\"}],",
        "  \"limit\": 10",
        "}",
        "",
        "CRITICAL WHERE CLAUSE FORMAT:",
        "- WHERE is an ARRAY of predicates, NOT a single object",
        "- For OR conditions: Use 'conjunction': 'OR' between predicates",
        "- Example (status = 'delayed' OR status = 'canceled'):",
        "[",
        "  {\"left\": {\"type\": \"column\", \"value\": \"appointments.status\"}, \"operator\": \"=\", \"right\": {\"type\": \"literal\", \"value\": \"delayed\"}},",
        "  {\"left\": {\"type\": \"column\", \"value\": \"appointments.status\"}, \"operator\": \"=\", \"right\": {\"type\": \"literal\", \"value\": \"canceled\"}, \"conjunction\": \"OR\"}",
        "]",
        "",
        "IMPORTANT NOTES:",
        "- \"limit\" must be an INTEGER (e.g., 10, 100) or null, NOT an expression object",
        "- \"group_by\" must be an ARRAY OF STRINGS (column names), NOT expression objects",
        "- For complex queries, use subqueries, CTEs, or CASE expressions within the IR structure",
        "- Return the complete JSON in a SINGLE response",
        "",
        "EXPRESSION TYPES (use whichever fits best):",
        "",
        "Column reference:",
        "{\"type\": \"column\", \"value\": \"table.column\"}",
        "",
        "Literal value:",
        "{\"type\": \"literal\", \"value\": \"...\", \"data_type\": \"string|number|boolean\"}",
        "",
        "Aggregate function:",
        "{\"type\": \"aggregate\", \"function\": \"COUNT|SUM|AVG|MIN|MAX\", \"args\": [...], \"distinct\": false}",
        "",
        "Regular function:",
        "{\"type\": \"function\", \"function\": \"UPPER|LOWER|CONCAT|CAST|...\", \"args\": [...]}",
        "",
        "For CAST (type conversion):",
        "{\"type\": \"function\", \"function\": \"CAST\", \"args\": [{column}, {\"type\": \"literal\", \"value\": \"DECIMAL|INTEGER|CHAR\"}]}",
        "",
        "Window function (ROW_NUMBER, RANK, DENSE_RANK, LEAD, LAG, etc.):",
        "{\"type\": \"window\", \"function\": \"ROW_NUMBER|RANK|DENSE_RANK|LEAD|LAG|NTILE|...\", \"args\": [...], \"partition_by\": [columns], \"order_by\": [{\"column\": \"...\", \"direction\": \"ASC|DESC\"}]}",
        "",
        "Example for ranking: ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank",
        "{",
        "  \"type\": \"window\",",
        "  \"function\": \"ROW_NUMBER\",",
        "  \"args\": [],",
        "  \"partition_by\": [\"department\"],",
        "  \"order_by\": [{\"column\": \"salary\", \"direction\": \"DESC\"}],",
        "  \"alias\": \"rank\"",
        "}",
        "",
        "Example for LEAD (access next row): LEAD(salary, 1) OVER (ORDER BY hire_date) AS next_salary",
        "{",
        "  \"type\": \"window\",",
        "  \"function\": \"LEAD\",",
        "  \"args\": [{\"type\": \"column\", \"value\": \"salary\"}, {\"type\": \"literal\", \"value\": 1, \"data_type\": \"number\"}],",
        "  \"partition_by\": [],",
        "  \"order_by\": [{\"column\": \"hire_date\", \"direction\": \"ASC\"}],",
        "  \"alias\": \"next_salary\"",
        "}",
        "",
        "CASE expression:",
        "{\"type\": \"case\", \"conditions\": [{\"when\": {condition}, \"then\": {result}}], \"else\": {default}}",
        "",
        "Example for percentage: COUNT(CASE WHEN Attrition='Yes' THEN 1 END) * 100.0 / COUNT(*) AS AttritionRate",
        "{",
        "  \"type\": \"function\",",
        "  \"function\": \"DIVIDE\",",
        "  \"args\": [",
        "    {\"type\": \"function\", \"function\": \"MULTIPLY\", \"args\": [",
        "      {\"type\": \"aggregate\", \"function\": \"COUNT\", \"args\": [",
        "        {\"type\": \"case\", \"conditions\": [{",
        "          \"when\": {\"left\": {\"type\": \"column\", \"value\": \"Attrition\"}, \"operator\": \"=\", \"right\": {\"type\": \"literal\", \"value\": \"Yes\"}},",
        "          \"then\": {\"type\": \"literal\", \"value\": 1, \"data_type\": \"number\"}",
        "        }], \"else\": null}",
        "      ]},",
        "      {\"type\": \"literal\", \"value\": 100.0, \"data_type\": \"number\"}",
        "    ]},",
        "    {\"type\": \"aggregate\", \"function\": \"COUNT\", \"args\": [{\"type\": \"literal\", \"value\": \"*\"}]}",
        "  ],",
        "  \"alias\": \"AttritionRate\"",
        "}",
        "",
        "CRITICAL CTE EXAMPLE - Correct way to use aliases:",
        "WRONG:",
        "{",
        "  \"ctes\": [{",
        "    \"name\": \"EmployeeCTE\",",
        "    \"query\": {",
        "      \"from_table\": \"employees\",  # No alias defined",
        "      \"select\": [{\"type\": \"column\", \"value\": \"e.salary\"}]  # ❌ WRONG: 'e' not defined!",
        "    }",
        "  }]",
        "}",
        "",
        "CORRECT (Option 1 - No aliases, use full table names):",
        "{",
        "  \"ctes\": [{",
        "    \"name\": \"EmployeeCTE\",",
        "    \"query\": {",
        "      \"from_table\": \"employees\",",
        "      \"select\": [{\"type\": \"column\", \"value\": \"employees.salary\"}]  # ✅ Use full table name",
        "    }",
        "  }]",
        "}",
        "",
        "CORRECT (Option 2 - Define aliases properly):",
        "{",
        "  \"ctes\": [{",
        "    \"name\": \"EmployeeCTE\",",
        "    \"query\": {",
        "      \"from_table\": \"employees\",",
        "      \"from_alias\": \"e\",  # ✅ Define the alias",
        "      \"select\": [{\"type\": \"column\", \"value\": \"e.salary\"}]  # ✅ Now 'e' is valid",
        "    }",
        "  }]",
        "}",
        "",
        "REMINDER: Return the COMPLETE JSON object in ONE SINGLE response. For complex queries:",
        "- Use CTEs (\"ctes\" field) for multi-step logic",
        "- Use subqueries within expressions",
        "- Use CASE expressions for conditional logic",
        "- But always return everything as ONE complete JSON object",
        "",
        "Now generate the JSON IR for the user's question:",
    ])
    
    return "\n".join(prompt_parts)
    
    return "\n".join(prompt_parts)


def build_clarification_prompt(
    original_query: str,
    ambiguities: list,
    schema_context: str = ""
) -> str:
    """
    Build prompt for generating clarification questions.
    
    Args:
        original_query: User's original query
        ambiguities: List of detected ambiguities
        schema_context: Relevant schema information
    
    Returns:
        Prompt for clarification generation
    """
    prompt_parts = [
        "You are helping clarify an ambiguous database query.",
        "",
        f"Original Query: {original_query}",
        "",
        "Detected Ambiguities:",
    ]
    
    for i, amb in enumerate(ambiguities, 1):
        prompt_parts.append(f"{i}. {amb}")
    
    if schema_context:
        prompt_parts.extend([
            "",
            "Schema Context:",
            schema_context,
        ])
    
    prompt_parts.extend([
        "",
        "Generate specific clarification questions to resolve these ambiguities.",
        "Return as JSON array: [{\"question\": \"...\", \"options\": [...], \"field\": \"...\"}]"
    ])
    
    return "\n".join(prompt_parts)


def build_error_explanation_prompt(
    sql_query: str,
    error_message: str,
    schema_context: str = ""
) -> str:
    """
    Build prompt for generating user-friendly error explanations.
    
    Args:
        sql_query: The SQL query that failed
        error_message: Technical error message
        schema_context: Relevant schema information
    
    Returns:
        Prompt for error explanation generation
    """
    prompt_parts = [
        "You are helping explain a SQL error in user-friendly terms.",
        "",
        f"SQL Query: {sql_query}",
        "",
        f"Error: {error_message}",
    ]
    
    if schema_context:
        prompt_parts.extend([
            "",
            "Schema Context:",
            schema_context,
        ])
    
    prompt_parts.extend([
        "",
        "Provide:",
        "1. A simple explanation of what went wrong",
        "2. Specific suggestions to fix the issue",
        "3. General tips to avoid similar errors",
        "",
        "Use non-technical language that a business user would understand."
    ])
    
    return "\n".join(prompt_parts)
