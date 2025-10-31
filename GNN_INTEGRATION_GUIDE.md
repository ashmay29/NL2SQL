# GNN Integration Guide
## Complete Guide for Integrating External GNN Model with NL2SQL System

---

## 🎯 Overview

This guide explains how the NL2SQL system integrates with an external Graph Neural Network (GNN) model for enhanced schema understanding and query embedding generation.

### Architecture Flow

```
User Query (NL) 
    ↓
[Data Ingestion] → CSV/Excel/DB Tables → Schema Extraction
    ↓
[Schema → Graph Conversion] → Nodes (tables/columns) + Edges (relationships)
    ↓
[Sentence Transformer] → Text Embeddings (384-dim)
    ↓
[GNN Model Inference] → Graph-aware Embeddings (512-dim)
    ↓
[Redis Cache] → Fast retrieval for subsequent queries
    ↓
[Prompt Builder] → Enhanced prompt with relevant schema context
    ↓
[LLM (Gemini)] → SQL Generation
```

---

## 📁 New Components Added

### **1. Data Ingestion Service**
**File**: `backend/app/services/data_ingestion_service.py`

**Purpose**: Handle multiple data formats and extract schema

**Capabilities**:
- ✅ CSV file ingestion with delimiter/encoding support
- ✅ Excel file ingestion (single or multi-sheet)
- ✅ Database table ingestion with statistics
- ✅ Parquet file support
- ✅ JSON file support
- ✅ Automatic schema fingerprinting
- ✅ Column statistics (null counts, cardinality, min/max, etc.)

**Key Methods**:
```python
# Ingest CSV
schema = ingestion_service.ingest_csv(file, table_name, delimiter=",")

# Ingest Excel
schema = ingestion_service.ingest_excel(file, sheet_name="Sheet1")

# Ingest DB table
schema = ingestion_service.ingest_database_table(database, table_name)

# Merge multiple schemas
unified_schema = ingestion_service.merge_schemas([schema1, schema2, ...])
```

---

### **2. GNN Inference Service**
**File**: `backend/app/services/gnn_inference_service.py`

**Purpose**: Communicate with external GNN model server

**Architecture**:
- **External GNN Server**: Separate service hosting the trained GNN model
- **HTTP Communication**: Async HTTP client (httpx) for inference requests
- **Mock Fallback**: Deterministic hash-based embeddings when GNN unavailable
- **Graph Conversion**: Converts schema to graph representation

**Key Methods**:
```python
# Generate schema embeddings
embeddings = await gnn_service.generate_schema_embeddings(schema)
# Returns: {"table:customers": [0.1, 0.2, ...], "column:orders.id": [...], ...}

# Generate query embedding
query_emb = await gnn_service.generate_query_embedding(query_text, schema)
# Returns: [0.3, 0.4, ...] (512-dim vector)

# Find relevant nodes
nodes = await gnn_service.get_relevant_schema_nodes(query_emb, schema_embs, top_k=10)
# Returns: [{"node_id": "table:customers", "similarity": 0.92, ...}, ...]

# Health check
health = await gnn_service.health_check()
```

**Graph Representation**:
```json
{
  "nodes": [
    {"id": "table:customers", "type": "table", "properties": {...}},
    {"id": "column:customers.id", "type": "column", "properties": {...}}
  ],
  "edges": [
    {"source": "table:customers", "target": "column:customers.id", "type": "has_column"},
    {"source": "column:orders.customer_id", "target": "column:customers.id", "type": "foreign_key"}
  ]
}
```

---

### **3. Enhanced Embedding Service**
**File**: `backend/app/services/enhanced_embedding_service.py`

**Purpose**: Orchestrate GNN + Sentence Transformer with intelligent fallback

**Priority Chain**:
1. **Check Redis cache** → Return if hit
2. **Try GNN service** → If endpoint configured and available
3. **Fall back to Sentence Transformer** → If GNN fails or unavailable
4. **Cache result** → Store in Redis for future requests

