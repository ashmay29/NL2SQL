# ✅ GNN + LLM Integration - Complete

## 🎯 Summary

Your GNN model is now **fully integrated** with the LLM pipeline, matching your training code's workflow:

```
User Query → GNN (score schema nodes) → Top-K Pruned Schema → LLM Prompt → SQL
```

---

## 🔄 Complete Data Flow

### **Your Training Code (utils.py):**

```python
def text_to_sql(question, db_id, gnn_model, embed_model, sql_generator, all_schema_graphs, device):
    # 1. Get question embedding
    q_embedding = get_text_embedding(question, embed_model).to(device)
    
    # 2. Run GNN to score schema nodes
    scores = gnn_model(x, edge_index, question_embedding, batch_index)
    
    # 3. Create pruned prompt with top-K nodes
    prompt = create_llm_prompt(question, graph, scores, top_k=15)
    
    # 4. Generate SQL with LLM
    response = sql_generator(prompt, max_new_tokens=150, ...)
    
    return sql_query
```

### **Backend Implementation (NOW MATCHES):**

```python
# pipeline_orchestrator.py - generate_ir()

async def generate_ir(self, ctx: PipelineContext):
    # 1. Get GNN ranker service
    if settings.USE_LOCAL_GNN:
        gnn_service = get_gnn_ranker_service()
        
        # 2. Score schema nodes using GNN (with question embedding)
        gnn_top_nodes = await gnn_service.score_schema_nodes(
            query=ctx.resolved_query,
            backend_schema=ctx.schema,
            top_k=15  # Top 15 relevant nodes
        )
        # ✅ This calls your trained GNN model!
    
    # 3. Build pruned schema (only top-K nodes)
    schema_text = build_compact_schema_text(
        ctx.schema,
        gnn_top_nodes=gnn_top_nodes  # ✅ Pruned schema
    )
    
    # 4. Build prompt with pruned schema
    prompt = build_ir_prompt(schema_text, ctx.resolved_query, rag_examples, context)
    
    # 5. Generate IR/SQL with LLM
    ir_json = self.llm_service.generate_json(prompt)
    
    return ir_json
```

---

## 📊 What Changed

### **1. Updated: `prompt_templates.py`** ✅

**New Function:**
```python
def _build_gnn_pruned_schema(schema: Dict[str, Any], gnn_nodes: List[Dict[str, Any]]) -> str:
    """
    Build pruned schema based on GNN top-K ranked nodes.
    Matches your training code's create_llm_prompt() logic.
    """
    # Extract relevant tables and columns from GNN results
    pruned_tables = set()
    pruned_cols = {}
    
    for node in gnn_nodes:
        node_id = node.get("node_id", "")
        # "column:Customers.customer_id" → add to pruned_cols
        # "table:Products" → add to pruned_tables
    
    # Build CREATE TABLE statements (like your training code)
    schema_lines = []
    for table in pruned_tables:
        cols_str = ", ".join([f"{col} {col_type.upper()}" for col, col_type in pruned_cols[table]])
        schema_lines.append(f"CREATE TABLE {table} ({cols_str});")
    
    return "\n".join(schema_lines)
```

**Updated Function:**
```python
def build_compact_schema_text(
    schema: Dict[str, Any],
    max_columns_per_table: int = None,
    gnn_top_nodes: Optional[List[Dict[str, Any]]] = None  # ✅ NEW PARAMETER
) -> str:
    # If GNN provided top-K nodes, build pruned schema
    if gnn_top_nodes:
        return _build_gnn_pruned_schema(schema, gnn_top_nodes)
    
    # Otherwise, fall back to compact schema (all tables)
    ...
```

### **2. Updated: `pipeline_orchestrator.py`** ✅

**Modified `generate_ir()` method:**

