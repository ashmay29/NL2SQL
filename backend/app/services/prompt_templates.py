"""
Centralized prompt templates for NL2SQL system
"""
from typing import Dict, Any
from app.core.config import settings


def build_compact_schema_text(schema: Dict[str, Any], max_columns_per_table: int = None) -> str:
    """
    Build a compact schema string: only table and column names to minimize context size.
    
    Args:
        schema: Database schema dictionary
        max_columns_per_table: Maximum columns to show per table (uses settings if None)
    
    Returns:
        Formatted schema text
    """
    if max_columns_per_table is None:
        max_columns_per_table = settings.MAX_COLUMNS_IN_PROMPT
    
    lines = [f"Database: {schema.get('database', 'unknown')}"]
    tables: Dict[str, Any] = schema.get("tables", {})
    
    for tname, tinfo in tables.items():
        cols = [c.get("name") for c in tinfo.get("columns", [])]
        if len(cols) > max_columns_per_table:
            shown = cols[:max_columns_per_table]
            shown.append(f"... (+{len(cols) - max_columns_per_table} more)")
            cols = shown
        lines.append(f"- {tname}: {', '.join(cols)}")
    
    return "\n".join(lines)


def build_ir_prompt(
    schema_text: str,
    user_query: str,
    rag_examples: str = "",
    context: str = ""
) -> str:
    """
    Build IR generation prompt with RAG examples and conversation context.
    
    Args:
        schema_text: Formatted database schema
        user_query: User's natural language query
        rag_examples: Similar past queries for reference
        context: Conversation history context
    
    Returns:
        Complete prompt for IR generation
    """
    prompt_parts = [
        "You are an expert NL2SQL assistant. Convert the user's question into a JSON Intermediate Representation (IR) for MySQL.",
        "",
        "Return ONLY valid JSON. Do not include explanations.",
        "",
        "Schema:",
        schema_text,
    ]
    
    if rag_examples:
        prompt_parts.extend([
            "",
            "Similar past queries (for reference):",
            rag_examples,
        ])
    
    if context:
        prompt_parts.extend([
            "",
            context,
        ])
    
    prompt_parts.extend([
        "",
        "User Question:",
        user_query,
        "",
        "CRITICAL: Use EXACT field names as specified below:",
        "",
        "JSON Structure:",
        "{",
        "  \"select\": [{\"type\": \"column\", \"value\": \"table.column\", \"alias\": \"...\"}],",
        "  \"from_table\": \"table_name\",",
        "  \"joins\": [{\"type\": \"INNER\", \"table\": \"table_name\", \"on\": [{\"left\": {\"type\": \"column\", \"value\": \"...\"}, \"operator\": \"=\", \"right\": {\"type\": \"column\", \"value\": \"...\"}}]}],",
        "  \"where\": [{\"left\": {...}, \"operator\": \"=\", \"right\": {...}}],",
        "  \"group_by\": [\"column1\", \"column2\"],",
        "  \"order_by\": [{\"column\": \"column_name\", \"direction\": \"ASC\"}],",
        "  \"limit\": 10,",
        "  \"ctes\": [{\"name\": \"cte_name\", \"query\": {...}}]",
        "}",
        "",
        "Rules:",
        "- select items MUST have 'type' and 'value' fields",
        "- joins MUST have 'type', 'table', and 'on' fields (not 'join_type', 'target_table', or 'condition')",
        "- order_by MUST have 'column' and 'direction' fields (not 'field' or 'col')",
        "- ctes MUST have 'name' and 'query' fields (not 'cte_name' or 'cte_definition')",
        "- direction must be 'ASC' or 'DESC' (uppercase)",
        "- type for joins must be one of: INNER, LEFT, RIGHT, FULL, CROSS",
        "- If ORDER BY uses an aggregate like COUNT(*), that aggregate MUST also appear in SELECT",
        "- For aggregates in SELECT, use type='aggregate', function='COUNT', args=[...], not type='column'",
        "- When grouping, include all non-aggregated SELECT columns in group_by",
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
