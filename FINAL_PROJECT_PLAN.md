# NL2SQL System - Final MVP Project Plan

## Executive Summary
Advanced NL2SQL system with GNN schema linking, RAG feedback, multi-turn conversations, IR-based query generation, and enterprise security.

---

## 1. Current State & Reuse Strategy

### ✅ Existing Assets (from `nl_to_sql_llm.py`)
- **SchemaVisualizer**: Schema extraction + NetworkX visualization → **Migrate to FastAPI service**
- **SchemaLinker**: Embedding-based schema linking (FAISS) → **Enhance with GNN embeddings**
- **SemanticCache**: Vector similarity cache → **Integrate with Qdrant**
- **ConversationContextManager**: Multi-turn context → **Add clarification strategies**
- **QueryComplexityAnalyzer**: Complexity scoring → **Keep as-is**
- **DataPreparationModule**: Data quality checks → **Keep as-is**
- **SQLSelfCorrection**: Schema validation + LLM correction → **Enhance with IR validation**
- **NL2SQLEngine**: Main orchestrator → **Refactor to use IR pipeline**

### 🔧 Tech Stack Decisions
| Component | Current | MVP Target | Rationale |
|-----------|---------|------------|-----------|
| LLM | Gemini 2.5 Flash | **Ollama (Mistral 7B) for NL→IR; Gemini for feedback** | Local dev-friendly; keeps high-quality feedback |
| Embeddings | all-MiniLM-L6-v2 | **Keep** | Fast, good quality |
| Vector DB | FAISS (in-memory) | **Qdrant** | Persistent, scalable, OSS |
| Database | SQLite | **MySQL 8.0+** | Production-ready, CTE/window support |
| Backend | Monolithic script | **FastAPI** | REST API, async, OpenAPI docs |
| Frontend | CLI | **React + Monaco** | Modern UI, SQL editing |
| GNN | None | **PyTorch Geometric** | Schema graph embeddings |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND: React + Monaco + TailwindCSS + shadcn/ui         │
│ • Chat UI (multi-turn) • SQL Editor • History • Auth       │
└─────────────────────────────────────────────────────────────┘
                            ↕ REST API (JWT)
┌─────────────────────────────────────────────────────────────┐
│ BACKEND: FastAPI + Python 3.11                              │
│ • Auth/RBAC Middleware • Rate Limiting • Audit Logging      │
│ • NL2SQL API • Schema API • Feedback API • SQL Exec API     │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│ NL2SQL ENGINE (Modular Pipeline)                            │
│ 1. Schema Extractor (MySQL INFORMATION_SCHEMA + caching)    │
│ 2. GNN Embedder (PyTorch Geometric schema graph)            │
│ 3. Schema Linker (Fusion: text embeddings + GNN)            │
│ 4. RAG Retriever (Qdrant: similar corrections)              │
│ 5. NL→IR Generator (Ollama: Mistral 7B + schema context)     │
│ 6. IR Validator (schema checks, SQL rules)                  │
│ 7. IR→MySQL Compiler (parameterized SQL)                    │
│ 8. SQL Executor (RBAC enforcement, audit log)               │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                   │
│ • MySQL (target DB) • Qdrant (feedback vectors)             │
│ • Redis (schema/embedding cache) • Postgres (auth/audit)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Phases

### Phase 0: Foundation (3-4 days)
**Goal**: Restructure existing code into production architecture

**Tasks**:
1. Create modular backend structure (FastAPI + services)
2. Migrate existing classes from `nl_to_sql_llm.py` to services
3. Setup Docker Compose (MySQL, Qdrant, Redis, Postgres)
4. Implement JWT auth + RBAC scaffolding
5. Add Pydantic models and type hints
6. Write unit tests for migrated components

**Deliverables**:
- ✅ FastAPI backend with health endpoints
- ✅ Docker environment running
- ✅ Migrated services with tests (70%+ coverage)

---

### Phase 1: Schema + IR + Compiler (5-7 days)
**Goal**: Build IR layer and MySQL schema management

**1.1 MySQL Schema Service**
- Extract schema from `INFORMATION_SCHEMA` (tables, columns, FKs, PKs, indexes)
- Compute schema fingerprint (SHA256 hash)
- Redis caching with TTL
- Schema diff engine (detect added/removed/modified tables/columns)
- Change detection service (periodic polling or binlog listener)