```python
async def generate_ir(self, ctx: PipelineContext):
    # ✅ NEW: Get GNN ranker service
    gnn_top_nodes = None
    try:
        from app.core.dependencies import get_gnn_ranker_service
        from app.core.config import settings
        
        if settings.USE_LOCAL_GNN:
            gnn_service = get_gnn_ranker_service()
            
            # ✅ Score schema nodes using GNN
            gnn_top_nodes = await gnn_service.score_schema_nodes(
                query=ctx.resolved_query,
                backend_schema=ctx.schema,
                top_k=15
            )
            logger.info(f"GNN scored {len(gnn_top_nodes)} relevant schema nodes")
    except Exception as e:
        logger.warning(f"GNN schema pruning failed, using full schema: {e}")
        gnn_top_nodes = None
    
    # ✅ Build schema with GNN pruning
    schema_text = build_compact_schema_text(
        ctx.schema,
        max_columns_per_table=settings.MAX_COLUMNS_IN_PROMPT,
        gnn_top_nodes=gnn_top_nodes  # ✅ Pass GNN results
    )
    
    # ... rest of prompt building and LLM generation
```

### **3. Updated: `nl2sql.py` API Endpoint** ✅

**Modified `nl2ir()` endpoint:**

```python
@router.post("/nl2ir", response_model=NL2IRResponse)
async def nl2ir(req: NL2IRRequest, ...):
    # Get schema
    schema = schema_service.get_cached_schema(...)
    
    # ✅ NEW: Use GNN to prune schema
    gnn_top_nodes = None
    try:
        if settings.USE_LOCAL_GNN:
            gnn_service = get_gnn_ranker_service()
            gnn_top_nodes = await gnn_service.score_schema_nodes(
                query=resolved_query,
                backend_schema=schema,
                top_k=15
            )
    except Exception as e:
        logger.warning(f"GNN failed: {e}")
    
    # ✅ Build pruned schema
    schema_text = build_compact_schema_text(
        schema,
        gnn_top_nodes=gnn_top_nodes
    )
    
    # ... rest of IR generation
```

---

## 🧪 How It Works - Step by Step

### **Example Query:** "Show customers who ordered product X"

#### **Step 1: GNN Scoring**

```python
# gnn_ranker_service.py
gnn_top_nodes = await gnn_service.score_schema_nodes(
    query="Show customers who ordered product X",
    backend_schema={...},
    top_k=15
)

# Returns:
[
    {"node_id": "table:Customers", "score": 0.95, "metadata": {...}},
    {"node_id": "column:Customers.customer_id", "score": 0.93, "metadata": {"type": "int"}},
    {"node_id": "column:Customers.first_name", "score": 0.88, "metadata": {"type": "varchar"}},
    {"node_id": "column:Customers.last_name", "score": 0.87, "metadata": {"type": "varchar"}},
    {"node_id": "table:Orders", "score": 0.92, "metadata": {...}},
    {"node_id": "column:Orders.customer_id", "score": 0.91, "metadata": {"type": "int"}},
    {"node_id": "column:Orders.product_id", "score": 0.90, "metadata": {"type": "int"}},
    {"node_id": "table:Products", "score": 0.89, "metadata": {...}},
    {"node_id": "column:Products.product_id", "score": 0.88, "metadata": {"type": "int"}},
    {"node_id": "column:Products.name", "score": 0.87, "metadata": {"type": "varchar"}},
    ...
]
```

#### **Step 2: Pruned Schema Generation**

```python
# prompt_templates.py - _build_gnn_pruned_schema()
schema_text = _build_gnn_pruned_schema(schema, gnn_top_nodes)

# Output:
"""
-- Database: ecommerce
-- GNN-Pruned Schema (Top-K Relevant Nodes)

CREATE TABLE Customers (customer_id INT, first_name VARCHAR, last_name VARCHAR);
CREATE TABLE Orders (customer_id INT, product_id INT);
CREATE TABLE Products (product_id INT, name VARCHAR);
"""
```

**Notice:** Only the most relevant tables and columns are included! ✅

#### **Step 3: LLM Prompt Construction**

```python
# prompt_templates.py - build_ir_prompt()
prompt = f"""
You are an expert NL2SQL assistant...

Schema:
-- Database: ecommerce
-- GNN-Pruned Schema (Top-K Relevant Nodes)

CREATE TABLE Customers (customer_id INT, first_name VARCHAR, last_name VARCHAR);
CREATE TABLE Orders (customer_id INT, product_id INT);
CREATE TABLE Products (product_id INT, name VARCHAR);

User Question:
Show customers who ordered product X

JSON Structure:
...
"""
```

**Key Benefit:** The LLM only sees relevant schema, avoiding confusion from irrelevant tables! ✅

