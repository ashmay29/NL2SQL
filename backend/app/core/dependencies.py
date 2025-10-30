"""
FastAPI dependencies for dependency injection
"""
import redis
from functools import lru_cache
from app.core.config import settings
from app.services.schema_service import SchemaService
from app.services.cache_service import CacheService
from app.services.llm_service import LLMService


# Redis client (singleton)
@lru_cache()
def get_redis_client() -> redis.Redis:
    """Get Redis client"""
    return redis.from_url(settings.REDIS_URI, decode_responses=True)


# Schema service (singleton)
@lru_cache()
def get_schema_service() -> SchemaService:
    """Get schema service"""
    redis_client = get_redis_client()
    return SchemaService(settings.MYSQL_URI, redis_client)


# Cache service (singleton)
@lru_cache()
def get_cache_service() -> CacheService:
    """Get cache service"""
    redis_client = get_redis_client()
    return CacheService(
        redis_client,
        embedding_model_name=settings.EMBEDDING_MODEL,
        max_size=settings.MAX_CACHE_SIZE,
        similarity_threshold=settings.CACHE_SIMILARITY_THRESHOLD
    )


# LLM service (singleton)
@lru_cache()
def get_llm_service() -> LLMService:
    """Get LLM service"""
    return LLMService(
        provider=settings.LLM_PROVIDER,
        ollama_endpoint=settings.OLLAMA_ENDPOINT,
        ollama_model=settings.OLLAMA_MODEL,
        gemini_api_key=settings.GEMINI_API_KEY,
        gemini_model=settings.GEMINI_MODEL
    )
