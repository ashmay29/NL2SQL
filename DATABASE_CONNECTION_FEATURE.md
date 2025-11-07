# Database Connection Feature

## Overview
Added functionality to connect to external MySQL/PostgreSQL databases directly from the frontend, extract their schemas, and use them in NL2SQL queries.

## Backend Changes

### 1. New API Endpoint: `/api/v1/database/connect`
**File:** `backend/app/api/v1/database_connection.py`

Features:
- Connect to MySQL or PostgreSQL databases
- Extract complete schema (tables, columns, types, keys, relationships)
- Generate embeddings for schema elements
- Cache schema in Redis (7-day TTL for stability)
- Return `database_id` for use in queries

**Request:**
```json
{
  "host": "localhost",
  "port": 3306,
  "username": "root",
  "password": "password",
  "database": "ecommerce",
  "db_type": "mysql"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully connected to ecommerce and extracted schema",
  "database_id": "db_ecommerce",
  "schema_summary": {
    "database": "ecommerce",
    "tables": ["customers", "orders", "products"],
    "table_count": 3,
    "total_columns": 25,
    "has_embeddings": true
  }
}
```

### 2. Test Connection Endpoint: `/api/v1/database/test-connection`
Lightweight endpoint to verify connection parameters before full schema extraction.

### 3. Updated Schema Service
**File:** `backend/app/services/schema_service.py`

- Added optional `database_id` parameter to `cache_schema()` method
- Allows caching with custom keys (e.g., `db_ecommerce` instead of just database name)

### 4. Main App Registration
**File:** `backend/app/main.py`

- Imported and registered database_connection router
- New endpoint accessible at `/api/v1/database/*`

## Frontend Changes

### 1. Database Connection Page
**File:** `frontend/src/pages/DatabaseConnection.tsx`

Features:
- Form to enter database connection details
- Database type selector (MySQL/PostgreSQL)
- Test connection button (lightweight check)
- Connect & extract schema button (full extraction)
- Visual feedback for success/error states
- Display schema summary after connection
- Stores `database_id` in localStorage for easy access

### 2. App Router
**File:** `frontend/src/App.tsx`

- Added route: `/database` → DatabaseConnection component

### 3. Navigation
**File:** `frontend/src/components/Layout.tsx`

- Added "Connect DB" navigation item with Database icon

## Usage Flow

### 1. Connect to Database
1. Navigate to "Connect DB" in the app
2. Select database type (MySQL/PostgreSQL)
3. Enter connection details:
   - Host (e.g., `localhost`, `db.example.com`)
   - Port (default: 3306 for MySQL, 5432 for PostgreSQL)
   - Username
   - Password
   - Database name
4. (Optional) Click "Test Connection" to verify credentials
5. Click "Connect & Extract Schema"

### 2. Use in Queries
After successful connection:
1. Copy the `database_id` (e.g., `db_ecommerce`)
2. Go to NL2SQL Playground
3. In the query form, use the database_id:
   - Either set it in the UI if available
   - Or it's automatically loaded from localStorage

### 3. Schema Caching
- Schema is cached in Redis for 7 days
- Subsequent queries use cached schema (fast)
- Re-connect to refresh schema if database structure changes

## Security Considerations

### Production Deployment
1. **Environment Variables:**
   - Never commit database credentials to code
   - Use environment variables or secure vaults

2. **Network Security:**
   - Use SSL/TLS for database connections
   - Restrict database access by IP/firewall
   - Use read-only database users when possible

3. **Input Validation:**
   - All inputs are validated by Pydantic models
   - Connection timeout prevents hanging
   - Error messages don't expose sensitive details

4. **CORS:**
   - Configure allowed origins in production
   - Don't use `allow_origins=["*"]` in production

## Dependencies

Already included in `requirements.txt`:
- `sqlalchemy==2.0.25` - Database abstraction
- `pymysql==1.1.0` - MySQL driver
- `psycopg2-binary==2.9.9` - PostgreSQL driver

## Example Use Cases

### 1. E-commerce Database
```bash
Host: localhost
Port: 3306
Database: ecommerce
Tables: customers, orders, products, categories
```

Query: "Show me total sales by category last month"

### 2. Employee Database
```bash
Host: db.company.com
Port: 3306
Database: hr_system
Tables: employees, departments, salaries, performance_reviews
```

Query: "Find departments with highest attrition rate"

### 3. Analytics Database
```bash
Host: analytics.example.com
Port: 5432
Database: analytics_db
Tables: events, users, sessions, conversions
```

Query: "What's the conversion rate by traffic source?"

## Error Handling

Common errors and solutions:

1. **Connection timeout:**
   - Check host/port are correct
   - Verify network connectivity
   - Check firewall rules

2. **Access denied:**
   - Verify username/password
   - Check user has SELECT permissions
   - Ensure user can connect from this IP

3. **Database not found:**
   - Verify database name is correct
   - Check user has access to this database

4. **Unsupported database type:**
   - Currently supports MySQL and PostgreSQL only
   - PostgreSQL aliases: 'postgresql' or 'postgres'

## Future Enhancements

Potential improvements:
1. Save connection profiles for quick reconnection
2. Support for other databases (SQLite, MongoDB, etc.)
3. SSL/TLS connection options
4. SSH tunnel support for remote databases
5. Schema diff/comparison tools
6. Automatic schema refresh detection
7. Multi-database queries (JOIN across databases)
8. Connection pooling for better performance

## Testing

### Backend Testing
```bash
# Test connection
curl -X POST http://localhost:8000/api/v1/database/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "password",
    "database": "test_db",
    "db_type": "mysql"
  }'

# Full connection
curl -X POST http://localhost:8000/api/v1/database/connect \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "password",
    "database": "test_db",
    "db_type": "mysql"
  }'
```

### Frontend Testing
1. Start frontend: `npm run dev`
2. Navigate to http://localhost:5173/database
3. Fill in connection form
4. Test connection
5. Extract schema
6. Verify database_id in localStorage
7. Use in Playground

## API Documentation

After starting the backend, visit:
- Swagger UI: http://localhost:8000/docs
- Look for "Database Connection" section
- Try the endpoints interactively

## Monitoring

Logs to watch:
```
✅ MySQL connection established: host:port/database
✅ Cached schema for 'db_name' with key 'schema:db_name'
✅ Generated embeddings for schema elements
```

Redis keys created:
- `schema:db_<database_name>` - Full schema with embeddings
- TTL: 7 days (604,800 seconds)
