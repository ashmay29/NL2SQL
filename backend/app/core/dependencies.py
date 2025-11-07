"""
FastAPI dependencies for dependency injection
"""
import redis
import logging
from functools import lru_cache
from typing import Any, Optional
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
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.data_ingestion_service import DataIngestionService
from app.services.gnn_inference_service import GNNInferenceService
from app.services.enhanced_embedding_service import EnhancedEmbeddingService
from app.services.gnn_ranker_service import GNNRankerService


class MockRedis:
    """Mock Redis client with in-memory storage for when Redis is unavailable"""
    def __init__(self):
        self._storage = {}  # In-memory key-value store
        self._ttl = {}      # Track expiration times
    
    def get(self, key: str) -> Optional[str]:
        """Get value from in-memory storage"""
        import time
        # Check if key expired
        if key in self._ttl and time.time() > self._ttl[key]:
            del self._storage[key]
            del self._ttl[key]
            return None
        return self._storage.get(key)
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set value in in-memory storage"""
        self._storage[key] = value
        if ex:
            import time
            self._ttl[key] = time.time() + ex
        return True
    
    def setex(self, key: str, time: int, value: Any) -> bool:
        """Set value with expiration in in-memory storage"""
        import time as t
        self._storage[key] = value
        self._ttl[key] = t.time() + time
        return True
    
    def delete(self, *keys: str) -> int:
        """Delete keys from in-memory storage"""
        count = 0
        for key in keys:
            if key in self._storage:
                del self._storage[key]
                if key in self._ttl:
                    del self._ttl[key]
                count += 1
        return count
    
    def ping(self) -> bool:
        """Always return True for mock"""
        return True
    
    def exists(self, key: str) -> int:
        """Check if key exists in in-memory storage"""
        import time
        if key in self._ttl and time.time() > self._ttl[key]:
            del self._storage[key]
            del self._ttl[key]
            return 0
        return 1 if key in self._storage else 0


# Redis client (singleton)
@lru_cache()
def get_redis_client() -> redis.Redis:
    """Get Redis client with graceful fallback"""
    try:
        client = redis.from_url(settings.REDIS_URI, decode_responses=True)
        # Test connection
        client.ping()
        logger = logging.getLogger(__name__)
        logger.info(f"✅ Redis connection established: {settings.REDIS_URI}")
        return client
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️  Redis connection failed: {e}")
        logger.warning("Caching will be disabled. Install Redis or update REDIS_URI in .env")
        # Return a mock Redis client that does nothing
        return MockRedis()


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


# GNN Inference service (singleton)
@lru_cache()
def get_gnn_inference_service() -> GNNInferenceService:
    """Get GNN inference service"""
    return GNNInferenceService(
        gnn_endpoint=settings.GNN_ENDPOINT,
        timeout=settings.GNN_TIMEOUT,
        use_mock=settings.USE_GNN_FALLBACK
    )


# GNN Ranker service (singleton) - Local GNN model
@lru_cache()
def get_gnn_ranker_service() -> GNNRankerService:
    """Get local GNN Ranker service"""
    if not settings.USE_LOCAL_GNN:
        return None
    
    try:
        return GNNRankerService(
            model_path=settings.GNN_MODEL_PATH,
            device=settings.GNN_DEVICE,
            node_feature_dim=settings.GNN_NODE_FEATURE_DIM,
            node_embedding_dim=384,  # SentenceTransformer dimension
            question_embedding_dim=768,  # BERT dimension
            hidden_channels=settings.GNN_HIDDEN_CHANNELS,
            use_rich_node_embeddings=True
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to initialize GNN Ranker: {e}")
        return None


# Enhanced Embedding service (singleton)
@lru_cache()
def get_enhanced_embedding_service() -> EnhancedEmbeddingService:
    """Get enhanced embedding service with GNN + SentenceTransformer"""
    # Use local GNN if enabled, otherwise external GNN service
    if settings.USE_LOCAL_GNN:
        gnn_service = get_gnn_ranker_service()
    else:
        gnn_service = get_gnn_inference_service() if settings.GNN_ENDPOINT else None
    
    return EnhancedEmbeddingService(
        redis_client=get_redis_client(),
        gnn_service=gnn_service,
        use_sentence_transformer=settings.USE_GNN_FALLBACK,
        embedding_dim=settings.EMBEDDING_DIM
    )


# Embedding service (singleton) - backwards compatible
@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get embedding service (legacy, prefer get_enhanced_embedding_service)"""
    provider_type = getattr(settings, 'EMBEDDING_PROVIDER', 'mock')
    
    # If 'enhanced' provider, return enhanced service wrapped
    if provider_type == 'enhanced':
        # Return enhanced service (compatible interface)
        return get_enhanced_embedding_service()
    
    # Legacy providers
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


# Data Ingestion service (singleton)
@lru_cache()
def get_data_ingestion_service() -> DataIngestionService:
    """Get data ingestion service"""
    return DataIngestionService(mysql_uri=settings.MYSQL_URI)


# Pipeline orchestrator (singleton)
@lru_cache()
def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """Get pipeline orchestrator"""
    return PipelineOrchestrator(
        schema_service=get_schema_service(),
        llm_service=get_llm_service(),
        feedback_service=get_feedback_service(),
        context_service=get_context_service(),
        complexity_service=get_complexity_service(),
        corrector_service=get_corrector_service(),
        clarification_service=get_clarification_service()
    )
