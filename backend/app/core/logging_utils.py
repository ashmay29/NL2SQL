"""
Standardized logging utilities for consistent structured logging
"""
import logging
from typing import Optional, Dict, Any
from functools import wraps
import time


class StructuredLogger:
    """Wrapper for structured logging with consistent context"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.service_name = name.split('.')[-1]  # Extract service name
    
    def _format_context(
        self,
        conversation_id: Optional[str] = None,
        provider: Optional[str] = None,
        database_id: Optional[str] = None,
        schema_fingerprint: Optional[str] = None,
        execution_time: Optional[float] = None,
        **kwargs
    ) -> str:
        """Format context information for logging"""
        context_parts = []
        
        if conversation_id:
            context_parts.append(f"conv={conversation_id}")
        if provider:
            context_parts.append(f"provider={provider}")
        if database_id:
            context_parts.append(f"db={database_id}")
        if schema_fingerprint:
            context_parts.append(f"schema={schema_fingerprint[:8]}...")
        if execution_time is not None:
            context_parts.append(f"time={execution_time:.2f}s")
        
        # Add any additional context
        for key, value in kwargs.items():
            if value is not None:
                context_parts.append(f"{key}={value}")
        
        return f"[{' '.join(context_parts)}]" if context_parts else ""
    
    def info(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        provider: Optional[str] = None,
        database_id: Optional[str] = None,
        schema_fingerprint: Optional[str] = None,
        execution_time: Optional[float] = None,
        **kwargs
    ):
        """Log info message with structured context"""
        context = self._format_context(
            conversation_id, provider, database_id, 
            schema_fingerprint, execution_time, **kwargs
        )
        self.logger.info(f"{context} {message}")
    
    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        conversation_id: Optional[str] = None,
        provider: Optional[str] = None,
        database_id: Optional[str] = None,
        schema_fingerprint: Optional[str] = None,
        **kwargs
    ):
        """Log error message with structured context"""
        context = self._format_context(
            conversation_id, provider, database_id, 
            schema_fingerprint, **kwargs
        )
        
        if error:
            self.logger.error(f"{context} {message}: {error}", exc_info=True)
        else:
            self.logger.error(f"{context} {message}")
    
    def warning(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ):
        """Log warning message with structured context"""
        context = self._format_context(conversation_id, provider, **kwargs)
        self.logger.warning(f"{context} {message}")
    
    def debug(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        **kwargs
    ):
        """Log debug message with structured context"""
        context = self._format_context(conversation_id, **kwargs)
        self.logger.debug(f"{context} {message}")


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


def log_execution_time(
    logger: StructuredLogger,
    operation: str,
    conversation_id: Optional[str] = None,
    **context
):
    """Decorator to log execution time of functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"{operation} completed",
                    conversation_id=conversation_id,
                    execution_time=execution_time,
                    **context
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{operation} failed",
                    error=e,
                    conversation_id=conversation_id,
                    execution_time=execution_time,
                    **context
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"{operation} completed",
                    conversation_id=conversation_id,
                    execution_time=execution_time,
                    **context
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{operation} failed",
                    error=e,
                    conversation_id=conversation_id,
                    execution_time=execution_time,
                    **context
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Service-specific logger instances
llm_logger = get_logger("app.services.llm_service")
feedback_logger = get_logger("app.services.feedback_service")
context_logger = get_logger("app.services.context_service")
complexity_logger = get_logger("app.services.complexity_service")
corrector_logger = get_logger("app.services.corrector_service")
clarification_logger = get_logger("app.services.clarification_service")
pipeline_logger = get_logger("app.services.pipeline_orchestrator")
api_logger = get_logger("app.api.v1.nl2sql")
