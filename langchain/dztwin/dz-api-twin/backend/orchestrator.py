from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
from ai_provider import create_provider, BaseAIProvider
from rag_service import RAGService
from config import get_config
from logger import logger


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
        self.conversations: Dict[str, List[Dict]] = {}
    
    def create_conversation(self, conversation_id: str) -> Dict:
        self.conversations[conversation_id] = []
        return {
            "conversation_id": conversation_id,
            "created_at": datetime.utcnow().isoformat(),
            "message_count": 0
        }
    
    def get_conversation(self, conversation_id: str) -> Optional[List[Dict]]:
        return self.conversations.get(conversation_id)
    
    def add_message(self, conversation_id: str, role: str, content: str) -> Dict:
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.conversations[conversation_id].append(message)
        return message
    
    async def stream_chat_response(
        self, 
        conversation_id: str, 
        user_message: str
    ) -> AsyncGenerator[str, None]:
        # Add user message
        self.add_message(conversation_id, "user", user_message)
        
        # Get conversation history
        messages = self.conversations.get(conversation_id, [])
        
        # RAG search if enabled
        context = None
        if self.rag_service.enabled:
            context = await self.rag_service.search(user_message)
        
        # Log LLM request if enabled
        if self.config.LOG_LLM_REQUESTS:
            logger.info("=" * 80)
            logger.info(f"LLM REQUEST - Conversation: {conversation_id}")
            logger.info(f"User message: {user_message}")
            logger.info(f"Conversation history length: {len(messages)} messages")
            if context:
                logger.info(f"RAG context provided: {len(context)} characters")
                logger.debug(f"Full RAG context:\n{context}")
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
            logger.info(f"Full response:\n{full_response}")
            logger.info("=" * 80)
        
        # Save assistant message
        self.add_message(conversation_id, "assistant", full_response)


_orchestrator = None

def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
