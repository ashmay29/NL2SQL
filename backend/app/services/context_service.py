"""
Context service for multi-turn conversation management
"""
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConversationTurn:
    """Single conversation turn"""
    def __init__(
        self,
        query: str,
        sql: str,
        ir: Dict[str, Any],
        timestamp: datetime,
        tables_used: List[str] = None
    ):
        self.query = query
        self.sql = sql
        self.ir = ir
        self.timestamp = timestamp
        self.tables_used = tables_used or []


class ContextService:
    """Service for managing conversation context"""
    
    def __init__(self, redis_client, max_turns: int = 5, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds
        logger.info(f"ContextService initialized with max_turns={max_turns}, ttl={ttl_seconds}s")
    
    def _get_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation"""
        return f"context:{conversation_id}"
    
    def add_turn(
        self,
        conversation_id: str,
        query: str,
        sql: str,
        ir: Dict[str, Any],
        tables_used: List[str] = None
    ):
        """Add a turn to conversation history"""
        try:
            key = self._get_key(conversation_id)
            
            # Get existing history
            history_json = self.redis.get(key)
            history = json.loads(history_json) if history_json else []
            
            # Add new turn
            turn = {
                "query": query,
                "sql": sql,
                "ir": ir,
                "timestamp": datetime.utcnow().isoformat(),
                "tables_used": tables_used or []
            }
            history.append(turn)
            
            # Keep only last N turns
            if len(history) > self.max_turns:
                history = history[-self.max_turns:]
            
            # Store back
            self.redis.setex(
                key,
                self.ttl_seconds,
                json.dumps(history)
            )
            
            logger.debug(f"Added turn to conversation {conversation_id}: {query[:50]}...")
        
        except Exception as e:
            logger.error(f"Failed to add turn: {e}")
    
    def get_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history"""
        try:
            key = self._get_key(conversation_id)
            history_json = self.redis.get(key)
            
            if not history_json:
                return []
            
            history = json.loads(history_json)
            logger.debug(f"Retrieved {len(history)} turns for conversation {conversation_id}")
            return history
        
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    def get_recent_tables(self, conversation_id: str, n: int = 3) -> List[str]:
        """Get tables used in recent turns"""
        try:
            history = self.get_history(conversation_id)
            
            # Collect tables from recent turns
            tables = set()
            for turn in reversed(history[-n:]):
                tables.update(turn.get("tables_used", []))
            
            return list(tables)
        
        except Exception as e:
            logger.error(f"Failed to get recent tables: {e}")
            return []
    
    def build_context_prompt(self, conversation_id: str, max_turns: int = 3) -> str:
        """Build context string for prompt augmentation"""
        try:
            history = self.get_history(conversation_id)
            
            if not history:
                return ""
            
            # Take last N turns
            recent = history[-max_turns:]
            
            context_lines = ["Previous conversation:"]
            for i, turn in enumerate(recent, 1):
                context_lines.append(
                    f"{i}. User: {turn['query']}\n"
                    f"   SQL: {turn['sql']}"
                )
            
            return "\n".join(context_lines)
        
        except Exception as e:
            logger.error(f"Failed to build context prompt: {e}")
            return ""
    
    def resolve_references(
        self,
        query: str,
        conversation_id: str
    ) -> str:
        """
        Resolve pronouns and references in query using context
        Examples:
        - "Show me the same for products" -> references previous table
        - "What about their orders?" -> "their" refers to previous entities
        """
        try:
            history = self.get_history(conversation_id)
            
            if not history:
                return query
            
            # Simple reference resolution
            last_turn = history[-1] if history else None
            
            if not last_turn:
                return query
            
            # Check for reference keywords
            reference_keywords = ["same", "those", "them", "their", "that", "it"]
            query_lower = query.lower()
            
            has_reference = any(kw in query_lower for kw in reference_keywords)
            
            if has_reference:
                # Add context hint
                last_tables = last_turn.get("tables_used", [])
                if last_tables:
                    resolved = f"{query} (referring to previous query about {', '.join(last_tables)})"
                    logger.info(f"Resolved reference: {query} -> {resolved}")
                    return resolved
            
            return query
        
        except Exception as e:
            logger.error(f"Failed to resolve references: {e}")
            return query
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation history"""
        try:
            key = self._get_key(conversation_id)
            self.redis.delete(key)
            logger.info(f"Cleared conversation: {conversation_id}")
        
        except Exception as e:
            logger.error(f"Failed to clear conversation: {e}")
