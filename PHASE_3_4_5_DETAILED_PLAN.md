# Phase 3, 4, 5 Detailed Implementation Plan
## With GNN Embeddings Integration

---

## 🎯 Overview

This plan covers:
- **Phase 3**: RAG Feedback System with Qdrant
- **Phase 4**: NL2SQL Engine Enhancements  
- **Phase 5**: SQL Execution & Security

**GNN Strategy**: Use mock embeddings initially (sentence-transformers), design for easy swap to real GNN embeddings later.

---

# PHASE 3: RAG Feedback System

## 3.1 Goals
- Store user corrections and successful queries in Qdrant
- Retrieve similar past queries using vector search
- Augment NL→IR prompts with relevant examples
- Use mock embeddings (sentence-transformers) initially, swap to GNN later

## 3.2 Data Models

### Qdrant Collection: `nl2sql_feedback`
```python
{
  "id": "uuid",
  "vector": [0.1, 0.2, ...],  # 384-dim (mock) or 512-dim (GNN)
  "payload": {
    "query_text": "top 5 customers by revenue",
    "schema_fingerprint": "abc123",
    "database": "nl2sql_target",
    "original_sql": "SELECT ...",
    "corrected_sql": "SELECT ... ORDER BY revenue DESC LIMIT 5",
    "correction_reason": "Missing ORDER BY and LIMIT",
    "execution_success": true,
    "involved_tables": ["customers", "orders"],
    "feedback_type": "correction" | "success",
    "timestamp": "2025-10-30T...",
    "upvotes": 0
  }
}
```

### Qdrant Collection: `schema_embeddings`
```python
{
  "id": "table:customers" | "column:customers.name",
  "vector": [0.1, ...],  # GNN embedding (512-dim)
  "payload": {
    "schema_fingerprint": "abc123",
    "node_type": "table" | "column",
    "name": "customers",
    "metadata": {...}
  }
}
```

## 3.3 Implementation Steps

### Step 3.1: Qdrant Service
**File**: `backend/app/services/qdrant_service.py`

```python
class QdrantService:
    def __init__(self, url, api_key):
        self.client = QdrantClient(url, api_key)
    
    async def init_collections(self):
        # Create nl2sql_feedback (384-dim for mock)
        # Create schema_embeddings (512-dim for GNN)
    
    async def upsert_feedback(self, point_id, vector, payload):
        pass
    
    async def search_similar(self, vector, filters, limit=5):
        pass
```

**Tasks**:
- ✅ Initialize Qdrant client
- ✅ Create collections on startup
- ✅ Add health check
- ✅ Implement upsert and search

---

### Step 3.2: Embedding Service (Mock + GNN)
**File**: `backend/app/services/embedding_service.py`

```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        pass

class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim
    
    async def embed_query(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

class GNNEmbeddingProvider(EmbeddingProvider):
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def embed_query(self, text: str) -> List[float]:
        # Load from Redis (uploaded via Phase 2)
        # Fallback to mock if missing
        pass
```

**Config**: `EMBEDDING_PROVIDER=mock` or `gnn` in `.env`

**Tasks**:
- ✅ Abstract interface
- ✅ Mock provider (sentence-transformers)
- ✅ GNN provider (load from Redis)
- ✅ Factory to switch providers

---

### Step 3.3: Feedback Service
**File**: `backend/app/services/feedback_service.py`

```python
class FeedbackService:
    def __init__(self, qdrant: QdrantService, embedder: EmbeddingProvider):
        pass
    
    async def store_feedback(self, query_text, original_sql, corrected_sql, metadata):
        vector = await self.embedder.embed_query(query_text)
        point_id = str(uuid.uuid4())
        await self.qdrant.upsert_feedback(point_id, vector, {...})
        return point_id
    
    async def find_similar(self, query_text, schema_fingerprint, limit=5):
        vector = await self.embedder.embed_query(query_text)
        results = await self.qdrant.search_similar(vector, filters={...}, limit=limit)
        return results
```

**Tasks**:
- ✅ Store feedback with embeddings
- ✅ Search by vector similarity
- ✅ Filter by schema fingerprint

---

### Step 3.4: RAG Service
**File**: `backend/app/services/rag_service.py`

