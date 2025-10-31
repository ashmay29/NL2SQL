"""
Feedback service for RAG-based query improvement
"""
from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime
from app.services.qdrant_service import QdrantService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for storing and retrieving user feedback"""
    
    def __init__(
        self,
        qdrant_service: QdrantService,
        embedding_service: EmbeddingService
    ):
        self.qdrant = qdrant_service
        self.embeddings = embedding_service
        logger.info("FeedbackService initialized")
    
    async def submit_feedback(
        self,
        query_text: str,
        generated_sql: str,
        corrected_sql: str,
        schema_fingerprint: str,
        database: str = "nl2sql_target",
        tables_used: List[str] = None,
        correction_reason: str = "",
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Submit user feedback (correction or success confirmation)
        Returns: feedback_id
        """
        try:
            # Generate embedding for query
            vector = await self.embeddings.embed_query(query_text)
            
            # Create feedback point
            feedback_id = str(uuid.uuid4())
            payload = {
                "query_text": query_text,
                "schema_fingerprint": schema_fingerprint,
                "database": database,
                "original_sql": generated_sql,
                "corrected_sql": corrected_sql,
                "correction_reason": correction_reason,
                "involved_tables": tables_used or [],
                "feedback_type": "correction" if generated_sql != corrected_sql else "success",
                "timestamp": datetime.utcnow().isoformat(),
                "upvotes": 0,
                "metadata": metadata or {}
            }
            
            # Store in Qdrant
            self.qdrant.upsert_feedback(feedback_id, vector, payload)
            
            logger.info(f"Feedback submitted: {feedback_id} for query: {query_text[:50]}...")
            return feedback_id
        
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            raise
    
    async def get_similar_queries(
        self,
        query_text: str,
        schema_fingerprint: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar past queries for RAG augmentation
        Returns: List of similar query examples with scores
        """
        try:
            # Generate embedding for query
            vector = await self.embeddings.embed_query(query_text)
            
            # Search in Qdrant
            results = self.qdrant.search_similar(
                vector=vector,
                schema_fingerprint=schema_fingerprint,
                limit=top_k,
                score_threshold=score_threshold
            )
            
            logger.info(f"Found {len(results)} similar queries for: {query_text[:50]}...")
            return results
        
        except Exception as e:
            logger.error(f"Failed to retrieve similar queries: {e}")
            return []
    
    async def build_rag_examples(
        self,
        query_text: str,
        schema_fingerprint: str,
        max_examples: int = 3
    ) -> str:
        """
        Build RAG examples string for prompt augmentation
        Returns: Formatted examples string
        """
        try:
            similar = await self.get_similar_queries(
                query_text,
                schema_fingerprint,
                top_k=max_examples,
                score_threshold=0.75
            )
            
            if not similar:
                return ""
            
            examples = []
            for i, item in enumerate(similar, 1):
                # Use corrected SQL if available, otherwise original
                sql = item.get("corrected_sql") or item.get("original_sql")
                examples.append(
                    f"Example {i} (similarity: {item['score']:.2f}):\n"
                    f"Query: {item['query_text']}\n"
                    f"SQL: {sql}\n"
                )
            
            return "\n".join(examples)
        
        except Exception as e:
            logger.error(f"Failed to build RAG examples: {e}")
            return ""
    
    async def upvote_feedback(self, feedback_id: str) -> bool:
        """Increment upvote count for a feedback entry"""
        try:
            # Retrieve existing point
            point = self.qdrant.client.retrieve(
                collection_name=self.qdrant.feedback_collection,
                ids=[feedback_id]
            )
            
            if not point:
                logger.warning(f"Feedback not found: {feedback_id}")
                return False
            
            # Update upvotes
            payload = point[0].payload
            payload["upvotes"] = payload.get("upvotes", 0) + 1
            
            # Re-upsert with same vector
            self.qdrant.upsert_feedback(
                feedback_id,
                point[0].vector,
                payload
            )
            
            logger.info(f"Upvoted feedback: {feedback_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to upvote feedback: {e}")
            return False
