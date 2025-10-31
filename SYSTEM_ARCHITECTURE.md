# NL2SQL System Architecture & Data Flow

## 🏗️ System Overview

```
User Query → Frontend → Backend API → LLM (Ollama/Gemini) → IR → SQL → MySQL → Results
                ↓                           ↓
            Schema Cache              RAG Examples
                ↓                           ↓
            Redis                      Qdrant
                ↓                           ↓
            GNN Embeddings          Feedback Storage
```

---

## 📊 Complete Data Flow

### 1. Schema Ingestion & Loading

```
MySQL Database (nl2sql_target)
    ↓
SchemaService.extract_schema()
    ↓ (SQLAlchemy inspection)
Schema JSON {tables, columns, relationships, indexes}
    ↓
SHA-256 Fingerprint (schema version)
    ↓
Redis Cache (key: schema:nl2sql_target, TTL: 1 hour)
    ↓
Frontend: GET /api/v1/schema
```

**Schema Structure**:
```json
{
  "database": "nl2sql_target",
  "version": "abc123def456...",
  "tables": {
    "customers": {
      "columns": [
        {"name": "customer_id", "type": "INT", "primary_key": true},
        {"name": "name", "type": "VARCHAR(255)"}
      ],
      "foreign_keys": [],
      "indexes": []
    }
  },
  "relationships": [
    {"from_table": "orders", "to_table": "customers", "from_columns": ["customer_id"]}
  ]
}
```

---

### 2. GNN Embeddings Flow

```
GNN Model (External/Kaggle)
    ↓
Generate embeddings for schema nodes
    ↓
JSON Format: {schema_fingerprint, dim, nodes: [{id, vec}]}
    ↓
POST /api/v1/schema/embeddings/upload
    ↓
GNNEmbeddingService.upload_embeddings()
    ↓
Redis Storage:
  - Key: gnn:{fingerprint}:node:{node_id}
  - Value: JSON array of floats
  - Meta: gnn:{fingerprint}:meta
    ↓
Used by RAG, Context, Clarification services
```

**GNN Node IDs**:
- Tables: `table:customers`
- Columns: `column:customers.name`
- Relationships: `rel:customers->orders`

**Embedding Dimensions**:
- Mock (sentence-transformers): 384-dim
- Real GNN: 512-dim (configurable)

---

### 3. NL → IR → SQL Flow (Current)

```
User: "top 5 customers by total spent"
    ↓
Frontend: POST /api/v1/nl2sql
    ↓
Backend: nl2sql endpoint
    ↓
1. Load Schema from Redis
    ↓
2. Build Prompt with schema_text
    ↓
3. LLMService.generate_json(prompt)
    ↓
   Ollama (http://localhost:11434/api/generate)
   OR
   Gemini API
    ↓
4. Parse JSON → QueryIR object
    ↓
5. IRValidator.validate(ir, schema)
    ↓
6. IRToMySQLCompiler.compile(ir)
    ↓
7. Return SQL + params
```

**IR Structure**:
```json
{
  "select": [
    {"type": "column", "value": "customers.name", "alias": "customer_name"},
    {"type": "column", "value": "customers.total_spent", "alias": "total"}
  ],
  "from_table": "customers",
  "joins": [],
  "where": [],
  "order_by": [{"column": "customers.total_spent", "direction": "DESC"}],
  "limit": 5,
  "confidence": 0.95,
  "ambiguities": []
}
```

---

### 4. Enhanced Flow with RAG (Phase 3)

```
User: "top customers"
    ↓
1. Load Schema
    ↓
2. Embed Query (EmbeddingService)
   - Mock: sentence-transformers
   - GNN: Map query → schema nodes → aggregate embeddings
    ↓
3. Search Qdrant for similar past queries
   Collection: nl2sql_feedback
   Filter: schema_fingerprint = current
   Top-K: 3 results
    ↓
4. Augment Prompt with examples
   Base Prompt + Similar Examples
    ↓
5. LLM generates better IR (learned from corrections)
    ↓
6. Compile to SQL
    ↓
7. Store as feedback (if successful)
```

