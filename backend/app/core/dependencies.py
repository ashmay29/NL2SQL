"""
FastAPI dependencies for dependency injection
"""
import redis
from functools import lru_cache
from app.core.config import settings
from app.services.schema_service import SchemaService
from app.services.cache_service import CacheService
from app.services.llm_service import LLMService
from app.services.qdrant_service import QdrantService
from app.services.embedding_service import EmbeddingService
from app.services.feedback_service import FeedbackService
from app.services.context_service import ContextService
from app.services.complexity_service import ComplexityService
from app.services.corrector_service import CorrectorService
from app.services.clarification_service import ClarificationService
from app.services.error_explainer import ErrorExplainer


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


# Qdrant service (singleton)
@lru_cache()
def get_qdrant_service() -> QdrantService:
    """Get Qdrant service"""
    return QdrantService(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )


# Embedding service (singleton)
@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get embedding service"""
    provider_type = getattr(settings, 'EMBEDDING_PROVIDER', 'mock')
    redis_client = get_redis_client() if provider_type == 'gnn' else None
    return EmbeddingService(provider_type=provider_type, redis_client=redis_client)


# Feedback service (singleton)
@lru_cache()
def get_feedback_service() -> FeedbackService:
    """Get feedback service"""
    return FeedbackService(
        qdrant_service=get_qdrant_service(),
        embedding_service=get_embedding_service()
    )


# Context service (singleton)
@lru_cache()
def get_context_service() -> ContextService:
    """Get context service"""
    return ContextService(
        redis_client=get_redis_client(),
        max_turns=settings.MAX_CONTEXT_TURNS,
        ttl_seconds=3600
    )


# Complexity service (singleton)
@lru_cache()
def get_complexity_service() -> ComplexityService:
    """Get complexity service"""
    return ComplexityService()


# Corrector service (singleton)
@lru_cache()
def get_corrector_service() -> CorrectorService:
    """Get corrector service"""
    return CorrectorService()


# Clarification service (singleton)
@lru_cache()
def get_clarification_service() -> ClarificationService:
    """Get clarification service"""
    return ClarificationService(
        confidence_threshold=settings.CLARIFY_CONFIDENCE_THRESHOLD
    )


# Error explainer (singleton)
@lru_cache()
def get_error_explainer() -> ErrorExplainer:
    """Get error explainer"""
    return ErrorExplainer(verbose=settings.ERROR_EXPLAIN_VERBOSE)
