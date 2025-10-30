"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import health, schema, embeddings, nl2sql
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="NL2SQL API",
    description="Advanced Natural Language to SQL system with GNN schema linking and RAG feedback",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(schema.router, prefix="/api/v1", tags=["Schema"])
app.include_router(embeddings.router, prefix="/api/v1", tags=["Embeddings"])
app.include_router(nl2sql.router, prefix="/api/v1", tags=["NL2SQL"])

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("=" * 60)
    logger.info("NL2SQL API Starting")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("NL2SQL API Shutting down")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "NL2SQL API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.APP_ENV == "development" else False
    )