**Key Methods**:
```python
# Embed query (with schema context)
query_emb = await embedding_service.embed_query(query_text, schema)

# Embed entire schema
schema_embs = await embedding_service.embed_schema(schema, force_regenerate=False)

# Embed single node
node_emb = await embedding_service.embed_schema_node(node_id, metadata, schema)

# Get relevant context for query
relevant_nodes = await embedding_service.get_relevant_schema_context(
    query_text, schema, top_k=10
)

# Invalidate cache after schema change
await embedding_service.invalidate_cache(fingerprint)
```

---

## 🔌 API Endpoints

### **Data Ingestion Endpoints**

#### **1. Upload CSV**
```http
POST /api/v1/data/upload/csv
Content-Type: multipart/form-data

file: <csv_file>
table_name: "customers"
delimiter: ","
encoding: "utf-8"
generate_embeddings: true
```

**Response**:
```json
{
  "success": true,
  "table_name": "customers",
  "fingerprint": "a1b2c3d4e5f6g7h8",
  "row_count": 1000,
  "column_count": 5,
  "source_type": "csv",
  "message": "Successfully ingested CSV file",
  "schema": {...}
}
```

#### **2. Upload Excel**
```http
POST /api/v1/data/upload/excel
Content-Type: multipart/form-data

file: <excel_file>
table_name: "sales"
sheet_name: "Sheet1"
generate_embeddings: true
```

#### **3. Ingest Database Table**
```http
POST /api/v1/data/ingest/database-table
Content-Type: application/json

{
  "database": "nl2sql_target",
  "table_name": "orders",
  "sample_size": 1000,
  "generate_embeddings": true
}
```

#### **4. Get Supported Formats**
```http
GET /api/v1/data/formats
```

---

### **GNN Management Endpoints**

#### **1. Generate Schema Embeddings**
```http
POST /api/v1/gnn/embeddings/generate
Content-Type: application/json

{
  "database": "nl2sql_target",
  "force_regenerate": false
}
```

**Response**:
```json
{
  "success": true,
  "database": "nl2sql_target",
  "fingerprint": "b1b2006dfa0a2d01",
  "embeddings_count": 47,
  "dimension": 512,
  "tables": 5,
  "message": "Embeddings generated successfully"
}
```

#### **2. Generate Query Embedding**
```http
POST /api/v1/gnn/embeddings/query
Content-Type: application/json

{
  "query_text": "show me top 5 customers",
  "database": "nl2sql_target",
  "context": {}
}
```

#### **3. Find Relevant Schema Nodes**
```http
POST /api/v1/gnn/similarity/relevant-nodes
Content-Type: application/json

{
  "query_text": "total sales by customer",
  "database": "nl2sql_target",
  "top_k": 10
}
```

**Response**:
```json
{
  "success": true,
  "query": "total sales by customer",
  "database": "nl2sql_target",
  "nodes": [
    {
      "node_id": "table:customers",
      "similarity": 0.92,
      "embedding": [...]
    },
    {
      "node_id": "column:orders.total_amount",
      "similarity": 0.87,
      "embedding": [...]
    }
  ],
  "count": 10
}
```

#### **4. GNN Health Check**
```http
GET /api/v1/gnn/health
```

**Response (GNN Available)**:
```json
{
  "status": "healthy",
  "endpoint": "http://gnn-server:8080",
  "details": {...}
}
```

**Response (Mock Mode)**:
```json
{
  "status": "mock",
  "message": "GNN endpoint not configured, using mock mode"
}
```

#### **5. Invalidate Embeddings Cache**
```http
DELETE /api/v1/gnn/embeddings/invalidate/{database}
```

#### **6. GNN Service Info**
```http
GET /api/v1/gnn/info
```

---

## ⚙️ Configuration

### **Environment Variables** (`.env`)

```bash
# Embeddings Configuration
EMBEDDING_PROVIDER=enhanced  # Use enhanced mode (GNN + fallback)
EMBEDDING_DIM=512           # GNN embedding dimension

# GNN Service
GNN_ENDPOINT=http://gnn-server:8080  # External GNN model server
GNN_TIMEOUT=30                       # Request timeout
USE_GNN_FALLBACK=true               # Enable SentenceTransformer fallback

# Data Ingestion
ENABLE_FILE_UPLOAD=true
MAX_UPLOAD_SIZE_MB=100
SUPPORTED_FORMATS=csv,excel,parquet,json
```