**1.2 IR Schema Definition**
```python
# Core IR structure (Pydantic models)
QueryIR:
  - ctes: List[CTE]                    # Common Table Expressions
  - select: List[Expression]           # SELECT targets
  - from_table: str
  - joins: List[Join]
  - where: List[Predicate]
  - group_by: List[str]
  - having: List[Predicate]
  - order_by: List[OrderBy]
  - limit/offset: Optional[int]
  - parameters: Dict[str, Any]         # Safe parameter binding

Expression:
  - type: column | literal | function | aggregate | window | subquery
  - window: Optional[WindowFunction]   # ROW_NUMBER, RANK, etc.
  
WindowFunction:
  - function: str
  - partition_by: List[str]
  - order_by: List[OrderBy]
  - frame: Optional[WindowFrame]       # ROWS/RANGE BETWEEN ...
```

**1.3 IR Validator**
- Schema existence checks (tables, columns)
- GROUP BY validation (non-aggregated columns)
- Window function validation
- CTE circular reference detection
- Type compatibility checks

**1.4 IR→MySQL Compiler**
- Generate parameterized SQL from IR
- Support CTEs (MySQL 8+)
- Support window functions (MySQL 8+)
- Parameterized subqueries with safe binding
- Dialect gating (fallback for MySQL <8)

**Deliverables**:
- ✅ Schema service with change detection
- ✅ IR Pydantic models with full validation
- ✅ IR→MySQL compiler with 20+ test cases
- ✅ API endpoints: `GET /schema`, `POST /schema/refresh`

---

### Phase 2: GNN Schema Embeddings (7-10 days)
**Goal**: Graph-aware schema embeddings for better NL→schema mapping

**2.1 Schema Graph Construction**
```python
# Node types: Table, Column
# Edge types: TABLE_CONTAINS_COLUMN, FOREIGN_KEY, PRIMARY_KEY, SAME_TABLE, TYPE_COMPATIBLE

Graph:
  - Nodes: {table_name, column_name, data_type, is_pk, is_fk, stats}
  - Edges: {relation_type, from_node, to_node}
```

**2.2 GNN Model (PyTorch Geometric)**
- Heterogeneous GNN (R-GCN or GraphSAGE)
- Node features: name embeddings (BPE), type encoding, degree, table stats
- Edge features: relation type embeddings
- Output: 256-768 dim node embeddings

**2.3 Training Strategy**
- **Unsupervised**: Link prediction (predict FK relationships)
- **Supervised** (optional): Fine-tune on NL→schema alignment dataset
- Precompute embeddings per schema version
- Cache in Redis with schema fingerprint key

**2.4 Fusion with Text Embeddings**
- Combine sentence-transformer embeddings (NL query) with GNN embeddings (schema)
- Cross-attention or learned fusion layer
- Rank schema elements by fused similarity

**Deliverables**:
- ✅ GNN model trained on sample schemas
- ✅ Embedding service with caching
- ✅ Fusion module for schema linking
- ✅ API: `POST /schema/embed`, `POST /nl/link-schema`

---

### Phase 3: RAG Feedback Loop (7-10 days)
**Goal**: Learn from user corrections without retraining

**3.1 Qdrant Vector DB Setup**
- Collection schema: `{query_text, generated_sql, corrected_sql, schema_fingerprint, tables_used, embedding, metadata}`
- Embedding model: `all-MiniLM-L6-v2` (same as cache)

**3.2 Feedback Storage**
- User submits correction: `POST /feedback`
- Generate embedding of NL query + schema context
- Upsert to Qdrant with metadata

**3.3 RAG Retrieval**
- On new NL query, retrieve top-k similar corrections
- Filter by schema overlap (same tables/columns)
- Build few-shot prompt with corrections as examples

**3.4 Prompt Augmentation**
```python
# Enhanced prompt structure:
"""
SCHEMA: {schema_text}
GNN INSIGHTS: {top_relevant_columns}

PAST CORRECTIONS (similar queries):
1. User asked: "..." → Generated: "..." → Corrected to: "..."
2. ...

CURRENT QUERY: {user_question}

Generate IR JSON:
"""
```

**Deliverables**:
- ✅ Qdrant integration with feedback collection
- ✅ RAG retrieval service
- ✅ Prompt augmentation in NL2SQL engine
- ✅ API: `POST /feedback`, `GET /feedback/similar`

---

### Phase 4: NL2SQL Engine with IR (7-10 days)
**Goal**: Refactor engine to use IR pipeline

