from typing import Dict, List, Optional, AsyncGenerator, Tuple
from datetime import datetime, timedelta
from ai_provider import create_provider, BaseAIProvider
from rag_service import RAGService
from config import get_config
from logger import logger
from sanitizer import sanitize_for_logging


class Orchestrator:
    def __init__(self):
        self.config = get_config()
        try:
            self.provider: BaseAIProvider = create_provider(self.config)
            logger.info(f"AI provider '{self.config.AI_PROVIDER}' initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI provider: {e}", exc_info=True)
            raise
        
        self.rag_service = RAGService(self.config)
        # Store conversations with timestamp: {conv_id: (messages, created_at, last_accessed)}
        self.conversations: Dict[str, Tuple[List[Dict], datetime, datetime]] = {}
        self.session_ttl = timedelta(hours=24)  # 24 hour session timeout
        self.cleanup_interval = timedelta(hours=1)  # Cleanup every hour
        self.last_cleanup = datetime.utcnow()
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions to prevent memory leaks"""
        now = datetime.utcnow()
        
        # Only run cleanup if interval has passed
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        expired = [
            conv_id for conv_id, (_, _, last_accessed) in self.conversations.items()
            if now - last_accessed > self.session_ttl
        ]
        
        for conv_id in expired:
            del self.conversations[conv_id]
            logger.info(f"Cleaned up expired session: {conv_id}")
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        self.last_cleanup = now
    
    def create_conversation(self, conversation_id: str) -> Dict:
        self._cleanup_expired_sessions()
        
        now = datetime.utcnow()
        self.conversations[conversation_id] = ([], now, now)
        logger.info(f"Created conversation: {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "created_at": now.isoformat(),
            "message_count": 0
        }
    
    def get_conversation(self, conversation_id: str) -> Optional[List[Dict]]:
        self._cleanup_expired_sessions()
        
        if conversation_id not in self.conversations:
            return None
        
        messages, created_at, _ = self.conversations[conversation_id]
        
        # Update last accessed time
        now = datetime.utcnow()
        self.conversations[conversation_id] = (messages, created_at, now)
        
        return messages
    
    def add_message(self, conversation_id: str, role: str, content: str) -> Dict:
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        messages, created_at, _ = self.conversations[conversation_id]
        messages.append(message)
        
        # Update last accessed time
        now = datetime.utcnow()
        self.conversations[conversation_id] = (messages, created_at, now)
        
        return message
    
    async def stream_chat_response(
        self, 
        conversation_id: str, 
        user_message: str
    ) -> AsyncGenerator[str, None]:
        # Add user message
        self.add_message(conversation_id, "user", user_message)
        
        # Get conversation history (extract messages from tuple)
        conversation_data = self.conversations.get(conversation_id)
        messages = conversation_data[0] if conversation_data else []
        
        # RAG search if enabled
        context = None
        if self.rag_service.enabled:
            context = await self.rag_service.search(user_message)
        
        # Log LLM request if enabled
        if self.config.LOG_LLM_REQUESTS:
            logger.info("=" * 80)
            logger.info(f"LLM REQUEST - Conversation: {conversation_id}")
            logger.info(f"User message: {sanitize_for_logging(user_message)}")
            logger.info(f"Conversation history length: {len(messages)} messages")
            if context:
                logger.info(f"RAG context provided: {len(context)} characters")
                logger.debug(f"RAG context preview: {sanitize_for_logging(context, max_length=500)}")
            else:
                logger.info("No RAG context provided")
            logger.info("-" * 80)
        
        # Stream AI response
        full_response = ""
        async for chunk in self.provider.stream_response(messages, context):
            full_response += chunk
            yield chunk
        
        # Log LLM response if enabled
        if self.config.LOG_LLM_REQUESTS:
            logger.info(f"LLM RESPONSE - Conversation: {conversation_id}")
            logger.info(f"Response length: {len(full_response)} characters")
            logger.info(f"Response preview: {sanitize_for_logging(full_response, max_length=500)}")
            logger.info("=" * 80)
        
        # Save assistant message
        self.add_message(conversation_id, "assistant", full_response)


_orchestrator = None

def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
