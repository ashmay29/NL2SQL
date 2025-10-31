# Quick Start Guide - GNN Integration
## Get Started in 5 Minutes

---

## 🚀 Immediate Setup (Mock Mode - No External GNN Required)

### **Step 1: Update Environment**

Edit your `.env` file:

```bash
# Change this line
EMBEDDING_PROVIDER=enhanced

# Add these lines (if not present)
EMBEDDING_DIM=512
GNN_ENDPOINT=  # Leave empty for mock mode
USE_GNN_FALLBACK=true
ENABLE_FILE_UPLOAD=true
MAX_UPLOAD_SIZE_MB=100
```

### **Step 2: Install New Dependencies**

```bash
cd backend
pip install openpyxl==3.1.2 pyarrow==14.0.2
```

Or rebuild Docker:
```bash
docker-compose build backend
docker-compose up -d
```

### **Step 3: Verify System is Running**

```bash
# Check health
curl http://localhost:8000/health/detailed

# Check GNN status (should show "mock" mode)
curl http://localhost:8000/api/v1/gnn/health
```

Expected response:
```json
{
  "status": "mock",
  "message": "GNN endpoint not configured, using mock mode"
}
```

---

## 📤 Test Data Ingestion (Choose One)

### **Option A: Upload CSV File**

```bash
# Create a sample CSV
cat > customers.csv << EOF
id,name,email,total_orders
1,John Doe,john@example.com,5
2,Jane Smith,jane@example.com,3
3,Bob Johnson,bob@example.com,8
EOF

# Upload it
curl -X POST "http://localhost:8000/api/v1/data/upload/csv" \
  -F "file=@customers.csv" \
  -F "table_name=customers" \
  -F "generate_embeddings=true"
```

### **Option B: Upload Excel File**

```bash
curl -X POST "http://localhost:8000/api/v1/data/upload/excel" \
  -F "file=@your_file.xlsx" \
  -F "table_name=sales_data" \
  -F "sheet_name=Sheet1" \
  -F "generate_embeddings=true"
```

### **Option C: Use Existing Database Table**

```bash
curl -X POST "http://localhost:8000/api/v1/data/ingest/database-table" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "nl2sql_target",
    "table_name": "customers",
    "sample_size": 1000,
    "generate_embeddings": true
  }'
```

---

## 🧪 Test GNN Features

### **1. Generate Embeddings for Existing Schema**

```bash
curl -X POST "http://localhost:8000/api/v1/gnn/embeddings/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "nl2sql_target",
    "force_regenerate": false
  }'
```

Expected response:
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

### **2. Find Relevant Schema Nodes for a Query**

```bash
curl -X POST "http://localhost:8000/api/v1/gnn/similarity/relevant-nodes" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "show me customers with most orders",
    "database": "nl2sql_target",
    "top_k": 5
  }'
```

Expected response:
```json
{
  "success": true,
  "query": "show me customers with most orders",
  "database": "nl2sql_target",
  "nodes": [
    {
      "node_id": "table:customers",
      "similarity": 0.87,
      "embedding": [...]
    },
    {
      "node_id": "column:customers.name",
      "similarity": 0.82,
      "embedding": [...]
    },
    ...
  ],
  "count": 5
}
```

### **3. Test End-to-End NL2SQL**

```bash
curl -X POST "http://localhost:8000/api/v1/nl2sql" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "show me top 5 customers by total orders",
    "database_id": "nl2sql_target",
    "conversation_id": "test-123",
    "use_cache": true
  }'
```

---

## ✅ Verification Checklist

Run these commands to verify everything works:

```bash
# 1. Check API is running
curl http://localhost:8000/health/detailed

# 2. Check GNN service (should show mock mode)
curl http://localhost:8000/api/v1/gnn/info

# 3. Check supported formats
curl http://localhost:8000/api/v1/data/formats

# 4. Generate embeddings for default database
curl -X POST "http://localhost:8000/api/v1/gnn/embeddings/generate" \
  -H "Content-Type: application/json" \
  -d '{"database": "nl2sql_target"}'

# 5. Test NL2SQL with a simple query
curl -X POST "http://localhost:8000/api/v1/nl2sql" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "show me all customers",
    "database_id": "nl2sql_target"
  }'
```

All commands should return `200 OK` with valid JSON responses.

---

## 🔍 Check Logs

