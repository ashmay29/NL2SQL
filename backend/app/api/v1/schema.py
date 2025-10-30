"""
Schema management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import SchemaInfo, SchemaRefreshResponse
from app.services.schema_service import SchemaService
from app.core.dependencies import get_schema_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/schema", response_model=SchemaInfo)
async def get_schema(
    database: str = "nl2sql_target",
    schema_service: SchemaService = Depends(get_schema_service)
):
    """Get current schema with caching"""
    try:
        # Try cache first
        cached_schema = schema_service.get_cached_schema(database)
        if cached_schema:
            logger.info(f"Returning cached schema for {database}")
            return SchemaInfo(**cached_schema)
        
        # Extract fresh schema
        schema = schema_service.extract_schema(database)
        
        # Cache it
        schema_service.cache_schema(schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
        
        return SchemaInfo(**schema)
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schema/refresh", response_model=SchemaRefreshResponse)
async def refresh_schema(
    database: str = "nl2sql_target",
    schema_service: SchemaService = Depends(get_schema_service)
):
    """Force schema refresh and return diff"""
    try:
        # Get old schema
        old_schema = schema_service.get_cached_schema(database)
        if not old_schema:
            old_schema = schema_service.extract_schema(database)
        
        # Extract new schema
        new_schema = schema_service.extract_schema(database)
        
        # Detect changes
        changes = schema_service.detect_schema_changes(old_schema, new_schema)
        
        # Invalidate caches
        schema_service.invalidate_dependent_caches(changes)
        
        # Cache new schema
        schema_service.cache_schema(new_schema, ttl=settings.SCHEMA_REFRESH_TTL_SEC)
        
        invalidated = [
            f"gnn_embedding:{table}" 
            for table in (
                changes['added_tables'] + 
                changes['removed_tables'] + 
                list(changes['modified_tables'].keys())
            )
        ]
        invalidated.append("gnn_embedding:full_schema")
        
        return SchemaRefreshResponse(
            old_version=old_schema['version'],
            new_version=new_schema['version'],
            changes=changes,
            invalidated_caches=invalidated
        )
        
    except Exception as e:
        logger.error(f"Schema refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/graph")
async def get_schema_graph(
    database: str = "nl2sql_target",
    schema_service: SchemaService = Depends(get_schema_service)
):
    """Get schema as graph JSON for visualization"""
    try:
        schema = schema_service.get_cached_schema(database)
        if not schema:
            schema = schema_service.extract_schema(database)
            schema_service.cache_schema(schema)
        
        # Build graph structure
        nodes = []
        edges = []
        
        # Add table nodes
        for table_name in schema['tables'].keys():
            nodes.append({
                "id": f"table:{table_name}",
                "type": "table",
                "label": table_name
            })
        
        # Add column nodes and edges
        for table_name, table_info in schema['tables'].items():
            for col in table_info['columns']:
                col_id = f"column:{table_name}.{col['name']}"
                nodes.append({
                    "id": col_id,
                    "type": "column",
                    "label": col['name'],
                    "table": table_name,
                    "data_type": col['type'],
                    "primary_key": col['primary_key']
                })
                
                # Edge: table contains column
                edges.append({
                    "source": f"table:{table_name}",
                    "target": col_id,
                    "type": "contains"
                })
        
        # Add FK edges
        for rel in schema['relationships']:
            edges.append({
                "source": f"table:{rel['from_table']}",
                "target": f"table:{rel['to_table']}",
                "type": "foreign_key",
                "label": f"{','.join(rel['from_columns'])} → {','.join(rel['to_columns'])}"
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "schema_fingerprint": schema['version']
        }
        
    except Exception as e:
        logger.error(f"Schema graph generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