**4.1 Ollama Integration (Mistral 7B for NL→IR)**
- Use local Ollama endpoint for inference (Windows-friendly)
- Model: `mistral:latest` (or smaller instruct models for dev)
- Constrained decoding to valid IR JSON
- Optional fallback: Gemini for self-correction/feedback only

**4.2 NL→IR Generation**
- Prompt with schema + GNN insights + RAG corrections
- Generate IR JSON (not SQL directly)
- Parse and validate IR
- If validation fails → trigger clarification

**4.3 Multi-turn Clarification**
- Detect ambiguities:
  - Low confidence column/table mapping
  - Multiple candidate joins
  - Missing filters
- Generate clarification questions:
  - "Which 'date' do you mean: `orders.order_date` or `shipments.ship_date`?"
- Store conversation state with unresolved slots
- Re-generate IR after clarification

**4.4 Error Explanations**
- IR validation errors → user-friendly messages
- SQL execution errors → parse MySQL error codes, suggest fixes
- Return `{sql, ir, confidence, ambiguities[], explanations[], suggested_fixes[]}`

**Deliverables**:
- ✅ Ollama wired for NL→IR (Mistral 7B)
- ✅ NL→IR generation with constrained decoding
- ✅ Clarification UX (backend logic)
- ✅ API: `POST /nl2ir`, `POST /clarify`, `POST /nl2sql`

---

### GNN Embeddings Ingestion (External Training on Kaggle)
**Goal**: Pull precomputed node embeddings produced externally and cache by schema fingerprint.

**Ingestion Methods**
- **Pull by URL**: `POST /schema/embeddings/pull` with `{ schema_fingerprint, url }` to fetch JSON/NPY artifacts.
- **Direct Upload**: `POST /schema/embeddings/upload` (multipart) with JSON:
  ```json
  {
    "schema_fingerprint": "<hash>",
    "dim": 512,
    "nodes": [
      {"id": "table:orders", "vec": [..]},
      {"id": "column:orders.order_id", "vec": [..]}
    ]
  }
  ```
- **Kaggle API (optional)**: worker pulls latest dataset using `KAGGLE_USERNAME`/`KAGGLE_KEY`.

**Validation & Caching**
- Validate artifact `schema_fingerprint` matches current DB fingerprint.
- Ensure all `node_id` match graph nodes.
- Cache vectors in Redis as `gnn:<fingerprint>:node:<node_id>`; optionally mirror to Qdrant for analytics.

---

### Schema Fingerprinting Details
**What**: Stable hash (e.g., first 16 chars of SHA-256) of a canonical JSON describing tables, columns (names/types), PKs, FKs, and relationships.

**How**
- Extract schema via `INFORMATION_SCHEMA`, build deterministic JSON (sorted keys), SHA-256 → `schema_fingerprint`.

**Why**
- Namespaces caches (schema, embeddings, autocomplete).
- Prevents cross-contamination across versions/databases.
- Triggers invalidation and partial re-embedding on change (diff engine or binlog).

---

### Multi-user & Multi-database Readiness (Future)
- **Namespacing**: Include `org_id`, `project_id`, `database_id`, `schema_fingerprint` in cache keys, RAG metadata, and audit logs.
- **RAG Visibility**: `visibility=global|org|user` on corrections to avoid cross-tenant leakage.
- **DB Scoping**: Each session bound to a `database_id`; Monaco autocomplete fetched per active schema fingerprint.
- **RBAC**: Per-tenant table/column policies evaluated pre-execution.

---

### Phase 5: Frontend (React + Monaco) (6-8 days)
**Goal**: Modern web UI for NL2SQL interaction

**5.1 Tech Stack**
- React 18 + TypeScript + Vite
- TailwindCSS + shadcn/ui components
- Monaco Editor (SQL language support)
- Zustand (state management)
- React Query (API calls)

**5.2 Components**
- **ChatInterface**: Multi-turn conversation with clarification prompts
- **MonacoEditor**: SQL editing with syntax highlighting, autocomplete (schema-aware), linting
- **QueryHistory**: Past queries with versioning, re-run, export
- **SchemaViewer**: Interactive schema graph (D3.js or Cytoscape.js)
- **AuthUI**: Login, JWT refresh, user profile

**5.3 Features**
- Real-time SQL validation (call `/sql/validate`)
- Autocomplete from schema metadata
- Inline error explanations with "Apply fix" buttons
- Query execution preview (EXPLAIN)
- Download results (CSV/JSON)
- Dark mode

