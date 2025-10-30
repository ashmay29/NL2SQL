"""
GNN Embedding ingestion API
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_redis_client
from app.services.gnn_embedding_service import GNNEmbeddingService
from app.models.schemas import EmbeddingPullRequest, EmbeddingUploadResponse
import redis
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_gnn_service(redis_client: redis.Redis = Depends(get_redis_client)) -> GNNEmbeddingService:
    return GNNEmbeddingService(redis_client)


@router.post("/schema/embeddings/pull", response_model=EmbeddingUploadResponse)
async def pull_embeddings(req: EmbeddingPullRequest, service: GNNEmbeddingService = Depends(get_gnn_service)):
    try:
        meta = service.pull_from_url(req.schema_fingerprint, req.url)
        return EmbeddingUploadResponse(
            schema_fingerprint=meta["schema_fingerprint"],
            nodes_count=meta["count"],
            dim=meta["dim"],
            message="Embeddings pulled and cached"
        )
    except Exception as e:
        logger.error(f"Embedding pull failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/schema/embeddings/upload", response_model=EmbeddingUploadResponse)
async def upload_embeddings(payload: dict, service: GNNEmbeddingService = Depends(get_gnn_service)):
    try:
        meta = service.upload_embeddings(payload)
        return EmbeddingUploadResponse(
            schema_fingerprint=meta["schema_fingerprint"],
            nodes_count=meta["count"],
            dim=meta["dim"],
            message="Embeddings uploaded and cached"
        )
    except Exception as e:
        logger.error(f"Embedding upload failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