```bash
# View backend logs
docker-compose logs --tail=50 backend

# Look for these success messages:
# - "EnhancedEmbeddingService initialized"
# - "GNNInferenceService initialized in mock mode"
# - "DataIngestionService initialized"
# - "Generated X embeddings"
```

---

## 🎉 Success Indicators

You'll know it's working when:

1. ✅ `/api/v1/gnn/health` returns `"status": "mock"`
2. ✅ `/api/v1/gnn/info` shows `"embedding_dimension": 512`
3. ✅ File uploads return `"success": true` with schema details
4. ✅ Embedding generation completes without errors
5. ✅ NL2SQL queries return SQL with enhanced context
6. ✅ No errors in `docker-compose logs backend`

---

## 🚀 Next Steps

### **For Development/Testing**
You're all set! The system works in mock mode with:
- ✅ Multi-format data ingestion
- ✅ Mock GNN embeddings (deterministic, hash-based)
- ✅ Sentence Transformer fallback
- ✅ Full NL2SQL pipeline

### **For Production (Real GNN)**

When you're ready to integrate a real GNN model:

1. **Deploy your GNN server** with these endpoints:
   - `POST /infer/schema` - Generate schema embeddings
   - `POST /infer/query` - Generate query embeddings
   - `POST /similarity/top_k` - Find similar nodes
   - `GET /health` - Health check

2. **Update `.env`**:
   ```bash
   GNN_ENDPOINT=http://your-gnn-server:8080
   ```

3. **Restart backend**:
   ```bash
   docker-compose restart backend
   ```

4. **Verify GNN connection**:
   ```bash
   curl http://localhost:8000/api/v1/gnn/health
   # Should return: "status": "healthy"
   ```

5. **Regenerate embeddings with real GNN**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/gnn/embeddings/generate" \
     -H "Content-Type: application/json" \
     -d '{"database": "nl2sql_target", "force_regenerate": true}'
   ```

---

## 📚 Documentation

- **Full Integration Guide**: See `GNN_INTEGRATION_GUIDE.md`
- **Implementation Details**: See `GNN_IMPLEMENTATION_COMPLETE.md`
- **API Reference**: Visit `http://localhost:8000/docs` (Swagger UI)

---

## 🐛 Troubleshooting

### **Issue: "Module not found" errors**

```bash
# Reinstall dependencies
pip install -r backend/requirements.txt

# Or rebuild Docker
docker-compose build backend
```

### **Issue: File upload fails**

```bash
# Check file size limit in .env
MAX_UPLOAD_SIZE_MB=100

# Restart backend
docker-compose restart backend
```

### **Issue: Embeddings not generated**

```bash
# Check Redis is running
docker-compose ps redis

# Check Redis connection
redis-cli ping

# View backend logs
docker-compose logs backend
```

---

## 🎯 Quick Test Script

Save this as `test_gnn.sh`:

```bash
#!/bin/bash

echo "Testing GNN Integration..."

# 1. Health check
echo "\n1. Checking API health..."
curl -s http://localhost:8000/health/detailed | jq '.status'

# 2. GNN status
echo "\n2. Checking GNN status..."
curl -s http://localhost:8000/api/v1/gnn/health | jq '.status'

# 3. Generate embeddings
echo "\n3. Generating embeddings..."
curl -s -X POST http://localhost:8000/api/v1/gnn/embeddings/generate \
  -H "Content-Type: application/json" \
  -d '{"database": "nl2sql_target"}' | jq '.embeddings_count'

# 4. Test NL2SQL
echo "\n4. Testing NL2SQL..."
curl -s -X POST http://localhost:8000/api/v1/nl2sql \
  -H "Content-Type: application/json" \
  -d '{"query_text": "show all customers", "database_id": "nl2sql_target"}' \
  | jq '.sql'

echo "\n✅ All tests complete!"
```

Run it:
```bash
chmod +x test_gnn.sh
./test_gnn.sh
```

---

## 🎊 You're Ready!

The system is now fully functional with:
- ✅ Multi-format data ingestion (CSV, Excel, Parquet, JSON, DB)
- ✅ GNN-ready architecture (mock mode active)
- ✅ Sentence Transformer fallback
- ✅ Enhanced NL2SQL with schema context
- ✅ Production-ready for real GNN integration

**Start uploading your data and testing queries!** 🚀
