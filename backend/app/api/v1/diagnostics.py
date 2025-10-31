"""
Diagnostic endpoints for troubleshooting
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_llm_service, get_schema_service
from app.services.llm_service import LLMService
from app.services.schema_service import SchemaService
import requests
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/diagnostics/llm")
async def check_llm(llm: LLMService = Depends(get_llm_service)):
    """Check LLM connectivity"""
    try:
        # Test Ollama
        if llm.provider == "ollama":
            response = requests.get(f"{llm.ollama_endpoint}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "provider": "ollama",
                    "status": "healthy",
                    "endpoint": llm.ollama_endpoint,
                    "configured_model": llm.ollama_model,
                    "available_models": [m.get("name") for m in models]
                }
            else:
                return {
                    "provider": "ollama",
                    "status": "unhealthy",
                    "error": f"Status code: {response.status_code}"
                }
        
        # Test Gemini
        elif llm.provider == "gemini":
            if not llm.gemini_api_key:
                return {
                    "provider": "gemini",
                    "status": "unhealthy",
                    "error": "API key not configured"
                }
            return {
                "provider": "gemini",
                "status": "configured",
                "model": llm.gemini_model
            }
        
        return {"provider": llm.provider, "status": "unknown"}
    
    except Exception as e:
        logger.error(f"LLM diagnostic failed: {e}")
        return {
            "provider": llm.provider,
            "status": "error",
            "error": str(e)
        }


@router.get("/diagnostics/schema")
async def check_schema(schema_service: SchemaService = Depends(get_schema_service)):
    """Check schema service"""
    try:
        schema = schema_service.get_cached_schema("nl2sql_target")
        if schema:
            return {
                "status": "cached",
                "database": schema.get("database"),
                "version": schema.get("version", "")[:12],
                "tables": len(schema.get("tables", {}))
            }
        
        # Try to extract
        schema = schema_service.extract_schema("nl2sql_target")
        return {
            "status": "extracted",
            "database": schema.get("database"),
            "version": schema.get("version", "")[:12],
            "tables": len(schema.get("tables", {}))
        }
    
    except Exception as e:
        logger.error(f"Schema diagnostic failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/diagnostics/test-llm")
async def test_llm_generation(llm: LLMService = Depends(get_llm_service)):
    """Test LLM generation with simple prompt"""
    try:
        prompt = "Return only valid JSON: {\"test\": \"success\", \"number\": 42}"
        result = llm.generate_json(prompt)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.error(f"LLM test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
