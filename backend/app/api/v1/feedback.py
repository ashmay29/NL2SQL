"""
Feedback API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import (
    FeedbackSubmit,
    FeedbackResponse,
    FeedbackSimilarRequest,
    FeedbackSimilarResponse
)
from app.core.dependencies import get_feedback_service
from app.services.feedback_service import FeedbackService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackSubmit,
    feedback_service: FeedbackService = Depends(get_feedback_service)
):
    """Submit user feedback (correction or confirmation)"""
    try:
        feedback_id = await feedback_service.submit_feedback(
            query_text=req.query_text,
            generated_sql=req.generated_sql,
            corrected_sql=req.corrected_sql,
            schema_fingerprint=req.schema_fingerprint,
            tables_used=req.tables_used,
            metadata=req.metadata
        )
        
        return FeedbackResponse(
            id=feedback_id,
            message="Feedback submitted successfully"
        )
    
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/similar", response_model=FeedbackSimilarResponse)
async def get_similar_feedback(
    req: FeedbackSimilarRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service)
):
    """Get similar past queries for reference"""
    try:
        results = await feedback_service.get_similar_queries(
            query_text=req.query,
            schema_fingerprint=req.schema_fingerprint or "default",
            top_k=req.top_k
        )
        
        return FeedbackSimilarResponse(results=results)
    
    except Exception as e:
        logger.error(f"Failed to get similar feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/{feedback_id}/upvote")
async def upvote_feedback(
    feedback_id: str,
    feedback_service: FeedbackService = Depends(get_feedback_service)
):
    """Upvote a feedback entry"""
    try:
        success = await feedback_service.upvote_feedback(feedback_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        return {"message": "Feedback upvoted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upvote feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