### **Modes of Operation**

1. **Full GNN Mode** (Production):
   ```bash
   EMBEDDING_PROVIDER=enhanced
   GNN_ENDPOINT=http://gnn-server:8080
   USE_GNN_FALLBACK=true
   ```

2. **Mock Mode** (Development/Testing):
   ```bash
   EMBEDDING_PROVIDER=enhanced
   GNN_ENDPOINT=  # Empty = mock mode
   USE_GNN_FALLBACK=true
   ```

3. **SentenceTransformer Only**:
   ```bash
   EMBEDDING_PROVIDER=mock
   ```

---

## 🔄 Integration Workflow

### **Step 1: Data Ingestion**

Upload your data source (CSV, Excel, or use existing DB table):

```bash
curl -X POST "http://localhost:8000/api/v1/data/upload/csv" \
  -F "file=@customers.csv" \
  -F "table_name=customers" \
  -F "generate_embeddings=true"
```

This will:
1. Parse the file and extract schema
2. Compute schema fingerprint
3. Generate embeddings (GNN or fallback)
4. Cache embeddings in Redis

### **Step 2: Query with Enhanced Context**

When you submit a query via `/api/v1/nl2sql`:

```bash
curl -X POST "http://localhost:8000/api/v1/nl2sql" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "show me top 5 customers by total spent",
    "database_id": "nl2sql_target",
    "conversation_id": "conv-123"
  }'
```

**Behind the scenes**:
1. Query embedding generated (GNN or SentenceTransformer)
2. Schema embeddings retrieved from cache
3. Top-K relevant schema nodes identified via cosine similarity
4. Relevant tables/columns included in LLM prompt
5. SQL generated with better context awareness

### **Step 3: Monitor GNN Health**

```bash
curl "http://localhost:8000/api/v1/gnn/health"
```

---

## 🧪 Testing the Integration

### **1. Test Data Ingestion**

```python
import requests

# Upload CSV
with open('customers.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/data/upload/csv',
        files={'file': f},
        data={
            'table_name': 'customers',
            'generate_embeddings': True
        }
    )
    print(response.json())
```

### **2. Test GNN Embeddings**

```python
# Generate embeddings
response = requests.post(
    'http://localhost:8000/api/v1/gnn/embeddings/generate',
    json={'database': 'nl2sql_target', 'force_regenerate': False}
)
print(f"Generated {response.json()['embeddings_count']} embeddings")

# Find relevant nodes
response = requests.post(
    'http://localhost:8000/api/v1/gnn/similarity/relevant-nodes',
    json={
        'query_text': 'total revenue by customer',
        'database': 'nl2sql_target',
        'top_k': 5
    }
)
for node in response.json()['nodes']:
    print(f"{node['node_id']}: {node['similarity']:.2f}")
```

### **3. Test End-to-End NL2SQL**

```python
response = requests.post(
    'http://localhost:8000/api/v1/nl2sql',
    json={
        'query_text': 'show me top 10 customers by total orders',
        'database_id': 'nl2sql_target',
        'use_cache': True
    }
)
print(response.json()['sql'])
```

---

## 🚀 Deploying External GNN Server

### **GNN Server Requirements**

Your external GNN server should expose these endpoints:

#### **1. Schema Inference**
```http
POST /infer/schema
Content-Type: application/json

{
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "schema_fingerprint": "abc123",
  "force_regenerate": false
}
```

**Response**:
```json
{
  "embeddings": {
    "table:customers": [0.1, 0.2, ...],
    "column:orders.id": [0.3, 0.4, ...]
  }
}
```

#### **2. Query Inference**
```http
POST /infer/query
Content-Type: application/json

{
  "query": "show me top customers",
  "graph": {...},
  "context": {}
}
```

