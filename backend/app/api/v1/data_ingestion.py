"""
Data Ingestion API Endpoints
Upload and process CSV, Excel, and other data formats
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.core.dependencies import (
    get_data_ingestion_service,
    get_enhanced_embedding_service,
    get_redis_client
)
from app.services.data_ingestion_service import DataIngestionService, DataSourceType
from app.services.enhanced_embedding_service import EnhancedEmbeddingService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["data-ingestion"])


class IngestionResponse(BaseModel):
    """Response for data ingestion"""
    success: bool
    table_name: str
    fingerprint: str
    row_count: int
    column_count: int
    source_type: str
    message: str
    schema: dict


class SchemaUploadRequest(BaseModel):
    """Request to upload schema with embeddings"""
    schema: dict
    generate_embeddings: bool = True


@router.post("/upload/csv", response_model=IngestionResponse)
async def upload_csv(
    file: UploadFile = File(...),
    table_name: str = Form(...),
    delimiter: str = Form(","),
    encoding: str = Form("utf-8"),
    generate_embeddings: bool = Form(True),
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Upload and ingest CSV file
    
    - **file**: CSV file to upload
    - **table_name**: Name for the table
    - **delimiter**: CSV delimiter (default: comma)
    - **encoding**: File encoding (default: utf-8)
    - **generate_embeddings**: Generate GNN embeddings for schema (default: true)
    """
    if not settings.ENABLE_FILE_UPLOAD:
        raise HTTPException(status_code=403, detail="File upload is disabled")
    
    # Check file size
    file_size = 0
    content = await file.read()
    file_size = len(content) / (1024 * 1024)  # MB
    
    if file_size > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size:.2f}MB (max: {settings.MAX_UPLOAD_SIZE_MB}MB)"
        )
    
    try:
        # Reset file pointer
        from io import BytesIO
        file_obj = BytesIO(content)
        
        # Ingest CSV
        schema = ingestion_service.ingest_csv(
            file=file_obj,
            table_name=table_name,
            delimiter=delimiter,
            encoding=encoding
        )
        
        # Generate embeddings if requested
        if generate_embeddings:
            try:
                # Wrap schema in database format
                db_schema = {
                    'database': 'uploaded_data',
                    'tables': {table_name: schema},
                    'fingerprint': schema['fingerprint']
                }
                
                embeddings = await embedding_service.embed_schema(db_schema)
                logger.info(f"Generated {len(embeddings)} embeddings for {table_name}")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings: {e}")
        
        return IngestionResponse(
            success=True,
            table_name=table_name,
            fingerprint=schema['fingerprint'],
            row_count=schema['row_count'],
            column_count=len(schema['columns']),
            source_type=schema['source_type'],
            message=f"Successfully ingested CSV file: {file.filename}",
            schema=schema
        )
        
    except Exception as e:
        logger.error(f"CSV ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/upload/excel", response_model=IngestionResponse)
async def upload_excel(
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None),
    sheet_name: Optional[str] = Form(None),
    generate_embeddings: bool = Form(True),
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Upload and ingest Excel file
    
    - **file**: Excel file to upload
    - **table_name**: Name for the table (defaults to sheet name)
    - **sheet_name**: Specific sheet to read (defaults to first sheet)
    - **generate_embeddings**: Generate GNN embeddings for schema
    """
    if not settings.ENABLE_FILE_UPLOAD:
        raise HTTPException(status_code=403, detail="File upload is disabled")
    
    # Check file size
    content = await file.read()
    file_size = len(content) / (1024 * 1024)
    
    if file_size > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size:.2f}MB"
        )
    
    try:
        from io import BytesIO
        file_obj = BytesIO(content)
        
        # Ingest Excel
        schema = ingestion_service.ingest_excel(
            file=file_obj,
            sheet_name=sheet_name,
            table_name=table_name
        )
        
        # Generate embeddings
        if generate_embeddings:
            try:
                db_schema = {
                    'database': 'uploaded_data',
                    'tables': {schema['table_name']: schema},
                    'fingerprint': schema['fingerprint']
                }
                
                embeddings = await embedding_service.embed_schema(db_schema)
                logger.info(f"Generated {len(embeddings)} embeddings")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings: {e}")
        
        return IngestionResponse(
            success=True,
            table_name=schema['table_name'],
            fingerprint=schema['fingerprint'],
            row_count=schema['row_count'],
            column_count=len(schema['columns']),
            source_type=schema['source_type'],
            message=f"Successfully ingested Excel file: {file.filename}",
            schema=schema
        )
        
    except Exception as e:
        logger.error(f"Excel ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest/database-table", response_model=IngestionResponse)
async def ingest_database_table(
    database: str,
    table_name: str,
    sample_size: int = 1000,
    generate_embeddings: bool = True,
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Ingest existing database table
    
    - **database**: Database name
    - **table_name**: Table name
    - **sample_size**: Number of rows to sample for statistics
    - **generate_embeddings**: Generate GNN embeddings
    """
    try:
        # Ingest table
        schema = ingestion_service.ingest_database_table(
            database=database,
            table_name=table_name,
            sample_size=sample_size
        )
        
        # Generate embeddings
        if generate_embeddings:
            try:
                db_schema = {
                    'database': database,
                    'tables': {table_name: schema},
                    'fingerprint': schema['fingerprint']
                }
                
                embeddings = await embedding_service.embed_schema(db_schema)
                logger.info(f"Generated {len(embeddings)} embeddings")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings: {e}")
        
        return IngestionResponse(
            success=True,
            table_name=table_name,
            fingerprint=schema['fingerprint'],
            row_count=schema['row_count'],
            column_count=len(schema['columns']),
            source_type=schema['source_type'],
            message=f"Successfully ingested database table: {database}.{table_name}",
            schema=schema
        )
        
    except Exception as e:
        logger.error(f"Database table ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/schema/upload")
async def upload_schema_with_embeddings(
    request: SchemaUploadRequest,
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Upload pre-extracted schema and optionally generate embeddings
    Useful for external schema extraction pipelines
    """
    try:
        schema = request.schema
        
        if request.generate_embeddings:
            embeddings = await embedding_service.embed_schema(schema, force_regenerate=True)
            
            return {
                "success": True,
                "fingerprint": schema.get('fingerprint', schema.get('version')),
                "embeddings_count": len(embeddings),
                "message": "Schema uploaded and embeddings generated"
            }
        else:
            return {
                "success": True,
                "fingerprint": schema.get('fingerprint', schema.get('version')),
                "message": "Schema uploaded (no embeddings generated)"
            }
        
    except Exception as e:
        logger.error(f"Schema upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported data formats"""
    return {
        "supported_formats": settings.SUPPORTED_FORMATS,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "upload_enabled": settings.ENABLE_FILE_UPLOAD
    }
