"""
LLM service supporting Ollama and Gemini
"""
import requests
import json
from typing import Dict, Any, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Unified LLM service for Ollama and Gemini"""
    
    def __init__(
        self,
        provider: str = "ollama",
        ollama_endpoint: str = "http://localhost:11434",
        ollama_model: str = "mistral:latest",
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash"
    ):
        self.provider = provider
        self.ollama_endpoint = ollama_endpoint
        self.ollama_model = ollama_model
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        
        logger.info(f"LLMService initialized with provider={provider}")
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        provider_override: Optional[str] = None
    ) -> str:
        """Generate text from LLM"""
        provider = provider_override or self.provider
        
        if provider == "ollama":
            return self._generate_ollama(prompt, temperature, max_tokens)
        elif provider == "gemini":
            return self._generate_gemini(prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _generate_ollama(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Ollama"""
        try:
            url = f"{self.ollama_endpoint}/api/generate"
            # Ollama API expects num_predict (not max_tokens) and can accept options.num_ctx.
            # Large schema prompts can overflow default context; set a higher num_ctx.
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "num_predict": max(32, min(getattr(settings, 'OLLAMA_NUM_PREDICT', 128), 512)),
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": int(getattr(settings, 'OLLAMA_NUM_CTX', 4096))
                }
            }
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            # Improve error context to aid debugging (e.g., 500 due to context overflow)
            logger.error(f"Ollama generation failed: {e}\nEndpoint={self.ollama_endpoint} Model={self.ollama_model}")
            raise
    
    def _generate_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Gemini API"""
        if not self.gemini_api_key:
            raise ValueError("Gemini API key not configured")
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(self.gemini_model)
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    def generate_json(
        self,
        prompt: str,
        provider_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate JSON response (for IR generation)"""
        provider = provider_override or self.provider
        # Prefer Ollama chat API with format=json to force valid JSON
        if provider == "ollama":
            try:
                json_text = self._ollama_chat_json(prompt)
                return json.loads(json_text)
            except Exception as e:
                logger.error(f"Ollama chat/json failed, falling back to generate: {e}")
                # Fall through to text generation + extraction

        response_text = self.generate(
            prompt,
            temperature=0.3,  # Lower temperature for structured output
            provider_override=provider_override
        )
        
        # Extract JSON from response
        try:
            # Try to parse directly
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find any JSON object
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            raise ValueError(f"Could not extract JSON from response: {response_text[:200]}")

    def _ollama_chat_json(self, prompt: str) -> str:
        """Use Ollama chat API with format=json to force JSON-only output."""
        try:
            url = f"{self.ollama_endpoint}/api/chat"
            payload = {
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": "You return only valid JSON without any extra text."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_ctx": int(getattr(settings, 'OLLAMA_NUM_CTX', 4096)),
                    "num_predict": max(32, min(getattr(settings, 'OLLAMA_NUM_PREDICT', 128), 512))
                }
            }
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            # Ollama chat returns { message: { content: "..." } }
            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama chat API failed: {e}\nEndpoint={self.ollama_endpoint} Model={self.ollama_model}")
            raise