```python
class RAGService:
    def __init__(self, feedback: FeedbackService):
        self.feedback = feedback
    
    async def augment_prompt(self, query_text, schema_fingerprint, base_prompt):
        similar = await self.feedback.find_similar(query_text, schema_fingerprint, 3)
        if not similar:
            return base_prompt
        
        examples_text = "\n".join([
            f"Q: {s['query_text']}\nSQL: {s.get('corrected_sql') or s['original_sql']}"
            for s in similar
        ])
        
        return base_prompt + f"\n\nSimilar examples:\n{examples_text}"
```

**Tasks**:
- ✅ Retrieve top-3 similar queries
- ✅ Format for prompt injection
- ✅ Prioritize corrections

---

### Step 3.5: API Endpoints
**File**: `backend/app/api/v1/feedback.py`

**Endpoints**:
- `POST /api/v1/feedback` - Submit correction
- `GET /api/v1/feedback/similar?query=...` - Get similar queries
- `POST /api/v1/feedback/{id}/vote` - Upvote/downvote

**Tasks**:
- ✅ Implement all endpoints
- ✅ Add to main router
- ✅ Add Pydantic models

---

### Step 3.6: Integrate RAG into NL2SQL
**File**: `backend/app/api/v1/nl2sql.py`

```python
@router.post("/nl2sql")
async def nl2sql(req, rag: RAGService = Depends(...)):
    base_prompt = build_ir_prompt(schema_text, req.query_text)
    
    if req.use_rag:  # Optional flag
        prompt = await rag.augment_prompt(req.query_text, schema_fp, base_prompt)
    else:
        prompt = base_prompt
    
    # Generate IR with augmented prompt
    ir = llm.generate_json(prompt)
    # ... rest
```

**Tasks**:
- ✅ Add RAG dependency
- ✅ Augment prompt before LLM call
- ✅ Make RAG optional via flag

---

### Step 3.7: Frontend - Feedback Page
**File**: `frontend/src/pages/FeedbackManager.tsx`

**Features**:
- Submit correction form
- Search similar queries
- View feedback history
- Upvote/downvote

**Tasks**:
- ✅ Create page component
- ✅ Add to router
- ✅ Add nav item in Layout

---

## 3.8 GNN Integration Points

**Mock Phase**:
- Use sentence-transformers (384-dim)
- Embed query text directly

**GNN Phase**:
- Upload GNN embeddings via `/api/v1/schema/embeddings/upload`
- Switch `EMBEDDING_PROVIDER=gnn`
- Query embeddings: Map query to schema nodes, aggregate GNN vectors
- Schema embeddings: Direct lookup from Redis

---

# PHASE 4: NL2SQL Engine Enhancements

## 4.1 Goals
- Multi-turn conversations with context
- Query complexity analysis
- SQL self-correction
- Clarification questions
- User-friendly error messages

## 4.2 Implementation Steps

### Step 4.1: Context Manager
**File**: `backend/app/services/context_service.py`

```python
class ContextService:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_context(self, conversation_id):
        key = f"context:{conversation_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else {"messages": []}
    
    async def update_context(self, conversation_id, message):
        context = await self.get_context(conversation_id)
        context["messages"].append(message)
        context["messages"] = context["messages"][-10:]  # Keep last 10
        self.redis.setex(f"context:{conversation_id}", 3600, json.dumps(context))
```

**Tasks**:
- ✅ Store conversation history in Redis
- ✅ TTL of 1 hour
- ✅ Track clarifications

---

### Step 4.2: Complexity Analyzer
**File**: `backend/app/services/complexity_service.py`

```python
class ComplexityAnalyzer:
    def analyze(self, ir: QueryIR):
        score = 0
        score += len(ir.joins) * 2
        score += 5 if any(e.type == "aggregate" for e in ir.select) else 0
        score += 10 if any(e.type == "subquery" for e in ir.select) else 0
        
        complexity = "simple" if score < 5 else "medium" if score < 15 else "hard"
        
        return {
            "complexity": complexity,
            "score": score,
            "features": {...},
            "warnings": [...]
        }
```

