"""
Qdrant vector database service for RAG feedback
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QdrantService:
    """Qdrant service for storing and retrieving feedback"""
    
    def __init__(self, url: str, api_key: Optional[str] = None):
        self.client = QdrantClient(url=url, api_key=api_key)
        self.feedback_collection = "nl2sql_feedback"
        self.schema_collection = "schema_embeddings"
        logger.info(f"QdrantService initialized with url={url}")
    
    async def init_collections(self, vector_dim: int = 384):
        """Initialize collections if they don't exist"""
        try:
            # Check if feedback collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.feedback_collection not in collection_names:
                self.client.create_collection(
                    collection_name=self.feedback_collection,
                    vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE)
                )
                logger.info(f"Created collection: {self.feedback_collection}")
            
            if self.schema_collection not in collection_names:
                self.client.create_collection(
                    collection_name=self.schema_collection,
                    vectors_config=VectorParams(size=512, distance=Distance.COSINE)
                )
                logger.info(f"Created collection: {self.schema_collection}")
        
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise
    
    def upsert_feedback(self, point_id: str, vector: List[float], payload: Dict[str, Any]):
        """Store feedback point"""
        try:
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            self.client.upsert(
                collection_name=self.feedback_collection,
                points=[point]
            )
            logger.info(f"Upserted feedback point: {point_id}")
        except Exception as e:
            logger.error(f"Failed to upsert feedback: {e}")
            raise
    
    def search_similar(
        self,
        vector: List[float],
        schema_fingerprint: str,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar queries"""
        try:
            results = self.client.search(
                collection_name=self.feedback_collection,
                query_vector=vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="schema_fingerprint",
                            match=MatchValue(value=schema_fingerprint)
                        )
                    ]
                ),
                limit=limit,
                score_threshold=score_threshold
            )
            
            return [
                {
                    "id": r.id,
                    "score": r.score,
                    **r.payload
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Failed to search similar: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
