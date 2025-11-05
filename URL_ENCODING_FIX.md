# URL Encoding Fix for Database Passwords

## Issue
Database passwords containing special characters (like `@`, `#`, `%`, `:`, etc.) were causing connection failures because they weren't being properly URL-encoded in the connection string.

## Solution
Added `urllib.parse.quote_plus()` to encode both username and password before building the SQLAlchemy connection URL.

## Changes Made

### File: `backend/app/api/v1/database_connection.py`

1. **Added import:**
   ```python
   from urllib.parse import quote_plus
   ```

2. **Updated connection URL building in `/connect` endpoint:**
   ```python
   # URL-encode username and password to handle special characters
   encoded_username = quote_plus(request.username)
   encoded_password = quote_plus(request.password)
   
   # Build connection URL with encoded credentials
   connection_url = (
       f"mysql+pymysql://{encoded_username}:{encoded_password}"
       f"@{request.host}:{request.port}/{request.database}"
   )
   ```

3. **Updated connection URL building in `/test-connection` endpoint:**
   - Same encoding applied to ensure consistency

## Special Characters Handled

The `quote_plus()` function properly encodes:
- `@` → `%40`
- `#` → `%23`
- `%` → `%25`
- `:` → `%3A`
- `/` → `%2F`
- `?` → `%3F`
- `&` → `%26`
- `=` → `%3D`
- `+` → `%2B`
- Space → `+`

## Examples

### Password with `@` character:
```
Original:    user@123
Encoded:     user%40123
Connection:  mysql+pymysql://root:user%40123@localhost:3306/mydb
```

### Password with multiple special characters:
```
Original:    P@ss#w0rd!
Encoded:     P%40ss%23w0rd%21
Connection:  mysql+pymysql://admin:P%40ss%23w0rd%21@db.example.com:3306/production
```

## Testing

### Before Fix:
```bash
# Password: root@123
curl -X POST http://localhost:8000/api/v1/database/connect \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "root@123",
    "database": "test_db",
    "db_type": "mysql"
  }'

# Result: Connection failed - password interpreted as "root" with host "123@localhost"
```

### After Fix:
```bash
# Password: root@123
curl -X POST http://localhost:8000/api/v1/database/connect \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "root@123",
    "database": "test_db",
    "db_type": "mysql"
  }'

# Result: ✅ Connection successful - password correctly encoded as "root%40123"
```

## Frontend Impact

**No changes needed in frontend!** 

The frontend sends credentials as JSON in the request body, not as a URL. The encoding happens on the backend when building the SQLAlchemy connection string.

Users can enter passwords with special characters directly in the UI:
```
Password: [root@123]  ← User types this
         ↓
Backend receives: "root@123" (via JSON)
         ↓
Backend encodes: "root%40123" (for connection URL)
         ↓
MySQL receives: "root@123" (decoded by driver)
```

## Security Notes

1. **Credentials are not logged** - The encoded password is only used internally for connection
2. **HTTPS recommended** - Always use HTTPS in production to encrypt credentials in transit
3. **Connection string not exposed** - The full connection URL is never returned to the client
4. **Error messages sanitized** - SQLAlchemy errors don't expose the password

## Verification

To verify the fix works:

1. Create a database user with a password containing `@`:
   ```sql
   CREATE USER 'testuser'@'localhost' IDENTIFIED BY 'pass@word123';
   GRANT ALL PRIVILEGES ON test_db.* TO 'testuser'@'localhost';
   ```

2. Test connection via API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/database/test-connection \
     -H "Content-Type: application/json" \
     -d '{
       "host": "localhost",
       "port": 3306,
       "username": "testuser",
       "password": "pass@word123",
       "database": "test_db",
       "db_type": "mysql"
     }'
   ```

3. Expected response:
   ```json
   {
     "success": true,
     "message": "Connection successful",
     "database": "test_db",
     "version": "8.0.x",
     "table_count": 5
   }
   ```

## Related Files

- `backend/app/api/v1/database_connection.py` - Main fix applied here
- `frontend/src/pages/NLSQLPlayground.tsx` - No changes needed (sends JSON)
- `frontend/src/pages/DatabaseConnection.tsx` - No changes needed (standalone page)

## Additional Resources

- [Python urllib.parse documentation](https://docs.python.org/3/library/urllib.parse.html)
- [SQLAlchemy Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [URL encoding reference](https://www.w3schools.com/tags/ref_urlencode.asp)