#### **Step 4: LLM Generation**

```python
# llm_service.py
ir_json = llm.generate_json(prompt)

# Returns:
{
    "select": [
        {"type": "column", "value": "Customers.first_name"},
        {"type": "column", "value": "Customers.last_name"}
    ],
    "from_table": "Customers",
    "joins": [
        {
            "type": "INNER",
            "table": "Orders",
            "on": [{"left": {"type": "column", "value": "Customers.customer_id"}, ...}]
        },
        {
            "type": "INNER",
            "table": "Products",
            "on": [{"left": {"type": "column", "value": "Orders.product_id"}, ...}]
        }
    ],
    "where": [{"left": {"type": "column", "value": "Products.name"}, "operator": "=", "right": {"type": "literal", "value": "X"}}]
}
```

---

## 🎯 Key Differences vs. Before

### **BEFORE (Without GNN Integration):**

```python
# All tables and columns shown (overwhelming for LLM)
schema_text = """
Database: ecommerce
- Customers: customer_id, first_name, last_name, email, phone, address, city, state, zip
- Products: product_id, name, description, price, category, stock, supplier_id, ...
- Orders: order_id, customer_id, product_id, quantity, date, status, ...
- Suppliers: supplier_id, name, contact, ...
- Categories: category_id, name, ...
- ... (20+ more tables)
"""

# Problem: LLM gets confused by irrelevant schema
```

### **AFTER (With GNN Integration):** ✅

```python
# Only GNN top-K relevant nodes (focused for LLM)
schema_text = """
-- GNN-Pruned Schema (Top-K Relevant Nodes)

CREATE TABLE Customers (customer_id INT, first_name VARCHAR, last_name VARCHAR);
CREATE TABLE Orders (customer_id INT, product_id INT);
CREATE TABLE Products (product_id INT, name VARCHAR);
"""

# Benefit: LLM focuses on relevant schema only!
```

---

## 🚀 Usage

### **Automatic (Default):**

When `USE_LOCAL_GNN=true` in `.env`, the pipeline automatically uses GNN:

```bash
# .env
USE_LOCAL_GNN=true
GNN_MODEL_PATH=/app/models/gnn/best_model.pt
```

**Request:**
```bash
POST /api/v1/nl2sql
{
    "query_text": "Show top 5 customers by total orders",
    "database_id": "ecommerce",
    "conversation_id": "user123"
}
```

**What Happens:**
1. ✅ GNN scores all schema nodes
2. ✅ Top 15 nodes selected
3. ✅ Pruned schema built
4. ✅ LLM generates IR/SQL with focused schema

### **Fallback (If GNN Fails):**

If GNN fails (model not found, error, etc.), the system falls back to full schema:

```python
try:
    gnn_top_nodes = await gnn_service.score_schema_nodes(...)
except Exception as e:
    logger.warning(f"GNN failed, using full schema: {e}")
    gnn_top_nodes = None  # Fallback to compact schema
```

---

## 📈 Benefits

### **1. Improved Accuracy** ✅
- LLM sees only relevant schema
- Reduces hallucination (using wrong tables/columns)
- Matches your training methodology

### **2. Reduced Context Size** ✅
- Pruned schema is much smaller
- Faster LLM inference
- Lower token costs

### **3. Better Complex Schema Handling** ✅
- Large databases (100+ tables) now manageable
- GNN intelligently selects relevant parts

### **4. Exact Match to Training** ✅
- Same workflow: Query → GNN → Pruned Schema → LLM
- Your trained model is used as designed

---

## 🧪 Testing

### **Test 1: Verify GNN is Called**

Check backend logs for:

```
INFO: GNN Ranker using device: cuda
INFO: Loading GNN weights from /app/models/gnn/best_model.pt
INFO: GNN weights loaded successfully
INFO: GNN scored 15 relevant schema nodes for query
```

### **Test 2: Check Pruned Schema in Logs**

Enable debug logging:

```python
# .env
LOG_LEVEL=DEBUG
```

Look for:

```
DEBUG: Schema text:
-- Database: ecommerce
-- GNN-Pruned Schema (Top-K Relevant Nodes)

CREATE TABLE Customers (...);
CREATE TABLE Orders (...);
...
```

### **Test 3: Compare Prompt Before/After**

