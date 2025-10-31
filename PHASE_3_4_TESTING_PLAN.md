# Phase 3 & 4 Testing Plan
## End-to-End Testing for NL2SQL with RAG & Advanced Features

---

## Test Environment Setup

### Prerequisites
- ✅ Backend running with Gemini API
- ✅ All services initialized (Qdrant, Redis, MySQL, PostgreSQL)
- ✅ Sample data loaded in `nl2sql_target` database
- ✅ Frontend UI ready for testing

### Configuration
```yaml
LLM_PROVIDER: gemini
GEMINI_API_KEY: [configured]
EMBEDDING_PROVIDER: mock
COMPACT_SCHEMA: true
MAX_COLUMNS_IN_PROMPT: 8
```

---

## Phase 3: RAG Feedback System Tests

### Test 3.1: Submit Feedback
**Endpoint**: `POST /api/v1/feedback`

**Test Case 1**: Submit correction feedback
```json
{
  "query_text": "show top 5 customers",
  "generated_sql": "SELECT * FROM customers LIMIT 5",
  "corrected_sql": "SELECT * FROM customers ORDER BY total_spent DESC LIMIT 5",
  "schema_fingerprint": "abc123",
  "tables_used": ["customers"],
  "metadata": {}
}
```

**Expected**:
- Status 200
- Returns feedback_id
- Feedback stored in Qdrant

**Test Case 2**: Submit success confirmation
```json
{
  "query_text": "count all orders",
  "generated_sql": "SELECT COUNT(*) FROM orders",
  "corrected_sql": "SELECT COUNT(*) FROM orders",
  "schema_fingerprint": "abc123",
  "tables_used": ["orders"]
}
```

**Expected**:
- Status 200
- Feedback marked as "success" type

---

### Test 3.2: Retrieve Similar Queries
**Endpoint**: `POST /api/v1/feedback/similar`

**Test Case 1**: Find similar queries
```json
{
  "query": "show top 10 customers by revenue",
  "schema_fingerprint": "abc123",
  "top_k": 5
}
```

**Expected**:
- Returns list of similar past queries
- Each result has score, query_text, corrected_sql
- Results sorted by similarity score

**Test Case 2**: No similar queries
```json
{
  "query": "completely unique query about xyz",
  "schema_fingerprint": "abc123",
  "top_k": 5
}
```

**Expected**:
- Returns empty list or low-score results

---

### Test 3.3: RAG Integration in NL2IR
**Endpoint**: `POST /api/v1/nl2ir`

**Setup**: Submit 2-3 feedback entries first

**Test Case**: Query with RAG examples
```json
{
  "query_text": "top 3 customers by spending",
  "database_id": "nl2sql_target"
}
```

**Expected**:
- IR generated successfully
- Check logs for "Found X similar queries"
- IR should benefit from RAG examples (correct ORDER BY, LIMIT)

---

## Phase 4: Advanced Features Tests

### Test 4.1: Context Service (Multi-turn Conversation)

**Test Case 1**: Reference resolution
```
Turn 1:
POST /api/v1/nl2sql
{
  "query_text": "show all customers",
  "conversation_id": "test-conv-1"
}

Turn 2:
POST /api/v1/nl2sql
{
  "query_text": "show their orders",
  "conversation_id": "test-conv-1"
}
```

**Expected**:
- Turn 1: Returns customers query
- Turn 2: Resolves "their" to customers, generates JOIN query
- Check logs for "Resolved reference"

**Test Case 2**: Context in prompt
```
Turn 1: "count orders"
Turn 2: "what about products?"
Turn 3: "show me the same for categories"
```

**Expected**:
- Each turn builds on previous context
- Prompt includes "Previous conversation:" section

---

### Test 4.2: Complexity Analysis

**Test Case 1**: Simple query
```json
{
  "query_text": "select all customers"
}
```

**Expected**:
- complexity_level: "simple"
- score < 20
- No warnings

**Test Case 2**: Complex query
```json
{
  "query_text": "show customers with their total orders, average order value, grouped by country, having more than 10 orders"
}
```

**Expected**:
- complexity_level: "complex" or "very_complex"
- score > 40
- Warnings about grouping, aggregation
- Optimization suggestions in response

---

### Test 4.3: SQL Corrector

**Test Case 1**: Missing ORDER BY with LIMIT
```json
{
  "query_text": "top 5 products"
}
```

**Expected**:
- Generates SQL with LIMIT
- Corrector detects missing ORDER BY
- explanations includes: "LIMIT without ORDER BY may produce non-deterministic results"

**Test Case 2**: Ambiguous columns in JOIN
```json
{
  "query_text": "show customers and their orders with name"
}
```

**Expected**:
- Corrector detects potential ambiguity
- suggested_fixes includes disambiguation advice

---

### Test 4.4: Clarification Service

**Test Case 1**: Low confidence query
```json
{
  "query_text": "show me the users"
}
```

