"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from app.models.schemas import HealthResponse
from app.core.dependencies import get_redis_client, get_schema_service
import redis
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        services={}
    )


@router.get("/health/detailed", response_model=HealthResponse)
async def detailed_health_check(
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """Detailed health check with service status"""
    services = {}
    
    # Check Redis
    try:
        redis_client.ping()
        services["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        services["redis"] = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if all(
        s == "healthy" for s in services.values()
    ) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        services=services
    )
