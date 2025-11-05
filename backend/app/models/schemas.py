"""
Pydantic models for API request/response schemas
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


# Auth schemas
class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# Schema schemas
class SchemaInfo(BaseModel):
    database: str
    tables: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    version: str
    extracted_at: str


class SchemaRefreshResponse(BaseModel):
    old_version: str
    new_version: str
    changes: Dict[str, Any]
    invalidated_caches: List[str]


# NL2SQL schemas
class NL2IRRequest(BaseModel):
    query_text: str
    conversation_id: Optional[str] = None
    database_id: Optional[str] = None


class NL2IRResponse(BaseModel):
    ir: Dict[str, Any]
    confidence: float
    ambiguities: List[Dict[str, Any]] = []
    questions: List[str] = []
    conversation_id: str


class IR2SQLRequest(BaseModel):
    ir: Dict[str, Any]


class IR2SQLResponse(BaseModel):
    sql: str
    params: Dict[str, Any] = {}


class NL2SQLRequest(BaseModel):
    query_text: str
    conversation_id: Optional[str] = None
    database_id: Optional[str] = None
    use_cache: bool = True


class NL2SQLResponse(BaseModel):
    original_question: str
    resolved_question: str
    sql: str
    params: Dict[str, Any] = {}  # Include SQL parameters for frontend display
    ir: Optional[Dict[str, Any]] = None
    confidence: float
    ambiguities: List[Dict[str, Any]] = []
    explanations: List[str] = []
    suggested_fixes: List[str] = []
    cache_hit: bool = False
    execution_time: float


# SQL execution schemas
class SQLExecuteRequest(BaseModel):
    sql: str
    params: Dict[str, Any] = {}
    database_id: Optional[str] = None


class SQLExecuteResponse(BaseModel):
    results: List[Dict[str, Any]]
    row_count: int
    execution_time: float
    columns: List[str]


class SQLValidateRequest(BaseModel):
    sql: str
    database_id: Optional[str] = None


class SQLValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []


# Feedback schemas
class FeedbackSubmit(BaseModel):
    query_text: str
    generated_sql: str
    corrected_sql: str
    schema_fingerprint: str
    tables_used: List[str] = []
    metadata: Dict[str, Any] = {}


class FeedbackResponse(BaseModel):
    id: str
    message: str = "Feedback submitted successfully"


class FeedbackSimilarRequest(BaseModel):
    query: str
    schema_fingerprint: Optional[str] = None
    top_k: int = 5


class FeedbackSimilarResponse(BaseModel):
    results: List[Dict[str, Any]]


# GNN Embeddings schemas
class EmbeddingPullRequest(BaseModel):
    schema_fingerprint: str
    url: str


class EmbeddingUploadResponse(BaseModel):
    schema_fingerprint: str
    nodes_count: int
    dim: int
    message: str = "Embeddings uploaded successfully"


# Health check
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]
