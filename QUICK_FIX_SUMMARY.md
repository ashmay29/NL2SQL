# Quick Fix Summary - CSV Upload & Query

## Problem
Frontend was sending `database_id: "nl2sql_target"` which tried to access MySQL database that doesn't exist, causing 400 errors even after uploading CSV files.

## Root Causes
1. ❌ Frontend hardcoded `database_id: 'nl2sql_target'`
2. ❌ CSV upload didn't cache schema for pipeline to find
3. ❌ No real CSV upload logic - just UI mockup
4. ❌ Pipeline crashed when MySQL unavailable

## Solutions Implemented

### Backend Changes

#### 1. **data_ingestion.py** - Cache Uploaded Schemas
```python
# After CSV upload, cache schema with key "schema:uploaded_data"
schema_service.cache_schema(db_schema, ttl=86400)  # 24 hours
```

#### 2. **pipeline_orchestrator.py** - Graceful Fallback
```python
# Check cache first, only try MySQL if available
ctx.schema = self.schema_service.get_cached_schema(ctx.database_id)

if not ctx.schema and self.schema_service.inspector:
    # Try MySQL extraction
    
elif not ctx.schema:
    # Show helpful error message
    raise RuntimeError(
        f"No schema found for database '{ctx.database_id}'. "
        "Please upload a CSV/Excel file first..."
    )
```

#### 3. **nl2sql.py** - Better Default
```python
database_id = req.database_id or "uploaded_data"  # Changed from nl2sql_target
```

### Frontend Changes

#### 1. **NLSQLPlayground.tsx** - Real CSV Upload
- ✅ Added `useUploadCSV()` hook
- ✅ Added `tableName` input field
- ✅ Added "Upload to Backend" button with loading state
- ✅ Changed default `databaseId` from `'nl2sql_target'` to `'uploaded_data'`
- ✅ Dynamic state variable instead of hardcoded value
- ✅ Success/error notifications

#### 2. **api/hooks.ts** - Upload Hook
```typescript
export const useUploadCSV = () => {
  return useMutation({
    mutationFn: async ({ file, tableName }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('table_name', tableName);
      formData.append('generate_embeddings', 'true');
      
      return await apiClient.post('/api/v1/data/upload/csv', formData);
    },
  });
};
```

#### 3. **Other Files**
- `api/hooks.ts`: Changed `useSchema` default from `'nl2sql_target'` → `'uploaded_data'`
- `SchemaExplorer.tsx`: Changed refresh to use `'uploaded_data'`

## How It Works Now

### Step 1: Upload CSV
1. User selects CSV file
2. Frontend shows file picker
3. User enters table name (e.g., "customers")
4. Clicks "Upload to Backend"
5. Backend ingests CSV, extracts schema, generates embeddings
6. Schema cached with key `schema:uploaded_data` for 24 hours

### Step 2: Query
1. User enters natural language query
2. Frontend sends request with `database_id: 'uploaded_data'` (or omitted - defaults to this)
3. Backend finds cached schema from CSV upload
4. Pipeline generates SQL using uploaded data schema
5. Returns SQL to frontend

## User Flow (Updated)

```
┌─────────────────┐
│ 1. Upload CSV   │
│    ↓            │
│ 2. Enter table  │
│    name         │
│    ↓            │
│ 3. Click Upload │
│    ↓            │
│ 4. Backend      │
│    caches       │
│    schema       │
└─────────────────┘
        ↓
┌─────────────────┐
│ 5. Enter query  │
│    ↓            │
│ 6. Generate SQL │
│    (auto uses   │
│    uploaded_    │
│    data)        │
└─────────────────┘
```

## Error Messages (Before → After)

### Before ❌
```
(pymysql.err.OperationalError) (1049, "Unknown database 'nl2sql_target'")
[SQL: SHOW FULL TABLES FROM `nl2sql_target`]
```

### After ✅
```
No schema found for database 'nl2sql_target'. 
Please upload a CSV/Excel file first using /api/v1/data/upload/csv endpoint. 
After upload, use database_id='uploaded_data' in your NL2SQL request.
```

## Testing Checklist

- [ ] Upload CSV file via frontend
- [ ] Verify table name input appears
- [ ] Click "Upload to Backend" button
- [ ] See success notification with row/column counts
- [ ] Enter a natural language query
- [ ] Click "Generate SQL"
- [ ] Verify SQL is generated (no 400 error)
- [ ] Check backend logs show schema loaded from cache

## Key Files Changed

### Backend
- `backend/app/api/v1/data_ingestion.py` (cache schema after upload)
- `backend/app/services/pipeline_orchestrator.py` (graceful fallback)
- `backend/app/api/v1/nl2sql.py` (default database_id)

### Frontend  
- `frontend/src/pages/NLSQLPlayground.tsx` (real upload + dynamic DB ID)
- `frontend/src/api/hooks.ts` (useUploadCSV hook + default change)
- `frontend/src/pages/SchemaExplorer.tsx` (default change)

## What's Fixed
✅ CSV upload now actually uploads to backend
✅ Schema is cached for NL2SQL pipeline to find
✅ Frontend uses correct `database_id: 'uploaded_data'`
✅ No more MySQL connection errors for CSV uploads
✅ Graceful error messages when schema not found
✅ Upload success feedback with file stats
✅ Table name input for better organization