**Deliverables**:
- ✅ React app with all components
- ✅ Monaco SQL editor with schema autocomplete
- ✅ Multi-turn chat with clarification UX
- ✅ Dockerized frontend

---

### Phase 6: Security + Observability (4-6 days)
**Goal**: Production-ready security and monitoring

**6.1 Security**
- **Input Sanitization**: Validate all inputs, reject DDL/DML unless allowed
- **Parameterized Queries**: Only execute with bound parameters (no string concatenation)
- **RBAC**: Roles (viewer, analyst, admin) with table/column-level policies
- **RBAC Enforcement**: Pre-execution check: parse SQL, validate against policy
- **Audit Logging**: Store all queries with user, timestamp, SQL, params, row count, latency

**6.2 Observability**
- Structured logging (JSON) with correlation IDs
- Metrics: query latency, cache hit rate, error rate, model inference time
- Health checks: `/health`, `/health/db`, `/health/vector-db`
- Rate limiting per user/IP

**Deliverables**:
- ✅ RBAC middleware with policy enforcement
- ✅ Audit log service (Postgres table)
- ✅ Structured logging with correlation IDs
- ✅ Metrics endpoints (Prometheus format)

---

### Phase 7: Testing + Deployment (4-6 days)
**Goal**: Comprehensive testing and Docker deployment

**7.1 Testing**
- **Unit Tests**: IR validator, compiler, schema service, GNN embedder (70%+ coverage)
- **Integration Tests**: End-to-end NL→IR→SQL→DB with mock schema
- **RAG Tests**: Verify corrections improve generation
- **Security Tests**: RBAC deny cases, injection attempts blocked

**7.2 Deployment**
- Dockerfiles for backend, frontend, workers
- `docker-compose.yml` for local dev (all services)
- `.env.example` with all required variables
- CI/CD: GitHub Actions (lint, test, build, push images)

**7.3 Documentation**
- API docs (OpenAPI/Swagger)
- Developer README with quickstart
- Sample dataset + queries
- Architecture diagrams

**Deliverables**:
- ✅ Test suite with 70%+ coverage
- ✅ Docker Compose for one-command startup
- ✅ Comprehensive README + API docs

---

## 4. API Endpoints Summary

### Auth
- `POST /auth/login` → JWT tokens
- `POST /auth/refresh` → Refresh access token

### Schema
- `GET /schema` → Current schema with version
- `POST /schema/refresh` → Force schema refresh, return diff
- `GET /schema/graph` → Schema graph JSON for visualization
- `POST /schema/embed` → Trigger GNN embedding recompute

### NL2SQL
- `POST /nl2ir` → Generate IR from NL (returns IR + confidence + ambiguities)
- `POST /clarify` → Resolve ambiguities, re-generate IR
- `POST /ir2sql` → Compile IR to SQL
- `POST /nl2sql` → End-to-end NL→SQL (uses RAG + IR internally)

### SQL
- `POST /sql/validate` → Validate SQL, return diagnostics
- `POST /sql/execute` → Execute SQL with RBAC + audit
- `GET /sql/history` → User's query history

### Feedback
- `POST /feedback` → Submit correction (NL, generated SQL, corrected SQL)
- `GET /feedback/similar?query=...` → Retrieve similar corrections

### Admin
- `GET /audit` → Audit logs (admin only)
- `POST /rbac/policy` → Update RBAC policies

---

## 5. Environment Variables

