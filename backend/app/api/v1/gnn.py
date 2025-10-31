"""
GNN Service API Endpoints
Manage GNN embeddings and inference
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from app.core.dependencies import (
    get_gnn_inference_service,
    get_enhanced_embedding_service,
    get_schema_service
)
from app.services.gnn_inference_service import GNNInferenceService
from app.services.enhanced_embedding_service import EnhancedEmbeddingService
from app.services.schema_service import SchemaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gnn", tags=["gnn"])


class EmbeddingGenerationRequest(BaseModel):
    """Request to generate embeddings for a schema"""
    database: str
    force_regenerate: bool = False


class QueryEmbeddingRequest(BaseModel):
    """Request to generate query embedding"""
    query_text: str
    database: str
    context: Optional[Dict[str, Any]] = None


class RelevantNodesRequest(BaseModel):
    """Request to find relevant schema nodes"""
    query_text: str
    database: str
    top_k: int = 10


@router.post("/embeddings/generate")
async def generate_schema_embeddings(
    request: EmbeddingGenerationRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Generate GNN embeddings for a database schema
    
    - **database**: Database name
    - **force_regenerate**: Force regeneration even if cached
    
    This endpoint:
    1. Extracts schema from database
    2. Converts schema to graph representation
    3. Calls GNN model for inference (or uses fallback)
    4. Caches embeddings in Redis
    """
    try:
        # Get schema
        schema = schema_service.get_cached_schema(request.database)
        if not schema or request.force_regenerate:
            schema = schema_service.extract_schema(request.database)
            schema_service.cache_schema(schema)
        
        # Generate embeddings
        embeddings = await embedding_service.embed_schema(
            schema,
            force_regenerate=request.force_regenerate
        )
        
        return {
            "success": True,
            "database": request.database,
            "fingerprint": schema.get('version'),
            "embeddings_count": len(embeddings),
            "dimension": embedding_service.get_dimension(),
            "tables": len(schema.get('tables', {})),
            "message": "Embeddings generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


@router.post("/embeddings/query")
async def generate_query_embedding(
    request: QueryEmbeddingRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Generate embedding for a natural language query
    
    - **query_text**: Natural language query
    - **database**: Database context
    - **context**: Optional conversation context
    """
    try:
        # Get schema for context
        schema = schema_service.get_cached_schema(request.database)
        if not schema:
            schema = schema_service.extract_schema(request.database)
            schema_service.cache_schema(schema)
        
        # Generate query embedding
        embedding = await embedding_service.embed_query(
            request.query_text,
            schema=schema,
            use_cache=True
        )
        
        return {
            "success": True,
            "query": request.query_text,
            "embedding": embedding,
            "dimension": len(embedding),
            "database": request.database
        }
        
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Query embedding failed: {str(e)}")


@router.post("/similarity/relevant-nodes")
async def get_relevant_nodes(
    request: RelevantNodesRequest,
    schema_service: SchemaService = Depends(get_schema_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Find most relevant schema nodes for a query
    Uses GNN-based similarity search
    
    - **query_text**: Natural language query
    - **database**: Database name
    - **top_k**: Number of top nodes to return
    """
    try:
        # Get schema
        schema = schema_service.get_cached_schema(request.database)
        if not schema:
            schema = schema_service.extract_schema(request.database)
            schema_service.cache_schema(schema)
        
        # Get relevant nodes
        nodes = await embedding_service.get_relevant_schema_context(
            request.query_text,
            schema,
            top_k=request.top_k
        )
        
        return {
            "success": True,
            "query": request.query_text,
            "database": request.database,
            "nodes": nodes,
            "count": len(nodes)
        }
        
    except Exception as e:
        logger.error(f"Failed to get relevant nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


@router.get("/health")
async def gnn_health_check(
    gnn_service: GNNInferenceService = Depends(get_gnn_inference_service)
):
    """
    Check GNN service health
    Returns status of external GNN model server
    """
    try:
        health = await gnn_service.health_check()
        return health
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.delete("/embeddings/invalidate/{database}")
async def invalidate_embeddings(
    database: str,
    schema_service: SchemaService = Depends(get_schema_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Invalidate cached embeddings for a database
    Useful after schema changes
    """
    try:
        # Get schema fingerprint
        schema = schema_service.get_cached_schema(database)
        if schema:
            fingerprint = schema.get('version')
            await embedding_service.invalidate_cache(fingerprint)
            
            return {
                "success": True,
                "database": database,
                "fingerprint": fingerprint,
                "message": "Embeddings invalidated"
            }
        else:
            return {
                "success": False,
                "database": database,
                "message": "No cached schema found"
            }
        
    except Exception as e:
        logger.error(f"Failed to invalidate embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Invalidation failed: {str(e)}")


@router.get("/info")
async def gnn_service_info(
    gnn_service: GNNInferenceService = Depends(get_gnn_inference_service),
    embedding_service: EnhancedEmbeddingService = Depends(get_enhanced_embedding_service)
):
    """
    Get information about GNN service configuration
    """
    health = await gnn_service.health_check()
    
    return {
        "gnn_endpoint": gnn_service.gnn_endpoint,
        "gnn_status": health.get('status'),
        "use_mock_fallback": gnn_service.use_mock,
        "embedding_dimension": embedding_service.get_dimension(),
        "sentence_transformer_available": embedding_service.sentence_model is not None,
        "cache_enabled": True
    }