**Response**:
```json
{
  "embedding": [0.5, 0.6, ...]
}
```

#### **3. Similarity Search**
```http
POST /similarity/top_k
Content-Type: application/json

{
  "query_embedding": [...],
  "schema_embeddings": {...},
  "top_k": 10
}
```

**Response**:
```json
{
  "nodes": [
    {"node_id": "table:customers", "similarity": 0.92, "embedding": [...]},
    ...
  ]
}
```

#### **4. Health Check**
```http
GET /health
```

### **Example Docker Compose for GNN Server**

```yaml
services:
  gnn-server:
    image: your-gnn-model:latest
    ports:
      - "8080:8080"
    environment:
      - MODEL_PATH=/models/gnn_model.pt
      - DEVICE=cuda  # or cpu
    volumes:
      - ./models:/models
    networks:
      - nl2sql-network
```

---

## 📊 Performance Considerations

### **Caching Strategy**

1. **Schema Embeddings**: Cached for 2 hours (7200s)
2. **Query Embeddings**: Cached for 1 hour (3600s)
3. **Cache Key Format**:
   - Schema: `schema_emb:{fingerprint}`
   - Query: `query_emb:{hash(query_text)}`
   - Node: `gnn:{fingerprint}:node:{node_id}`

### **Fallback Behavior**

| Scenario | Behavior |
|----------|----------|
| GNN endpoint not configured | Use SentenceTransformer immediately |
| GNN request timeout | Fall back to SentenceTransformer, log warning |
| GNN returns error | Fall back to SentenceTransformer, log error |
| Cache hit | Return cached embedding (no GNN call) |

### **Optimization Tips**

1. **Pre-generate embeddings** for known schemas:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/gnn/embeddings/generate" \
     -H "Content-Type: application/json" \
     -d '{"database": "nl2sql_target", "force_regenerate": true}'
   ```

2. **Invalidate cache** after schema changes:
   ```bash
   curl -X DELETE "http://localhost:8000/api/v1/gnn/embeddings/invalidate/nl2sql_target"
   ```

3. **Monitor GNN health** periodically to detect failures early

---

## 🔍 Debugging

### **Enable Debug Logging**

```bash
# In .env
LOG_LEVEL=DEBUG
```

### **Check GNN Service Status**

```bash
curl http://localhost:8000/api/v1/gnn/info
```

### **Inspect Cached Embeddings**

```python
import redis
r = redis.from_url('redis://localhost:6379/0', decode_responses=True)

# List all schema embeddings
keys = r.keys('schema_emb:*')
print(f"Cached schemas: {len(keys)}")

# Get specific embedding
embedding = r.get('schema_emb:b1b2006dfa0a2d01')
```

### **Test Mock Fallback**

```bash
# Temporarily disable GNN
export GNN_ENDPOINT=""

# Query should still work with SentenceTransformer
curl -X POST "http://localhost:8000/api/v1/nl2sql" ...
```

---

## 📝 Summary

### **What Was Added**

1. ✅ **Data Ingestion Service** - Multi-format data source support
2. ✅ **GNN Inference Service** - External GNN model integration
3. ✅ **Enhanced Embedding Service** - GNN + SentenceTransformer orchestration
4. ✅ **API Endpoints** - `/api/v1/data/*` and `/api/v1/gnn/*`
5. ✅ **Configuration** - Environment variables for GNN endpoint
6. ✅ **Fallback Mechanism** - Graceful degradation to SentenceTransformer
7. ✅ **Caching Layer** - Redis caching for performance

### **Current State**

- **Mock Mode Active**: System works without external GNN (uses hash-based embeddings)
- **Backward Compatible**: Existing functionality preserved
- **Production Ready**: Can integrate real GNN server by setting `GNN_ENDPOINT`

### **Next Steps to Full Integration**

1. Deploy external GNN model server
2. Set `GNN_ENDPOINT` in `.env`
3. Test with `/api/v1/gnn/health`
4. Generate embeddings for your schemas
5. Monitor performance and accuracy improvements

The system is now fully prepared for GNN integration while maintaining robust fallback behavior!