```bash
# Backend
APP_ENV=development
SECRET_KEY=<random-secret>
JWT_EXP_MIN=30
LOG_LEVEL=INFO

# Databases
MYSQL_URI=mysql+pymysql://user:pass@mysql:3306/target_db
APP_DB_URI=postgresql://user:pass@postgres:5432/app_db
REDIS_URI=redis://redis:6379/0

# Vector DB
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=  # Optional for OSS

# Model
HF_TOKEN=<huggingface-token>  # For gated models
MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.2
PEFT_ADAPTER_PATH=./models/nl2sql_lora
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Limits
MAX_QUERY_ROWS=10000
QUERY_TIMEOUT_MS=30000
RATE_LIMIT_PER_MIN=60

# Schema
SCHEMA_REFRESH_TTL_SEC=3600
SCHEMA_DIFF_STRATEGY=fingerprint  # or binlog
BINLOG_ENABLED=false
BINLOG_HOST=mysql
BINLOG_PORT=3306

# Features
IR_ADVANCED_FEATURES_ENABLED=true  # CTE, window functions
CLARIFY_CONFIDENCE_THRESHOLD=0.7
CLARIFY_MAX_TURNS=3
ERROR_EXPLAIN_VERBOSE=true

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

---

## 6. External API Keys Required

| Service | Purpose | How to Get | Required? |
|---------|---------|------------|-----------|
| **Hugging Face** | Download Mistral 7B weights | huggingface.co/settings/tokens | ✅ Yes |
| **Qdrant Cloud** (optional) | Hosted vector DB | cloud.qdrant.io | ❌ No (use OSS) |
| **OpenAI** (optional) | Fallback LLM for comparison | platform.openai.com | ❌ No |

**Note**: For MVP, use **OSS Qdrant** (Docker) and **Mistral 7B** (HuggingFace) - no paid keys required except HF token for gated models.

---

## 7. Success Criteria (MVP Acceptance)

- ✅ NL query produces correct SQL for 3-table join + aggregation on sample schema
- ✅ IR JSON is always valid and compilable to MySQL
- ✅ GNN embeddings improve schema linking accuracy vs baseline (measured on test set)
- ✅ RAG improves SQL correctness after 1+ user correction (A/B test)
- ✅ Monaco editor shows schema-aware autocomplete and inline errors
- ✅ RBAC blocks restricted column access; audit logs capture event
- ✅ Multi-turn clarification resolves ambiguous query (e.g., "Which date?")
- ✅ System handles schema change (add column) and invalidates caches correctly
- ✅ End-to-end latency <5s for simple query, <15s for complex query
- ✅ Test suite passes with 70%+ coverage

---

## 8. Timeline Summary

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0: Foundation | 3-4 days | 4 days |
| Phase 1: Schema + IR | 5-7 days | 11 days |
| Phase 2: GNN Embeddings | 7-10 days | 21 days |
| Phase 3: RAG Feedback | 7-10 days | 31 days |
| Phase 4: NL2SQL Engine | 7-10 days | 41 days |
| Phase 5: Frontend | 6-8 days | 49 days |
| Phase 6: Security + Observability | 4-6 days | 55 days |
| Phase 7: Testing + Deployment | 4-6 days | **61 days (~9 weeks)** |

**Buffer**: Add 20% for unknowns → **~11 weeks total**

---

## 9. Next Steps

1. **Confirm Tech Choices**:
   - ✅ Mistral 7B Instruct (vs LLaMA 2)?
   - ✅ Qdrant OSS (vs Weaviate)?
   - ✅ Separate Postgres for auth/audit (vs MySQL)?

2. **Start Phase 0**:
   - Create repo structure
   - Setup Docker Compose
   - Migrate `SchemaVisualizer` → `SchemaService`
   - Migrate `SchemaLinker` → `SchemaLinkingService`
   - Migrate `SemanticCache` → `CacheService`
   - Migrate `ConversationContextManager` → `ContextService`
   - Migrate `NL2SQLEngine` → `NL2SQLService` (refactor for IR)

3. **Parallel Workstreams** (if team >1):
   - **Backend**: Schema service + IR (Phase 1)
   - **ML**: GNN model training (Phase 2)
   - **Frontend**: React scaffold + Monaco (Phase 5 early start)

---

## 10. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| GNN training slow/complex | Start with simple R-GCN; use pretrained node embeddings |
| Mistral 7B too large for dev | Use quantized 4-bit version (bitsandbytes) |
| IR generation fails often | Fallback to direct SQL generation; log failures for fine-tuning |
| Schema change detection misses events | Start with polling; add binlog later as enhancement |
| RAG doesn't improve quality | Measure with A/B test; tune retrieval threshold |
| Frontend complexity | Use shadcn/ui templates; defer advanced features |

---

## 11. Post-MVP Enhancements

- Fine-tune Mistral on domain-specific NL2SQL dataset
- Binlog-based schema change detection (real-time)
- Multi-database support (Postgres, BigQuery)
- Query optimization hints (index suggestions)
- Natural language result explanations
- Voice input (speech-to-text)
- Collaborative query building (multi-user)
- Query performance profiling dashboard

---

**END OF PLAN**

**Ready to start? Confirm tech choices and I'll begin Phase 0 scaffolding.**
