"""
LLM service supporting Ollama and Gemini
"""
import requests
import json
import time
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
        max_tokens: int = 10000,
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
            from google.api_core import exceptions as gcore_exceptions
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(
                self.gemini_model
            )
            # Simple retry with exponential backoff for rate limits
            attempts = int(getattr(settings, 'GEMINI_MAX_RETRIES', 3))
            backoff_base = float(getattr(settings, 'GEMINI_BACKOFF_BASE_SEC', 1.0))
            last_err = None
            for i in range(attempts):
                try:
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                            "candidate_count": 1,  # Only generate one candidate
                            "stop_sequences": None   # Don't stop early
                        }
                    )
                    
                    # Handle multi-part responses - use the EXACT path Gemini tells us
                    try:
                        # Try simple accessor first
                        return response.text.strip()
                    except (ValueError, AttributeError) as ve:
                        # Multi-part response - use candidates[index].content.parts as error message says
                        logger.warning(f"⚠️  Multi-part response detected, extracting parts...")
                        
                        # First check if response was blocked or incomplete
                        if response.candidates and len(response.candidates) > 0:
                            candidate = response.candidates[0]
                            
                            # Log finish reason to understand why response is multi-part
                            finish_reason = getattr(candidate, 'finish_reason', None)
                            logger.info(f"Finish reason: {finish_reason}")
                            
                            # Check safety ratings
                            if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                                logger.info(f"Safety ratings: {candidate.safety_ratings}")
                            
                            # Check if blocked
                            if hasattr(response, 'prompt_feedback'):
                                logger.info(f"Prompt feedback: {response.prompt_feedback}")
                        
                        try:
                            # Use EXACTLY what the error message says: result.candidates[index].content.parts
                            parts = response.candidates[0].content.parts
                            logger.info(f"Found {len(parts)} parts")
                            
                            # Debug: log what's in each part
                            for i, part in enumerate(parts):
                                logger.info(f"Part {i}: type={type(part)}, has_text={hasattr(part, 'text')}, text_len={len(part.text) if hasattr(part, 'text') and part.text else 0}")
                            
                            text_parts = [part.text for part in parts if hasattr(part, 'text') and part.text]
                            
                            if text_parts:
                                combined = ''.join(text_parts).strip()
                                logger.info(f"✅ Extracted {len(text_parts)} parts → {len(combined)} chars")
                                return combined
                            else:
                                logger.error(f"❌ No text in {len(parts)} parts")
                                # Log what's actually in the parts
                                for i, part in enumerate(parts):
                                    logger.error(f"Part {i} attributes: {dir(part)[:10]}")
                                raise RuntimeError(f"Parts exist but contain no extractable text. Finish reason: {finish_reason if 'finish_reason' in locals() else 'unknown'}")
                                
                        except (AttributeError, IndexError, TypeError) as e:
                            logger.error(f"❌ Cannot access parts: {e}")
                            logger.error(f"Response: {type(response)}, Has candidates: {hasattr(response, 'candidates')}")
                            raise RuntimeError(f"Failed to extract multi-part response: {e}")
                        
                except gcore_exceptions.ResourceExhausted as e:
                    last_err = e
                    sleep_sec = backoff_base * (2 ** i)
                    logger.warning(f"Gemini 429 Resource exhausted, retrying in {sleep_sec:.1f}s (attempt {i+1}/{attempts})")
                    time.sleep(sleep_sec)
                except gcore_exceptions.TooManyRequests as e:  # pragma: no cover (alias in some versions)
                    last_err = e
                    sleep_sec = backoff_base * (2 ** i)
                    logger.warning(f"Gemini 429 TooManyRequests, retrying in {sleep_sec:.1f}s (attempt {i+1}/{attempts})")
                    time.sleep(sleep_sec)
            # Exhausted retries
            raise last_err if last_err else RuntimeError("Gemini generation failed without specific error")
            
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

        # Generate text with the selected provider (with retries already inside Gemini path)
        try:
            response_text = self.generate(
                prompt,
                temperature=0.3,  # Lower temperature for structured output
                provider_override=provider_override
            )
        except Exception as e:
            logger.error(f"Primary provider '{provider}' failed to generate JSON: {e}")
            # Optional fallback to Ollama if configured and not already using it
            fallback = getattr(settings, 'LLM_FALLBACK_PROVIDER', None)
            if provider != "ollama" and fallback == "ollama":
                logger.info("Falling back to Ollama for JSON generation")
                try:
                    json_text = self._ollama_chat_json(prompt)
                    return json.loads(json_text)
                except Exception as fe:
                    logger.error(f"Fallback Ollama chat/json failed: {fe}")
                    # last resort: try Ollama text and extract
                    try:
                        response_text = self._generate_ollama(prompt, temperature=0.1, max_tokens=2048)
                    except Exception:
                        raise e  # re-raise original
            else:
                # No fallback configured
                raise

        # Extract JSON from response
        try:
            # Try to parse directly
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find any JSON object
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
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
