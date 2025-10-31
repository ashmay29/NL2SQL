"""
Embedding service with mock and GNN providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract embedding provider"""
    
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embed a query text"""
        pass
    
    @abstractmethod
    async def embed_schema_node(self, node_id: str, metadata: Dict[str, Any]) -> List[float]:
        """Embed a schema node"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock provider using sentence-transformers"""
    
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("MockEmbeddingProvider initialized with all-MiniLM-L6-v2")
        except ImportError:
            logger.error("sentence-transformers not installed. Install: pip install sentence-transformers")
            raise
    
    async def embed_query(self, text: str) -> List[float]:
        """Embed query text"""
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise
    
    async def embed_schema_node(self, node_id: str, metadata: Dict[str, Any]) -> List[float]:
        """Embed schema node as text"""
        try:
            # Combine node info into text
            parts = [metadata.get('name', '')]
            if metadata.get('type'):
                parts.append(metadata['type'])
            if metadata.get('table'):
                parts.append(f"in table {metadata['table']}")
            
            text = ' '.join(parts)
            return await self.embed_query(text)
        except Exception as e:
            logger.error(f"Failed to embed schema node: {e}")
            raise
    
    def get_dimension(self) -> int:
        return 384


class GNNEmbeddingProvider(EmbeddingProvider):
    """GNN provider loading from Redis cache"""
    
    def __init__(self, redis_client, fallback_provider: EmbeddingProvider):
        self.redis = redis_client
        self.fallback = fallback_provider
        logger.info("GNNEmbeddingProvider initialized with Redis cache")
    
    async def embed_query(self, text: str) -> List[float]:
        """
        Embed query using GNN.
        For now, falls back to mock. In production, this would:
        1. Tokenize query
        2. Map tokens to schema nodes
        3. Retrieve GNN embeddings for matched nodes
        4. Aggregate (mean pooling)
        """
        # TODO: Implement GNN-based query embedding
        logger.debug("Using fallback for query embedding (GNN not fully implemented)")
        return await self.fallback.embed_query(text)
    
    async def embed_schema_node(self, node_id: str, metadata: Dict[str, Any]) -> List[float]:
        """Load schema node embedding from Redis"""
        try:
            fingerprint = metadata.get('schema_fingerprint')
            if not fingerprint:
                logger.warning("No schema_fingerprint in metadata, using fallback")
                return await self.fallback.embed_schema_node(node_id, metadata)
            
            key = f"gnn:{fingerprint}:node:{node_id}"
            vec_json = self.redis.get(key)
            
            if vec_json:
                vec = json.loads(vec_json)
                logger.debug(f"Loaded GNN embedding for {node_id} from Redis")
                return vec
            else:
                logger.warning(f"GNN embedding not found for {node_id}, using fallback")
                return await self.fallback.embed_schema_node(node_id, metadata)
        
        except Exception as e:
            logger.error(f"Failed to load GNN embedding: {e}, using fallback")
            return await self.fallback.embed_schema_node(node_id, metadata)
    
    def get_dimension(self) -> int:
        return 512  # GNN embeddings are 512-dim


class EmbeddingService:
    """Main embedding service with provider switching"""
    
    def __init__(self, provider_type: str = "mock", redis_client=None):
        if provider_type == "mock":
            self.provider = MockEmbeddingProvider()
        elif provider_type == "gnn":
            if not redis_client:
                raise ValueError("Redis client required for GNN provider")
            fallback = MockEmbeddingProvider()
            self.provider = GNNEmbeddingProvider(redis_client, fallback)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        logger.info(f"EmbeddingService initialized with provider={provider_type}")
    
    async def embed_query(self, text: str) -> List[float]:
        return await self.provider.embed_query(text)
    
    async def embed_schema_node(self, node_id: str, metadata: Dict[str, Any]) -> List[float]:
        return await self.provider.embed_schema_node(node_id, metadata)
    
    def get_dimension(self) -> int:
        return self.provider.get_dimension()