**Tasks**:
- ✅ Classify simple/medium/hard
- ✅ Detect joins, aggregations, subqueries, CTEs
- ✅ Generate warnings

---

### Step 4.3: SQL Corrector
**File**: `backend/app/services/corrector_service.py`

```python
class SQLCorrectorService:
    async def correct_sql(self, sql, ir, schema, error=None, max_iter=3):
        for i in range(max_iter):
            errors = self.validator.validate(ir)
            if not errors:
                return {"sql": sql, "corrected": i > 0}
            
            prompt = f"Fix this SQL:\n{sql}\nErrors: {errors}"
            sql = await self.llm.generate_text(prompt)
        
        return {"sql": sql, "warning": "Max iterations reached"}
```

**Tasks**:
- ✅ Validate SQL
- ✅ Use LLM to fix
- ✅ Iterate up to 3 times

---

### Step 4.4: Clarification Engine
**File**: `backend/app/services/clarification_service.py`

```python
class ClarificationService:
    def generate_questions(self, ambiguities):
        questions = []
        for amb in ambiguities:
            if amb["type"] == "ambiguous_column":
                questions.append(f"Column '{amb['column']}' exists in {amb['tables']}. Which?")
        return questions
    
    def resolve(self, ir, question, answer):
        # Parse answer and update IR
        pass
```

**Tasks**:
- ✅ Generate questions from ambiguities
- ✅ Parse user answers
- ✅ Update IR

---

### Step 4.5: Error Explainer
**File**: `backend/app/services/error_explainer.py`

```python
class ErrorExplainer:
    def explain(self, error, sql, schema):
        if "Unknown column" in str(error):
            return {
                "message": "Column does not exist",
                "suggestion": "Check column names"
            }
        # ... more patterns
```

**Tasks**:
- ✅ Parse common SQL errors
- ✅ Generate friendly messages
- ✅ Suggest fixes

---

### Step 4.6: Integrate into NL2SQL
**File**: `backend/app/api/v1/nl2sql.py`

```python
@router.post("/nl2sql")
async def nl2sql(
    req,
    context: ContextService = Depends(...),
    complexity: ComplexityAnalyzer = Depends(...),
    corrector: SQLCorrectorService = Depends(...),
):
    # 1. Load context
    conv = await context.get_context(req.conversation_id)
    
    # 2. Generate IR (with RAG)
    ir = ...
    
    # 3. Check clarifications
    if ir.questions:
        return {"clarifications_needed": ir.questions}
    
    # 4. Compile SQL
    sql = compile(ir)
    
    # 5. Analyze complexity
    analysis = complexity.analyze(ir)
    
    # 6. Self-correct if needed
    if analysis["score"] > 10:
        result = await corrector.correct_sql(sql, ir, schema)
        sql = result["sql"]
    
    # 7. Store in context
    await context.update_context(req.conversation_id, {...})
    
    return {"sql": sql, "complexity": analysis}
```

**Tasks**:
- ✅ Use all services
- ✅ Return complexity
- ✅ Handle clarifications

---

### Step 4.7: Frontend - Enhanced Playground
**File**: `frontend/src/pages/NLSQLPlayground.tsx`

**New Features**:
- Chat interface for multi-turn
- Complexity badge (simple/medium/hard)
- Correction indicator
- Clarification prompts
- Error explanations

**Tasks**:
- ✅ Add conversation UI
- ✅ Display complexity
- ✅ Show corrections
- ✅ Handle clarifications inline

---

# PHASE 5: SQL Execution & Security

## 5.1 Goals
- Safe SQL execution with timeouts
- Role-based access control (RBAC)
- Audit logging
- Query validation (prevent DROP, DELETE without WHERE)

## 5.2 Implementation Steps

### Step 5.1: SQL Executor
**File**: `backend/app/services/executor_service.py`

```python
class SQLExecutor:
    async def execute(self, sql, params, timeout_ms=30000, max_rows=10000):
        # Validate query (no DROP, DELETE without WHERE)
        self.validate_safe(sql)
        
        # Execute with timeout
        conn = await self.get_connection()
        try:
            result = await asyncio.wait_for(
                conn.execute(sql, params),
                timeout=timeout_ms / 1000
            )
            rows = result.fetchmany(max_rows)
            return {"rows": rows, "count": len(rows)}
        except asyncio.TimeoutError:
            raise Exception("Query timeout")
```

