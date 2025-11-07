"""
Intermediate Representation (IR) Pydantic models
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class JoinType(str, Enum):
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"
    CROSS = "CROSS"


class WindowFrameType(str, Enum):
    ROWS = "ROWS"
    RANGE = "RANGE"


class WindowBoundType(str, Enum):
    PRECEDING = "PRECEDING"
    FOLLOWING = "FOLLOWING"
    CURRENT_ROW = "CURRENT_ROW"
    UNBOUNDED = "UNBOUNDED"


class OrderDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class OrderBy(BaseModel):
    column: str
    direction: OrderDirection = OrderDirection.ASC


class WindowFrameBound(BaseModel):
    type: WindowBoundType
    value: Optional[int] = None


class WindowFrame(BaseModel):
    type: WindowFrameType
    start: WindowFrameBound
    end: WindowFrameBound


class WindowFunction(BaseModel):
    function: str  # ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, etc.
    partition_by: List[str] = []
    order_by: List[OrderBy] = []
    frame: Optional[WindowFrame] = None


class CaseWhen(BaseModel):
    """CASE WHEN condition for conditional expressions"""
    condition: Optional["Predicate"] = Field(None, alias="when")  # Alias 'when' to 'condition'
    result: Optional["Expression"] = Field(None, alias="then")  # Alias 'then' to 'result', allow None for NULL
    
    class Config:
        populate_by_name = True  # Allow both 'when'/'then' and 'condition'/'result'


class CaseExpression(BaseModel):
    """CASE expression support"""
    when_clauses: List[CaseWhen] = Field(..., alias="conditions")
    else_clause: Optional["Expression"] = Field(None, alias="else")
    
    class Config:
        populate_by_name = True  # Allow both 'conditions' and 'when_clauses'


class Expression(BaseModel):
    type: Literal["column", "literal", "function", "aggregate", "window", "subquery", "case"]
    value: Any = None  # Make optional for case expressions
    alias: Optional[str] = None

    # For function/aggregate
    function: Optional[str] = None
    args: List["Expression"] = []

    # For window functions (two formats supported for flexibility)
    window: Optional[WindowFunction] = None  # Nested format
    partition_by: Optional[List[str]] = None  # Direct format (alternative)
    order_by: Optional[List[dict]] = None  # Direct format (alternative) - list of {"column": str, "direction": str}
    window_frame: Optional[Dict[str, Any]] = None  # Window frame specification (ROWS/RANGE BETWEEN...)

    # For subquery (support both 'subquery' and 'query' field names)
    subquery: Optional["QueryIR"] = Field(None, alias="query")
    
    # For CASE expressions (two formats supported)
    case: Optional[CaseExpression] = None  # Nested format
    conditions: Optional[List[CaseWhen]] = None  # Direct format (alternative)
    else_: Optional["Expression"] = Field(None, alias="else")  # Direct format (alternative)
    
    # Additional field for data type hints
    data_type: Optional[str] = None
    
    class Config:
        populate_by_name = True  # Allow both 'else' and 'else_', 'query' and 'subquery'


class Predicate(BaseModel):
    left: Expression
    operator: str  # =, !=, <, >, <=, >=, LIKE, IN, NOT IN, IS NULL, etc.
    right: Optional[Expression] = None
    conjunction: Optional[Literal["AND", "OR"]] = "AND"


class Join(BaseModel):
    type: JoinType
    table: str
    alias: Optional[str] = None
    on: List[Predicate] = []  # Empty list for CROSS JOIN (no ON clause needed)


class CTE(BaseModel):
    name: str
    query: "QueryIR"


class QueryIR(BaseModel):
    # CTEs
    ctes: List[CTE] = []

    # SELECT
    select: List[Expression]
    distinct: bool = False

    # FROM
    from_table: Optional[str] = None  # Optional to support queries without FROM (e.g., SELECT 1)
    from_alias: Optional[str] = None

    # JOINs
    joins: List[Join] = []

    # WHERE
    where: List[Predicate] = []

    # GROUP BY
    group_by: List[str] = []

    # HAVING
    having: List[Predicate] = []

    # ORDER BY
    order_by: List[OrderBy] = []

    # LIMIT/OFFSET
    limit: Optional[int] = None
    offset: Optional[int] = None

    # Parameters for safe binding
    parameters: Dict[str, Any] = {}

    # Metadata
    confidence: float = 1.0
    ambiguities: List[Dict[str, Any]] = []

    @validator('select')
    def _validate_select_not_empty(cls, v):
        if not v:
            raise ValueError("SELECT clause cannot be empty")
        return v


# Forward refs
CaseWhen.update_forward_refs()
CaseExpression.update_forward_refs()
Expression.update_forward_refs()
QueryIR.update_forward_refs()