**Expected** (if "users" is ambiguous):
- confidence < 0.7
- explanations contains clarification questions
- sql may be empty, asking for clarification first

**Test Case 2**: Ambiguous aggregation
```json
{
  "query_text": "total sales"
}
```

**Expected**:
- Clarification: "Did you mean SUM (total value) or COUNT (total number)?"
- Options provided

---

### Test 4.5: Error Explainer

**Setup**: Create endpoint to test error explanation

**Test Case 1**: Unknown column error
```
Error: "Unknown column 'xyz' in 'field list'"
```

**Expected**:
- error_type: "unknown_column"
- user_friendly_message: "The column 'xyz' doesn't exist..."
- suggestions include spelling check, alternatives

**Test Case 2**: Syntax error
```
Error: "You have an error in your SQL syntax..."
```

**Expected**:
- error_type: "syntax_error"
- user_friendly_message explains it's a generator bug
- suggestions to rephrase or report

---

## Integration Tests

### Test I.1: Full Pipeline with All Features
```
Step 1: Submit feedback for "top customers"
Step 2: Query "show top 5 customers by revenue"
Step 3: Verify:
  - RAG examples used
  - Complexity analyzed
  - SQL corrected if needed
  - Context saved
Step 4: Follow-up query "what about their orders?"
Step 5: Verify:
  - Context resolved
  - JOIN generated correctly
```

---

### Test I.2: Multi-User Conversations
```
User A (conv-A):
  - "show customers"
  - "their orders"

User B (conv-B):
  - "show products"
  - "their categories"

Verify:
  - Contexts don't mix
  - Each conversation maintains separate history
```

---

### Test I.3: RAG Learning Loop
```
1. Query: "top products" -> generates wrong SQL
2. Submit correction feedback
3. Query again: "best products" -> should use corrected SQL from RAG
4. Verify improvement
```

---

## Performance Tests

### Test P.1: Response Time with Gemini
**Target**: < 5 seconds for simple queries

```
Query: "count all customers"
Expected: < 3 seconds
```

### Test P.2: RAG Search Performance
**Target**: < 500ms for similarity search

```
Search for similar queries with 1000+ feedback entries
Expected: < 500ms
```

### Test P.3: Context Retrieval
**Target**: < 100ms

```
Get conversation history (5 turns)
Expected: < 100ms
```

---

## UI Testing Scenarios

### Scenario 1: First-Time User
1. Open UI
2. See schema browser
3. Enter simple query: "show all customers"
4. View results with:
   - Generated SQL
   - Confidence score
   - Complexity indicator
   - Execution time

### Scenario 2: Power User with Feedback
1. Generate query
2. See SQL is wrong
3. Click "Provide Feedback"
4. Edit SQL
5. Submit correction
6. Try similar query
7. Verify improved result

### Scenario 3: Multi-Turn Conversation
1. Query: "show customers"
2. Query: "their orders"
3. Query: "total spent by each"
4. View conversation history panel
5. Clear conversation
6. Start fresh

### Scenario 4: Clarification Flow
1. Enter ambiguous query: "show users"
2. See clarification questions
3. Select option
4. Get refined SQL

### Scenario 5: Complexity Warnings
1. Enter complex query with multiple JOINs
2. See complexity badge (orange/red)
3. View warnings and optimization tips
4. Optionally simplify query

---

## Test Data Requirements

### Sample Database: `nl2sql_target`

**Tables**:
- `customers` (id, name, email, country, total_spent)
- `orders` (id, customer_id, order_date, total_amount, status)
- `products` (id, name, category, price, stock)
- `order_items` (id, order_id, product_id, quantity, price)
- `categories` (id, name, description)

**Sample Data**:
- 100+ customers
- 500+ orders
- 50+ products
- 1000+ order_items

---

## Success Criteria

### Phase 3 (RAG)
- ✅ Feedback submission works
- ✅ Similar query retrieval accurate (>70% relevance)
- ✅ RAG examples improve IR generation
- ✅ Feedback loop demonstrates learning

### Phase 4 (Advanced Features)
- ✅ Context resolution works across turns
- ✅ Complexity analysis accurate
- ✅ SQL corrector catches common errors
- ✅ Clarification triggers appropriately
- ✅ Error explanations user-friendly

### Performance
- ✅ Response time < 5s (Gemini)
- ✅ RAG search < 500ms
- ✅ No memory leaks over 100+ queries

### UI/UX
- ✅ All features accessible in UI
- ✅ Feedback flow intuitive
- ✅ Conversation history visible
- ✅ Complexity/warnings clear
- ✅ Error messages helpful

---

## Test Execution Checklist

- [ ] Backend built and running
- [ ] All services healthy
- [ ] Sample data loaded
- [ ] Gemini API working
- [ ] Qdrant collections initialized
- [ ] Run Phase 3 tests
- [ ] Run Phase 4 tests
- [ ] Run integration tests
- [ ] Run performance tests
- [ ] Test UI scenarios
- [ ] Document any issues
- [ ] Verify all success criteria met
