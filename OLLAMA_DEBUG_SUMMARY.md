# Ollama Integration Debug Summary

## Issues Found and Fixed

### 1. ✅ FIXED: Syntax Error in `nl2sql.py`
**Problem**: Function `build_compact_schema_text()` was placed BEFORE the module docstring (lines 1-17), causing Python syntax error.

**Error**:
```
File "/app/app/api/v1/nl2sql.py", line 5
    """Build a compact schema string: only table and column names to minimize context size."""
       ^^^^^
SyntaxError: invalid syntax
```

**Fix**: Moved function definition to correct location after imports (line 25).

**Impact**: Backend container was crashing on startup, preventing all API requests.

---

### 2. ⚠️ CRITICAL: Ollama Running on CPU Only
**Problem**: Ollama is not using GPU acceleration (`size_vram: 0`).

**Evidence**:
- Simple 10-token generation takes **57 seconds**
  - Model load: 13s
  - Prompt eval (11 tokens): 11.7s  
  - Generation (10 tokens): 27.4s
- `/api/ps` shows `"size_vram": 0`

**Root Cause**: No GPU available or Ollama not configured to use GPU.

**Impact**: All LLM requests timeout or take 1-2 minutes.

---

### 3. ⚠️ Model Size vs System Resources
**Problem**: `mistral:latest` (7.2B params, 4.4GB) requires more memory than available.

**Error**:
```
{"error":"model requires more system memory than is currently available unable to load full model on GPU"}
```

**Current Working Model**: `gemma3:4b` (4.3B params, 3.3GB) - works but very slow on CPU.

---

## Current Configuration

### Docker Compose Settings (Applied)
```yaml
environment:
  - OLLAMA_MODEL=gemma3:4b          # Smaller model that fits in memory
  - OLLAMA_NUM_CTX=2048             # Reduced context window
  - OLLAMA_NUM_PREDICT=32           # Limit output tokens
  - COMPACT_SCHEMA=true             # Use minimal schema format
  - MAX_COLUMNS_IN_PROMPT=5         # Limit columns per table
```

### Code Changes
1. **`backend/app/api/v1/nl2sql.py`**:
   - Fixed syntax error (function placement)
   - Updated to use `settings.MAX_COLUMNS_IN_PROMPT`

2. **`backend/app/services/llm_service.py`**:
   - Already configured with timeout=120s
   - Uses `/api/chat` with `format: "json"` for structured output
   - Respects `OLLAMA_NUM_CTX` and `OLLAMA_NUM_PREDICT` settings

---

## Solutions & Recommendations

### Immediate (Current State)
✅ Backend is now running successfully
✅ Diagnostics endpoints work
⚠️ LLM generation is VERY slow (1-2 minutes per request)

### Short-term Options

#### Option A: Use Smaller Model (Recommended for CPU)
```bash
# Pull tinyllama (1.1B params, ~600MB)
curl -X POST http://localhost:11434/api/pull -d '{"name": "tinyllama"}'

# Update docker-compose.yml
OLLAMA_MODEL=tinyllama
```

#### Option B: Use External API (Fast, but requires API key)
```yaml
environment:
  - LLM_PROVIDER=gemini
  - GEMINI_API_KEY=your_key_here
  - GEMINI_MODEL=gemini-2.5-flash
```

### Long-term Solution: Enable GPU
**For NVIDIA GPU**:
1. Install NVIDIA drivers + CUDA toolkit
2. Install nvidia-docker2
3. Restart Ollama with GPU support
4. Verify with `nvidia-smi`

**Expected improvement**: 50-100x faster (seconds instead of minutes)

---

## Testing Commands

### Check LLM Health
```bash
curl http://localhost:8000/api/v1/diagnostics/llm
```

### Test Simple Generation
```bash
curl -X POST http://localhost:8000/api/v1/diagnostics/test-llm
```

### Test NL→IR (with schema)
```bash
curl -X POST http://localhost:8000/api/v1/nl2ir \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "show top 3 customers",
    "database_id": "nl2sql_target"
  }'
```

### Check Ollama Model Status
```bash
curl http://localhost:11434/api/ps
```

---

## Performance Expectations

### Current Setup (CPU-only, gemma3:4b)
- Simple query: 1-2 minutes
- Complex query with schema: 2-3 minutes
- **Not suitable for production**

### With tinyllama (CPU)
- Simple query: 10-30 seconds
- Complex query: 30-60 seconds
- **Acceptable for development/testing**

### With GPU (any model)
- Simple query: 1-5 seconds
- Complex query: 5-15 seconds
- **Production ready**

---

## Test Results

### ✅ Fixed: Syntax Error
Backend now starts successfully.

### ✅ Tinyllama Performance
- **Simple prompt (10 tokens)**: 9.6 seconds (vs 57s for gemma3:4b)
- **6x faster** than gemma3:4b
- **Still too slow** for schema-based prompts (>2 minutes, times out)

### ❌ Root Cause: CPU-Only Inference
Even with the smallest model, CPU inference is too slow for production use.

## Recommended Solutions

### Option 1: Use Gemini API (RECOMMENDED for immediate results)
```yaml
# In docker-compose.yml
environment:
  - LLM_PROVIDER=gemini
  - GEMINI_API_KEY=your_api_key_here
  - GEMINI_MODEL=gemini-2.5-flash
```

**Pros**: 
- Instant responses (1-3 seconds)
- No local resources needed
- Production quality

**Cons**: 
- Requires API key
- Costs money (but very cheap)
- External dependency

### Option 2: Enable GPU (Long-term solution)
1. Install NVIDIA drivers + CUDA
2. Configure Ollama to use GPU
3. Restart Ollama service
4. Verify with `nvidia-smi`

**Expected**: 50-100x speedup

### Option 3: Mock IR for Development
Create a simple rule-based IR generator for testing the pipeline without LLM.

## Next Steps

1. **Get Gemini API key** from https://aistudio.google.com/app/apikey
2. **Update docker-compose.yml** with Gemini settings
3. **Restart backend**: `docker-compose restart backend`
4. **Test**: Should get responses in 1-3 seconds

---

## Files Modified

1. `backend/app/api/v1/nl2sql.py` - Fixed syntax error, updated schema function call
2. `docker-compose.yml` - Optimized Ollama settings for CPU performance
