# CSV Upload & Query Guide

## How to Use CSV Files with NL2SQL

### Step 1: Upload Your CSV File

```bash
POST /api/v1/data/upload/csv
```

**Parameters:**
- `file`: Your CSV file
- `table_name`: Name for the table (e.g., "customers", "sales")
- `delimiter`: CSV delimiter (default: ",")
- `encoding`: File encoding (default: "utf-8")
- `generate_embeddings`: Generate GNN embeddings (default: true)

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/data/upload/csv" \
  -F "file=@your_data.csv" \
  -F "table_name=customers" \
  -F "delimiter=," \
  -F "generate_embeddings=true"
```

**Response:**
```json
{
  "success": true,
  "table_name": "customers",
  "fingerprint": "abc123def456",
  "row_count": 1000,
  "column_count": 5,
  "source_type": "csv",
  "message": "Successfully ingested CSV file: your_data.csv",
  "schema": { ... }
}
```

### Step 2: Query Your Data

After uploading, use **`database_id="uploaded_data"`** in your NL2SQL request:

```bash
POST /api/v1/nl2sql
```

**Request Body:**
```json
{
  "query_text": "Show me all customers from New York",
  "database_id": "uploaded_data",
  "conversation_id": "my-session",
  "use_cache": true
}
```

**Important:** Always use `database_id="uploaded_data"` for CSV/Excel uploads!

### Step 3: Get SQL Results

The API will return:
```json
{
  "original_question": "Show me all customers from New York",
  "resolved_question": "Show me all customers from New York",
  "sql": "SELECT * FROM customers WHERE city = 'New York'",
  "ir": { ... },
  "confidence": 0.95,
  "execution_time": 1.2
}
```

---

## Multiple CSV Files

You can upload multiple CSV files as separate tables:

```bash
# Upload first file
curl -X POST "http://localhost:8000/api/v1/data/upload/csv" \
  -F "file=@customers.csv" \
  -F "table_name=customers"

# Upload second file  
curl -X POST "http://localhost:8000/api/v1/data/upload/csv" \
  -F "file=@orders.csv" \
  -F "table_name=orders"
```

Then query across both tables:
```json
{
  "query_text": "Show me customers who have orders",
  "database_id": "uploaded_data"
}
```

---

## Troubleshooting

### ❌ Error: "Unknown database 'nl2sql_target'"
**Problem:** You're using the default MySQL database but haven't uploaded data.

**Solution:** 
1. Upload your CSV first using `/api/v1/data/upload/csv`
2. Use `database_id="uploaded_data"` in your NL2SQL request

### ❌ Error: "No schema found for database 'xyz'"
**Problem:** The database doesn't exist in cache or MySQL.

**Solution:**
- For CSV/Excel: Upload files first, then use `database_id="uploaded_data"`
- For MySQL: Ensure the database exists and MYSQL_URI is configured in `.env`

### ✅ Working Without MySQL
The backend can run without MySQL! Just:
1. Upload CSV/Excel files
2. Use `database_id="uploaded_data"` 
3. Query your data

---

## Frontend Integration

In your TypeScript/React app:

```typescript
// 1. Upload CSV
const formData = new FormData();
formData.append('file', csvFile);
formData.append('table_name', 'my_table');
formData.append('generate_embeddings', 'true');

const uploadResponse = await fetch('http://localhost:8000/api/v1/data/upload/csv', {
  method: 'POST',
  body: formData
});

// 2. Query the uploaded data
const queryResponse = await fetch('http://localhost:8000/api/v1/nl2sql', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query_text: "Show me all records",
    database_id: "uploaded_data",  // ← IMPORTANT!
    use_cache: true
  })
});

const result = await queryResponse.json();
console.log('Generated SQL:', result.sql);
```

---

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/data/upload/csv` | POST | Upload CSV file |
| `/api/v1/data/upload/excel` | POST | Upload Excel file |
| `/api/v1/nl2sql` | POST | Convert natural language to SQL |
| `/api/v1/data/formats` | GET | Get supported formats |

---

## Schema Caching

- CSV uploads are cached for **24 hours** (86400 seconds)
- Schema key: `schema:uploaded_data`
- Multiple uploads to same table overwrite previous schema
- Embeddings are regenerated on each upload

---

## Best Practices

1. ✅ **Always** use `database_id="uploaded_data"` after CSV upload
2. ✅ Use descriptive table names (e.g., "sales_2024" not "table1")
3. ✅ Enable embedding generation for better schema linking
4. ✅ Upload multiple CSVs as separate tables for relational queries
5. ❌ Don't use `database_id="nl2sql_target"` unless you have MySQL configured

