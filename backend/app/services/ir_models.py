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


class Expression(BaseModel):
    type: Literal["column", "literal", "function", "aggregate", "window", "subquery"]
    value: Any
    alias: Optional[str] = None

    # For function/aggregate
    function: Optional[str] = None
    args: List["Expression"] = []

    # For window functions
    window: Optional[WindowFunction] = None

    # For subquery
    subquery: Optional["QueryIR"] = None


class Predicate(BaseModel):
    left: Expression
    operator: str  # =, !=, <, >, <=, >=, LIKE, IN, NOT IN, IS NULL, etc.
    right: Optional[Expression] = None
    conjunction: Optional[Literal["AND", "OR"]] = "AND"


class Join(BaseModel):
    type: JoinType
    table: str
    alias: Optional[str] = None
    on: List[Predicate]


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
    from_table: str
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
Expression.update_forward_refs()
QueryIR.update_forward_refs()
