"""
Semantic cache service for query results
Migrated from SemanticCache in nl_to_sql_llm.py
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import redis
import json
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Cache for storing and retrieving similar queries using embeddings"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_size: int = 1000,
        similarity_threshold: float = 0.85
    ):
        self.redis = redis_client
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.cache_entries: List[Dict] = []
        self.index: Optional[faiss.Index] = None
        
        logger.info(f"CacheService initialized with model={embedding_model_name}")
    
    def _rebuild_index(self):
        """Rebuild FAISS index from cache entries"""
        if not self.cache_entries:
            return
        
        embeddings = np.array([entry['embedding'] for entry in self.cache_entries])
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        logger.debug(f"Rebuilt FAISS index with {len(self.cache_entries)} entries")
    
    def add(
        self,
        question: str,
        sql: str,
        result: Any,
        metadata: Dict = None,
        database_id: str = "default"
    ):
        """Add query to cache"""
        try:
            embedding = self.embedding_model.encode([question])[0]
            
            entry = {
                'question': question,
                'sql': sql,
                'result': result,
                'embedding': embedding,
                'metadata': metadata or {},
                'database_id': database_id,
                'timestamp': datetime.now().isoformat(),
                'hit_count': 0
            }
            
            self.cache_entries.append(entry)
            
            # Evict oldest entries if over max size
            if len(self.cache_entries) > self.max_size:
                self.cache_entries.sort(key=lambda x: x['hit_count'])
                self.cache_entries = self.cache_entries[-self.max_size:]
            
            self._rebuild_index()
            logger.debug(f"Added to cache: {question[:50]}...")
            
        except Exception as e:
            logger.error(f"Cache add failed: {e}")
    
    def search(
        self,
        question: str,
        database_id: str = "default",
        threshold: Optional[float] = None
    ) -> Optional[Dict]:
        """Search for similar cached queries"""
        if not self.cache_entries or self.index is None:
            return None
        
        threshold = threshold or self.similarity_threshold
        
        try:
            question_embedding = self.embedding_model.encode([question])
            
            distances, indices = self.index.search(
                question_embedding.astype('float32'), 1
            )
            
            if len(distances[0]) == 0:
                return None
            
            distance = distances[0][0]
            similarity = 1 / (1 + distance)
            
            if similarity >= threshold:
                idx = indices[0][0]
                entry = self.cache_entries[idx]
                
                # Check database_id match
                if entry.get('database_id') != database_id:
                    return None
                
                entry['hit_count'] += 1
                entry['cache_similarity'] = float(similarity)
                
                logger.info(f"Cache HIT! Similarity: {similarity:.3f}")
                return entry
            
        except Exception as e:
            logger.error(f"Cache search failed: {e}")
        
        return None
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'total_entries': len(self.cache_entries),
            'total_hits': sum(e['hit_count'] for e in self.cache_entries),
            'max_size': self.max_size,
            'similarity_threshold': self.similarity_threshold
        }
    
    def clear(self, database_id: Optional[str] = None):
        """Clear cache entries"""
        if database_id:
            self.cache_entries = [
                e for e in self.cache_entries 
                if e.get('database_id') != database_id
            ]
        else:
            self.cache_entries = []
        
        self._rebuild_index()
        logger.info(f"Cache cleared for database_id={database_id or 'all'}")
