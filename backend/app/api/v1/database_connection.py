"""
Database Connection API
Allows users to connect to their own MySQL/PostgreSQL databases
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus
from app.core.dependencies import get_schema_service, get_enhanced_embedding_service
from app.services.schema_service import SchemaService
from app.services.enhanced_embedding_service import EnhancedEmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter()


class DatabaseConnectionRequest(BaseModel):
    """Request model for database connection"""
    host: str = Field(..., description="Database host (e.g., localhost, db.example.com)")
    port: int = Field(3306, description="Database port (default: 3306 for MySQL)")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    database: str = Field(..., description="Database name")
    db_type: str = Field("mysql", description="Database type: mysql or postgresql")
    
    @validator('db_type')
    def validate_db_type(cls, v):
        if v.lower() not in ['mysql', 'postgresql', 'postgres']:
            raise ValueError("db_type must be 'mysql' or 'postgresql'")
        return v.lower()
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class DatabaseConnectionResponse(BaseModel):
    """Response model for successful database connection"""
    success: bool
    message: str
    database_id: str
    schema_summary: Dict[str, Any]


@router.post("/connect", response_model=DatabaseConnectionResponse)
async def connect_to_database(
    request: DatabaseConnectionRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
) -> DatabaseConnectionResponse:
    """
    Connect to a MySQL/PostgreSQL database and extract schema
    
    This endpoint:
    1. Tests the database connection
    2. Extracts the full schema (tables, columns, types, keys, relationships)
    3. Generates embeddings for schema elements
    4. Caches the schema in Redis for fast access
    5. Returns a database_id to use in NL2SQL queries
    
    Example:
        POST /api/v1/database/connect
        {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "ecommerce",
            "db_type": "mysql"
        }
    """
    try:
        logger.info(f"Attempting to connect to {request.db_type} database: {request.database} at {request.host}:{request.port}")
        
        # URL-encode username and password to handle special characters
        encoded_username = quote_plus(request.username)
        encoded_password = quote_plus(request.password)
        
        # Build connection URL
        if request.db_type in ['mysql']:
            # MySQL connection string
            connection_url = (
                f"mysql+pymysql://{encoded_username}:{encoded_password}"
                f"@{request.host}:{request.port}/{request.database}"
            )
        elif request.db_type in ['postgresql', 'postgres']:
            # PostgreSQL connection string
            connection_url = (
                f"postgresql+psycopg2://{encoded_username}:{encoded_password}"
                f"@{request.host}:{request.port}/{request.database}"
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported database type")
        
        # Test connection and extract schema
        try:
            engine = create_engine(
                connection_url,
                pool_pre_ping=True,  # Test connection before using
                pool_recycle=3600,    # Recycle connections after 1 hour
                connect_args={
                    "connect_timeout": 10  # 10 second timeout
                }
            )
            
            # Test connection
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            logger.info(f"Successfully connected to database: {request.database}")
            
            # Extract schema using SQLAlchemy Inspector
            inspector = inspect(engine)
            schema = _extract_schema_from_database(inspector, request.database)
            
            logger.info(f"Extracted schema: {len(schema['tables'])} tables")
            
            # Generate embeddings for schema elements
            try:
                embeddings = await embedding_service.embed_schema(schema)
                logger.info(f"Generated {len(embeddings)} embeddings for schema elements")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings: {e}. Continuing without embeddings.")
            
            # Cache schema in Redis with TTL of 7 days (user databases are more stable)
            database_id = f"db_{request.database}"
            ttl = 7 * 24 * 60 * 60  # 7 days
            schema_service.cache_schema(schema, database_id=database_id, ttl=ttl)
            
            logger.info(f"Cached schema with database_id: {database_id}")
            
            # Build schema summary for response
            schema_summary = {
                "database": request.database,
                "tables": list(schema['tables'].keys()),
                "table_count": len(schema['tables']),
                "total_columns": sum(len(t['columns']) for t in schema['tables'].values()),
                "has_embeddings": "embeddings" in schema
            }
            
            # Clean up engine
            engine.dispose()
            
            return DatabaseConnectionResponse(
                success=True,
                message=f"Successfully connected to {request.database} and extracted schema",
                database_id=database_id,
                schema_summary=schema_summary
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to database: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


def _extract_schema_from_database(inspector, database_name: str) -> Dict[str, Any]:
    """
    Extract schema from database using SQLAlchemy Inspector
    
    Args:
        inspector: SQLAlchemy Inspector instance
        database_name: Name of the database
        
    Returns:
        Schema in backend format
    """
    schema = {
        "database": database_name,
        "tables": {}
    }
    
    # Get all table names
    table_names = inspector.get_table_names()
    
    for table_name in table_names:
        # Get columns
        columns = []
        for col in inspector.get_columns(table_name):
            col_info = {
                "name": col['name'],
                "type": str(col['type']),
                "nullable": col.get('nullable', True),
                "primary_key": False,  # Will be updated below
                "default": str(col.get('default')) if col.get('default') else None
            }
            columns.append(col_info)
        
        # Get primary keys
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = pk_constraint.get('constrained_columns', [])
        for col in columns:
            if col['name'] in pk_columns:
                col['primary_key'] = True
        
        # Get foreign keys
        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name):
            fk_info = {
                "constrained_columns": fk.get('constrained_columns', []),
                "referred_table": fk.get('referred_table', ''),
                "referred_columns": fk.get('referred_columns', []),
                "name": fk.get('name')
            }
            foreign_keys.append(fk_info)
        
        # Get indexes (for optimization hints)
        indexes = []
        for idx in inspector.get_indexes(table_name):
            idx_info = {
                "name": idx.get('name'),
                "columns": idx.get('column_names', []),
                "unique": idx.get('unique', False)
            }
            indexes.append(idx_info)
        
        # Try to get row count (may fail on some databases)
        row_count = None
        try:
            # This requires an active connection
            # We'll skip it for now and let the schema service handle it
            pass
        except:
            pass
        
        schema['tables'][table_name] = {
            "columns": columns,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "row_count": row_count
        }
    
    return schema


@router.post("/test-connection")
async def test_database_connection(request: DatabaseConnectionRequest) -> Dict[str, Any]:
    """
    Test database connection without extracting schema
    
    This is a lightweight endpoint to verify connection parameters
    before committing to full schema extraction.
    """
    try:
        # URL-encode username and password to handle special characters
        encoded_username = quote_plus(request.username)
        encoded_password = quote_plus(request.password)
        
        # Build connection URL
        if request.db_type in ['mysql']:
            connection_url = (
                f"mysql+pymysql://{encoded_username}:{encoded_password}"
                f"@{request.host}:{request.port}/{request.database}"
            )
        elif request.db_type in ['postgresql', 'postgres']:
            connection_url = (
                f"postgresql+psycopg2://{encoded_username}:{encoded_password}"
                f"@{request.host}:{request.port}/{request.database}"
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported database type")
        
        # Test connection
        engine = create_engine(
            connection_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5}
        )
        
        with engine.connect() as conn:
            # Get database version
            if request.db_type == 'mysql':
                result = conn.execute(text("SELECT VERSION()"))
            else:  # postgresql
                result = conn.execute(text("SELECT version()"))
            
            version = result.fetchone()[0]
            
            # Get table count
            inspector = inspect(engine)
            table_count = len(inspector.get_table_names())
        
        engine.dispose()
        
        return {
            "success": True,
            "message": "Connection successful",
            "database": request.database,
            "version": version,
            "table_count": table_count
        }
        
    except SQLAlchemyError as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Connection failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in connection test: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