**Tasks**:
- ✅ Execute with timeout
- ✅ Limit rows
- ✅ Validate safety

---

### Step 5.2: RBAC System
**File**: `backend/app/services/rbac_service.py`

```python
class RBACService:
    def check_permission(self, user_id, database, operation):
        # Load user roles from Postgres
        roles = self.get_user_roles(user_id)
        
        # Check permissions
        if "admin" in roles:
            return True
        if operation == "SELECT" and "viewer" in roles:
            return True
        return False
```

**Tasks**:
- ✅ Define roles (admin, editor, viewer)
- ✅ Check permissions before execution
- ✅ Store in Postgres

---

### Step 5.3: Audit Logger
**File**: `backend/app/services/audit_service.py`

```python
class AuditService:
    async def log_query(self, user_id, query, sql, result, error=None):
        # Store in Postgres
        await self.db.execute(
            "INSERT INTO audit_log (user_id, query, sql, success, timestamp) VALUES (...)"
        )
```

**Tasks**:
- ✅ Log all queries
- ✅ Store in Postgres
- ✅ Include user, timestamp, success/failure

---

### Step 5.4: API Endpoints
**File**: `backend/app/api/v1/sql.py`

**Endpoints**:
- `POST /api/v1/sql/execute` - Execute SQL
- `POST /api/v1/sql/validate` - Validate SQL
- `GET /api/v1/sql/history` - Query history

**Tasks**:
- ✅ Implement endpoints
- ✅ Add RBAC checks
- ✅ Add audit logging

---

### Step 5.5: Frontend - Execution Page
**File**: `frontend/src/pages/SQLExecutor.tsx`

**Features**:
- Execute SQL button
- Results table
- Query history
- Export to CSV

**Tasks**:
- ✅ Create page
- ✅ Display results
- ✅ Add export

---

## 5.6 GNN Usage in Phase 5

**Query Validation**:
- Use GNN to predict if query is safe
- Train on: SQL features + GNN embeddings → safety score

**Performance Prediction**:
- Use GNN to estimate execution time
- Train on: query complexity + table sizes + GNN embeddings → time

---

# Summary & Timeline

## Phase 3 (RAG) - 2 weeks
- Week 1: Qdrant, embeddings, feedback service
- Week 2: RAG service, API, frontend

## Phase 4 (Enhancements) - 2 weeks
- Week 1: Context, complexity, corrector
- Week 2: Clarifications, errors, frontend

## Phase 5 (Execution) - 1 week
- Executor, RBAC, audit, frontend

## GNN Transition
- Develop with mock embeddings
- Upload real GNN embeddings
- Switch `EMBEDDING_PROVIDER=gnn`
- Verify improved quality

---

# Testing Strategy

## Unit Tests
- All services (Qdrant, feedback, RAG, context, complexity, corrector, executor)

## Integration Tests
- End-to-end: Submit feedback → RAG retrieval → Augmented prompt
- Multi-turn conversation
- SQL execution with RBAC

## Manual Tests
- Submit correction → Query similar → Verify prompt
- Multi-turn clarifications
- Execute SQL → Check audit log

---

# Files to Create

## Phase 3
- `backend/app/services/qdrant_service.py`
- `backend/app/services/embedding_service.py`
- `backend/app/services/feedback_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/api/v1/feedback.py`
- `frontend/src/pages/FeedbackManager.tsx`

## Phase 4
- `backend/app/services/context_service.py`
- `backend/app/services/complexity_service.py`
- `backend/app/services/corrector_service.py`
- `backend/app/services/clarification_service.py`
- `backend/app/services/error_explainer.py`
- Modify: `backend/app/api/v1/nl2sql.py`
- Modify: `frontend/src/pages/NLSQLPlayground.tsx`

## Phase 5
- `backend/app/services/executor_service.py`
- `backend/app/services/rbac_service.py`
- `backend/app/services/audit_service.py`
- `backend/app/api/v1/sql.py`
- `frontend/src/pages/SQLExecutor.tsx`