**Without GNN:** Prompt contains all tables

**With GNN:** Prompt contains only top-K relevant tables ✅

---

## 🔧 Configuration

### **Enable/Disable GNN:**

```bash
# .env

# Enable GNN (default)
USE_LOCAL_GNN=true

# Disable GNN (use full schema)
USE_LOCAL_GNN=false
```

### **Adjust Top-K:**

```python
# pipeline_orchestrator.py
gnn_top_nodes = await gnn_service.score_schema_nodes(
    query=ctx.resolved_query,
    backend_schema=ctx.schema,
    top_k=15  # ← Change this (default: 15)
)
```

**Recommendations:**
- **Simple queries:** top_k=10
- **Complex queries:** top_k=20
- **Large schemas (100+ tables):** top_k=25

---

## 📝 Comparison Table

| Component | Your Training Code | Backend Implementation | Match? |
|-----------|-------------------|------------------------|--------|
| **GNN Architecture** | 3-layer GAT, 4 heads | 3-layer GAT, 4 heads | ✅ |
| **Question Embedding** | SentenceTransformer | SentenceTransformer | ✅ |
| **Schema Format** | Spider format | Backend → Spider (converted) | ✅ |
| **GNN Scoring** | `gnn_model(x, edge_index, q_emb, batch)` | `gnn_service.score_schema_nodes()` | ✅ |
| **Top-K Selection** | `torch.topk(scores, top_k=15)` | `top_k=15` in service | ✅ |
| **Schema Pruning** | `create_llm_prompt(graph, scores, top_k)` | `_build_gnn_pruned_schema()` | ✅ |
| **Prompt Format** | CREATE TABLE statements | CREATE TABLE statements | ✅ |
| **LLM Generation** | CodeLlama pipeline | Gemini/Ollama API | ⚠️ Different |

**Note:** Only difference is the LLM itself (you used CodeLlama, backend uses Gemini/Ollama). The GNN→Schema→Prompt flow is identical! ✅

---

## 🎉 Final Status

**✅ GNN Model:** Integrated  
**✅ Schema Conversion:** Backend → Spider  
**✅ Node Scoring:** GAT-based GNN  
**✅ Schema Pruning:** Top-K selection  
**✅ Prompt Building:** CREATE TABLE format  
**✅ LLM Integration:** Pruned schema in prompt  

**Your hybrid GNN+LLM architecture is now fully operational in the backend!** 🚀

---

## 🐛 Troubleshooting

### **GNN not being called:**

Check `.env`:
```bash
USE_LOCAL_GNN=true  # Must be true
```

Check logs:
```bash
docker-compose logs -f backend | grep "GNN"
```

### **GNN fails silently:**

Check model file exists:
```bash
ls -lh backend/models/gnn/best_model.pt
```

Check logs for error:
```bash
docker-compose logs backend | grep "ERROR"
```

### **Full schema still showing:**

Check if `gnn_top_nodes` is None in logs:
```
WARNING: GNN schema pruning failed, using full schema: ...
```

Fix the error message shown.

---

## 📚 Related Files

- **`backend/app/services/gnn_ranker_service.py`** - GNN model integration
- **`backend/app/services/schema_converter.py`** - Backend → Spider conversion
- **`backend/app/services/prompt_templates.py`** - Pruned schema generation
- **`backend/app/services/pipeline_orchestrator.py`** - Pipeline integration
- **`backend/app/api/v1/nl2sql.py`** - API endpoint integration

---

## 🔄 What Happens on Each Request

```
1. User sends query: "Show customers who ordered product X"
   ↓
2. Pipeline gets schema from database
   ↓
3. GNN scores all schema nodes (tables + columns)
   Score: Customers.customer_id=0.95, Orders.product_id=0.92, ...
   ↓
4. Top-15 nodes selected
   ↓
5. Pruned schema built (only relevant tables/columns)
   CREATE TABLE Customers (customer_id INT, ...);
   CREATE TABLE Orders (customer_id INT, product_id INT);
   CREATE TABLE Products (product_id INT, name VARCHAR);
   ↓
6. Prompt built with pruned schema
   ↓
7. LLM generates IR/SQL
   ↓
8. SQL returned to user
```

**Every step now matches your training code workflow!** ✅
