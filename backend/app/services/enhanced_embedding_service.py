"""
Enhanced Embedding Service
Integrates Sentence Transformer + GNN embeddings with intelligent fallback
Supports both schema node embeddings and query embeddings
"""
from typing import Dict, Any, List, Optional
import logging
import json
import redis
from app.services.gnn_inference_service import GNNInferenceService

logger = logging.getLogger(__name__)


class EnhancedEmbeddingService:
    """
    Enhanced embedding service that orchestrates:
    1. Sentence Transformer for text embeddings (fallback)
    2. GNN model for graph-aware schema embeddings (primary)
    3. Redis caching for performance
    
    Flow:
    - Query comes in → Check cache
    - If miss → Generate with GNN (if available) or SentenceTransformer
    - Cache result → Return
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        gnn_service: Optional[GNNInferenceService] = None,
        use_sentence_transformer: bool = True,
        embedding_dim: int = 512
    ):
        """
        Initialize enhanced embedding service
        
        Args:
            redis_client: Redis client for caching
            gnn_service: GNN inference service (optional)
            use_sentence_transformer: Enable sentence transformer fallback
            embedding_dim: Embedding dimension (512 for GNN, 384 for SentenceTransformer)
        """
        self.redis = redis_client
        self.gnn_service = gnn_service
        self.use_sentence_transformer = use_sentence_transformer
        self.embedding_dim = embedding_dim
        
        # Initialize sentence transformer if enabled
        self.sentence_model = None
        if use_sentence_transformer:
            try:
                from sentence_transformers import SentenceTransformer
                self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence Transformer initialized (fallback mode)")
            except ImportError:
                logger.warning("sentence-transformers not available, GNN-only mode")
        
        logger.info(f"EnhancedEmbeddingService initialized (dim={embedding_dim})")
    
    async def embed_query(
        self,
        query_text: str,
        schema: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[float]:
        """
        Generate embedding for a natural language query
        
        Priority:
        1. Check Redis cache
        2. Try GNN service (if available and schema provided)
        3. Fall back to Sentence Transformer
        
        Args:
            query_text: Natural language query
            schema: Optional schema context for GNN
            use_cache: Whether to use/update cache
            
        Returns:
            Query embedding vector
        """
        try:
            # Check cache
            if use_cache:
                cache_key = f"query_emb:{hash(query_text)}"
                cached = self.redis.get(cache_key)
                if cached:
                    logger.debug("Query embedding cache hit")
                    return json.loads(cached)
            
            # Try GNN if available and schema provided
            if self.gnn_service and schema:
                try:
                    embedding = await self.gnn_service.generate_query_embedding(
                        query_text,
                        schema
                    )
                    
                    # Cache result
                    if use_cache:
                        self.redis.setex(cache_key, 3600, json.dumps(embedding))
                    
                    logger.debug("Generated query embedding with GNN")
                    return embedding
                    
                except Exception as e:
                    logger.warning(f"GNN query embedding failed: {e}, falling back")
            
            # Fall back to Sentence Transformer
            if self.sentence_model:
                embedding = self.sentence_model.encode(
                    query_text,
                    convert_to_numpy=True
                ).tolist()
                
                # Pad/truncate to target dimension if needed
                embedding = self._normalize_dimension(embedding)
                
                # Cache result
                if use_cache:
                    self.redis.setex(cache_key, 3600, json.dumps(embedding))
                
                logger.debug("Generated query embedding with SentenceTransformer")
                return embedding
            
            # No embedding method available
            raise RuntimeError("No embedding method available (GNN and SentenceTransformer both unavailable)")
            
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise
    
    async def embed_schema(
        self,
        schema: Dict[str, Any],
        force_regenerate: bool = False
    ) -> Dict[str, List[float]]:
        """
        Generate embeddings for all nodes in a schema
        
        Args:
            schema: Schema dictionary
            force_regenerate: Force regeneration even if cached
            
        Returns:
            Dictionary mapping node_id → embedding
        """
        try:
            fingerprint = schema.get('fingerprint', schema.get('version'))
            
            # Check cache
            if not force_regenerate and fingerprint:
                cache_key = f"schema_emb:{fingerprint}"
                cached = self.redis.get(cache_key)
                if cached:
                    logger.info(f"Schema embeddings cache hit for {fingerprint}")
                    return json.loads(cached)
            
            # Generate with GNN if available
            if self.gnn_service:
                try:
                    embeddings = await self.gnn_service.generate_schema_embeddings(
                        schema,
                        force_regenerate
                    )
                    
                    # Cache result
                    if fingerprint:
                        cache_key = f"schema_emb:{fingerprint}"
                        self.redis.setex(cache_key, 7200, json.dumps(embeddings))
                    
                    logger.info(f"Generated {len(embeddings)} schema embeddings with GNN")
                    return embeddings
                    
                except Exception as e:
                    logger.warning(f"GNN schema embedding failed: {e}, falling back")
            
            # Fall back to Sentence Transformer
            if self.sentence_model:
                embeddings = await self._embed_schema_with_transformer(schema)
                
                # Cache result
                if fingerprint:
                    cache_key = f"schema_emb:{fingerprint}"
                    self.redis.setex(cache_key, 7200, json.dumps(embeddings))
                
                logger.info(f"Generated {len(embeddings)} schema embeddings with SentenceTransformer")
                return embeddings
            
            raise RuntimeError("No embedding method available")
            
        except Exception as e:
            logger.error(f"Failed to embed schema: {e}")
            raise
    
    async def embed_schema_node(
        self,
        node_id: str,
        metadata: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        Generate embedding for a single schema node
        
        Args:
            node_id: Node identifier (e.g., "table:customers", "column:orders.id")
            metadata: Node metadata
            schema: Full schema context (for GNN)
            
        Returns:
            Node embedding vector
        """
        try:
            fingerprint = metadata.get('schema_fingerprint')
            
            # Check cache
            if fingerprint:
                cache_key = f"gnn:{fingerprint}:node:{node_id}"
                cached = self.redis.get(cache_key)
                if cached:
                    logger.debug(f"Node embedding cache hit for {node_id}")
                    return json.loads(cached)
            
            # If full schema embeddings available, extract node
            if schema:
                schema_embeddings = await self.embed_schema(schema)
                if node_id in schema_embeddings:
                    return schema_embeddings[node_id]
            
            # Fall back to text-based embedding
            if self.sentence_model:
                # Build text representation
                parts = [metadata.get('name', '')]
                if metadata.get('type'):
                    parts.append(metadata['type'])
                if metadata.get('table'):
                    parts.append(f"in table {metadata['table']}")
                
                text = ' '.join(parts)
                embedding = self.sentence_model.encode(
                    text,
                    convert_to_numpy=True
                ).tolist()
                
                embedding = self._normalize_dimension(embedding)
                
                # Cache result
                if fingerprint:
                    cache_key = f"gnn:{fingerprint}:node:{node_id}"
                    self.redis.setex(cache_key, 7200, json.dumps(embedding))
                
                return embedding
            
            raise RuntimeError("No embedding method available")
            
        except Exception as e:
            logger.error(f"Failed to embed schema node: {e}")
            raise
    
    async def get_relevant_schema_context(
        self,
        query_text: str,
        schema: Dict[str, Any],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find most relevant schema nodes for a query
        Uses GNN-based similarity if available
        
        Args:
            query_text: Natural language query
            schema: Full schema
            top_k: Number of top nodes to return
            
        Returns:
            List of relevant nodes with metadata
        """
        try:
            # Generate query embedding
            query_emb = await self.embed_query(query_text, schema)
            
            # Generate schema embeddings
            schema_embs = await self.embed_schema(schema)
            
            # Get relevant nodes
            if self.gnn_service:
                try:
                    nodes = await self.gnn_service.get_relevant_schema_nodes(
                        query_emb,
                        schema_embs,
                        top_k
                    )
                    return nodes
                except Exception as e:
                    logger.warning(f"GNN similarity search failed: {e}, using fallback")
            
            # Fallback: simple cosine similarity
            return self._cosine_similarity_search(query_emb, schema_embs, top_k)
            
        except Exception as e:
            logger.error(f"Failed to get relevant schema context: {e}")
            return []
    
    async def _embed_schema_with_transformer(
        self,
        schema: Dict[str, Any]
    ) -> Dict[str, List[float]]:
        """Generate schema embeddings using Sentence Transformer"""
        embeddings = {}
        tables = schema.get('tables', {})
        
        for table_name, table_info in tables.items():
            # Table embedding
            table_text = f"table {table_name}"
            table_id = f"table:{table_name}"
            embeddings[table_id] = self.sentence_model.encode(
                table_text,
                convert_to_numpy=True
            ).tolist()
            embeddings[table_id] = self._normalize_dimension(embeddings[table_id])
            
            # Column embeddings
            for col in table_info.get('columns', []):
                col_text = f"column {col['name']} of type {col['type']} in table {table_name}"
                col_id = f"column:{table_name}.{col['name']}"
                embeddings[col_id] = self.sentence_model.encode(
                    col_text,
                    convert_to_numpy=True
                ).tolist()
                embeddings[col_id] = self._normalize_dimension(embeddings[col_id])
        
        return embeddings
    
    def _normalize_dimension(self, embedding: List[float]) -> List[float]:
        """Pad or truncate embedding to target dimension"""
        if len(embedding) == self.embedding_dim:
            return embedding
        elif len(embedding) < self.embedding_dim:
            # Pad with zeros
            return embedding + [0.0] * (self.embedding_dim - len(embedding))
        else:
            # Truncate
            return embedding[:self.embedding_dim]
    
    def _cosine_similarity_search(
        self,
        query_emb: List[float],
        schema_embs: Dict[str, List[float]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Simple cosine similarity search"""
        import numpy as np
        
        query_vec = np.array(query_emb)
        similarities = []
        
        for node_id, node_emb in schema_embs.items():
            node_vec = np.array(node_emb)
            
            # Cosine similarity
            sim = np.dot(query_vec, node_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(node_vec) + 1e-8
            )
            
            similarities.append({
                "node_id": node_id,
                "similarity": float(sim),
                "embedding": node_emb
            })
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    async def invalidate_cache(self, fingerprint: str):
        """Invalidate cached embeddings for a schema"""
        try:
            # Delete schema embeddings
            self.redis.delete(f"schema_emb:{fingerprint}")
            
            # Delete individual node embeddings
            pattern = f"gnn:{fingerprint}:node:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            
            logger.info(f"Invalidated cache for fingerprint {fingerprint}")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
