"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_ENV: str = "development"
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_MIN: int = 30
    LOG_LEVEL: str = "INFO"
    
    # Databases
    MYSQL_URI: str
    APP_DB_URI: str
    REDIS_URI: str
    
    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    
    # LLM Providers
    LLM_PROVIDER: str = "ollama"  # ollama | gemini
    OLLAMA_ENDPOINT: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:latest"
    USE_GEMINI_FOR_FEEDBACK: bool = True
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Limits
    MAX_QUERY_ROWS: int = 10000
    QUERY_TIMEOUT_MS: int = 30000
    RATE_LIMIT_PER_MIN: int = 60
    
    # Schema
    SCHEMA_REFRESH_TTL_SEC: int = 3600
    SCHEMA_DIFF_STRATEGY: str = "fingerprint"
    
    # Features
    IR_ADVANCED_FEATURES_ENABLED: bool = True
    CLARIFY_CONFIDENCE_THRESHOLD: float = 0.7
    CLARIFY_MAX_TURNS: int = 3
    ERROR_EXPLAIN_VERBOSE: bool = True
    CACHE_SIMILARITY_THRESHOLD: float = 0.85
    MAX_CACHE_SIZE: int = 1000
    MAX_CONTEXT_TURNS: int = 5
    
    # Optional: Kaggle
    KAGGLE_USERNAME: Optional[str] = None
    KAGGLE_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