**Qdrant Search**:
```python
query_vector = embedder.embed("top customers")  # [0.1, 0.2, ...]
results = qdrant.search(
    collection="nl2sql_feedback",
    query_vector=query_vector,
    filter={"schema_fingerprint": "abc123"},
    limit=3
)
# Returns: [
#   {score: 0.92, query: "best customers by revenue", sql: "SELECT ..."},
#   {score: 0.88, query: "top 10 customers", sql: "SELECT ..."}
# ]
```

---

### 5. Multi-Turn with Context (Phase 4)

```
Turn 1: "show orders"
    ↓
Context: {messages: [], schema_context: {}}
    ↓
Generate IR → SQL
    ↓
Store in Redis: context:{conversation_id}
    {messages: [{query: "show orders", sql: "SELECT * FROM orders"}]}

Turn 2: "from last month"
    ↓
Load Context from Redis
    ↓
Augment Prompt: "Previous: 'show orders' → SELECT * FROM orders. Now: 'from last month'"
    ↓
Generate IR with WHERE order_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
    ↓
Update Context

Turn 3: "by total amount"
    ↓
Load Context (knows we're querying orders from last month)
    ↓
Add ORDER BY total_amount DESC
```

**Context Storage (Redis)**:
```json
{
  "conversation_id": "conv_123",
  "messages": [
    {"query": "show orders", "sql": "SELECT * FROM orders", "timestamp": "..."},
    {"query": "from last month", "sql": "SELECT * FROM orders WHERE ...", "timestamp": "..."}
  ],
  "schema_context": {
    "active_tables": ["orders"],
    "active_columns": ["order_date", "total_amount"]
  },
  "clarifications": []
}
```

---

### 6. SQL Execution Flow (Phase 5)

```
Generated SQL + params
    ↓
1. RBAC Check
   user_id → roles → permissions
   Can user execute SELECT on nl2sql_target?
    ↓
2. Query Validation
   - No DROP/DELETE without WHERE
   - No TRUNCATE
   - Row limit check
    ↓
3. Execute with timeout (30s)
   MySQL connection pool
    ↓
4. Fetch results (max 10,000 rows)
    ↓
5. Audit Log (Postgres)
   {user_id, query, sql, success, timestamp, row_count}
    ↓
6. Return results to frontend
```

---

## 🗄️ Database Usage

### MySQL (Target Database)
- **Purpose**: User's data to query
- **Tables**: customers, orders, products, etc.
- **Access**: Read-only for NL2SQL
- **Connection**: `MYSQL_URI` in .env

### PostgreSQL (App Metadata)
- **Purpose**: Auth, audit, RBAC
- **Tables**:
  - `users` (id, email, password_hash, roles)
  - `audit_log` (id, user_id, query, sql, success, timestamp)
  - `permissions` (role, database, operation)
- **Connection**: `APP_DB_URI` in .env

### Redis (Cache & Context)
- **Purpose**: Fast access to schema, embeddings, context
- **Keys**:
  - `schema:{database}` → Schema JSON
  - `gnn:{fingerprint}:node:{id}` → GNN embedding vector
  - `gnn:{fingerprint}:meta` → Embedding metadata
  - `context:{conversation_id}` → Conversation state
- **TTL**: Schema (1h), Context (1h), GNN (permanent)
- **Connection**: `REDIS_URI` in .env

### Qdrant (Vector DB)
- **Purpose**: RAG feedback storage
- **Collections**:
  - `nl2sql_feedback` (384 or 512-dim)
  - `schema_embeddings` (512-dim for GNN)
- **Operations**: Upsert, vector search, filter by metadata
- **Connection**: `QDRANT_URL` in .env

---

## 🔄 GNN Mapping Details

### Schema Node Embedding
```
Table: customers
    ↓
GNN encodes:
  - Table name
  - Column names + types
  - Relationships (FK to orders, products)
  - Sample values (optional)
    ↓
512-dim vector: [0.12, -0.34, 0.56, ...]
    ↓
Stored in Redis: gnn:abc123:node:table:customers
```

