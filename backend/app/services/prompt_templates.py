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
    prompt_parts = [
        "You are an expert SQL database assistant. Convert the user's question into the JSON Intermediate Representation (IR) defined below.",
        "",
        "=== DATABASE SCHEMA ===",
        schema_text,
        "",
    ]
    
    if rag_examples:
        prompt_parts.extend([
            "=== SIMILAR EXAMPLES ===",
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
        "=== OUTPUT FORMAT ===",
        "Return ONLY a valid JSON object (no markdown) with this exact structure:",
        "{",
        "  \"select\": [{\"type\": \"column|aggregate|function|case\", \"value\": \"...\", \"alias\": \"...\"}],",
        "  \"from_table\": \"table_name\",",
        "  \"joins\": [{\"type\": \"INNER|LEFT\", \"table\": \"...\", \"on\": [{\"left\": {...}, \"operator\": \"=\", \"right\": {...}}]}],",
        "  \"where\": [{\"left\": {...}, \"operator\": \"=\", \"right\": {...}, \"conjunction\": \"AND|OR\"}],",
        "  \"group_by\": [\"col1\", \"col2\"],",
        "  \"order_by\": [{\"column\": \"col1\", \"direction\": \"ASC|DESC\"}],",
        "  \"limit\": 10",
        "}",
        "",
        "IMPORTANT RULES:",
        "1. Use EXACT table/column names from schema.",
        "2. Return the COMPLETE JSON object in ONE SINGLE response.",
        "3. For WHERE conditions, use the structure: [{\"left\": {...}, \"operator\": \"...\", \"right\": {...}}].",
        "4. Use CTEs (\"ctes\" field) for multi-step logic.",
        "",
        "Now generate the JSON IR:"
    ])
    
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