### Query Embedding (GNN-based)
```
Query: "top customers by revenue"
    ↓
Tokenize: ["top", "customers", "revenue"]
    ↓
Map to schema nodes:
  - "customers" → table:customers
  - "revenue" → column:orders.total_amount (via semantic similarity)
    ↓
Retrieve GNN embeddings for matched nodes
    ↓
Aggregate (mean pooling): [0.08, -0.12, 0.34, ...]
    ↓
Use for Qdrant search
```

### Fallback (Mock Embeddings)
```
Query: "top customers by revenue"
    ↓
sentence-transformers.encode(query)
    ↓
384-dim vector: [0.05, 0.23, -0.11, ...]
```

---

## 🧪 Testing Different Schemas

### Small Schema (5 tables, 20 columns)
- Example: E-commerce (customers, orders, products, categories, order_items)
- Complexity: Simple joins, basic aggregations
- Test: "top products by sales"

### Medium Schema (15 tables, 80 columns)
- Example: CRM (customers, contacts, deals, activities, tasks, notes, etc.)
- Complexity: Multi-hop joins, nested aggregations
- Test: "deals closed last quarter by sales rep"

### Large Schema (50+ tables, 300+ columns)
- Example: ERP (inventory, procurement, finance, HR, etc.)
- Complexity: Complex joins, CTEs, window functions
- Test: "inventory turnover rate by warehouse and product category"

### Test Strategy
1. Upload schema to MySQL
2. Extract via `/api/v1/schema`
3. Generate GNN embeddings (or use mock)
4. Test queries of varying complexity
5. Submit corrections via feedback
6. Verify RAG improves subsequent queries

---

## 🚀 Startup Sequence

1. **Docker Compose Up**
   - MySQL, Postgres, Redis, Qdrant start
   - MySQL auto-seeds from `backend/db/mysql/seed.sql`

2. **Backend Starts**
   - Load config from `.env`
   - Initialize services (Schema, LLM, Cache, Qdrant)
   - Create Qdrant collections if missing
   - Health checks

3. **First Request**
   - Extract schema from MySQL
   - Cache in Redis
   - Return schema fingerprint

4. **Upload GNN Embeddings** (optional)
   - POST `/api/v1/schema/embeddings/upload`
   - Store in Redis

5. **Query Flow**
   - NL → IR (with RAG if embeddings exist)
   - IR → SQL
   - Execute (Phase 5)
   - Store feedback

---

## 📈 Performance Considerations

### Caching Strategy
- Schema: 1 hour TTL (refresh on schema changes)
- GNN embeddings: Permanent (invalidate on schema change)
- Context: 1 hour TTL (auto-expire inactive conversations)
- RAG results: No cache (always fresh search)

### Optimization
- Redis: In-memory, <1ms access
- Qdrant: HNSW index, <10ms vector search
- LLM: 2-5s (Ollama local), 1-2s (Gemini API)
- SQL execution: Depends on query complexity

### Scalability
- Horizontal: Multiple backend instances (stateless)
- Vertical: Redis cluster, Qdrant sharding
- LLM: Load balancing across Ollama instances

---

## 🔧 Configuration

### Environment Variables
```bash
# LLM
LLM_PROVIDER=ollama  # or gemini
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=mistral:latest
GEMINI_API_KEY=...

# Embeddings
EMBEDDING_PROVIDER=mock  # or gnn
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Databases
MYSQL_URI=mysql+pymysql://root:password@localhost:3306/nl2sql_target
APP_DB_URI=postgresql://postgres:password@localhost:5432/nl2sql_app
REDIS_URI=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Limits
MAX_QUERY_ROWS=10000
QUERY_TIMEOUT_MS=30000
SCHEMA_REFRESH_TTL_SEC=3600
```

---

## 🎯 Next Steps

1. **Fix 400 Error**: Add LLM health check, better error messages
2. **Implement Phase 3**: Qdrant, feedback, RAG
3. **Implement Phase 4**: Context, complexity, corrections
4. **Test Robustness**: Multiple schemas, complex queries
5. **UI Enhancements**: Test all stages, show data flow
