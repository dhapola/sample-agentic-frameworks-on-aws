from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
import re
from orchestrator import get_orchestrator
from config import get_config
from logger import logger
from sanitizer import sanitize_error_message

app = FastAPI(title="AI Chat Widget API", version="1.0.0")
logger.info("Starting AI Chat Widget API")

# CORS
config = get_config()
logger.info(f"Configuring CORS with origins: {config.CORS_ORIGINS}")
logger.info(f"AI Provider: {config.AI_PROVIDER}")
if config.RAG_ENABLED:
    logger.info(f"RAG enabled with collection: {config.QDRANT_COLLECTION}")


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking (allow iframe embedding for widget)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    
    # XSS Protection (legacy but still useful)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions Policy (restrict features)
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # HSTS (only in production with HTTPS)
    # Uncomment when running on HTTPS in production
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    conversation_id: Optional[str] = Field(None, pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', description="UUID v4 conversation ID")
    
    @validator('message')
    def sanitize_message(cls, v):
        # Remove control characters except newlines, tabs, carriage returns
        v = ''.join(char for char in v if char.isprintable() or char in '\n\r\t')
        
        # Check for potential prompt injection patterns
        suspicious_patterns = [
            'ignore previous',
            'ignore all previous',
            'disregard previous',
            'forget previous',
            'system:',
            'assistant:',
            '<|im_start|>',
            '<|im_end|>',
            '[INST]',
            '[/INST]'
        ]
        
        lower_message = v.lower()
        for pattern in suspicious_patterns:
            if pattern in lower_message:
                logger.warning(f"Potential prompt injection detected: {pattern}")
                # Don't block, but log for monitoring
                break
        
        return v.strip()
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        if v is None:
            return v
        # Additional validation beyond regex
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("Invalid conversation ID format")
        return v


class ConversationResponse(BaseModel):
    conversation_id: str
    created_at: str
    message_count: int


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str


@app.get("/")
async def root():
    return {"message": "AI Chat Widget API", "version": "1.0.0"}


@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation():
    orchestrator = get_orchestrator()
    conversation_id = str(uuid.uuid4())
    logger.info(f"Creating new conversation: {conversation_id}")
    conversation = orchestrator.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=List[MessageResponse])
async def get_conversation(conversation_id: str):
    orchestrator = get_orchestrator()
    logger.debug(f"Fetching conversation: {conversation_id}")
    messages = orchestrator.get_conversation(conversation_id)
    
    if messages is None:
        logger.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return messages


@app.post("/api/chat")
async def chat(request: ChatRequest):
    orchestrator = get_orchestrator()
    
    # Create conversation if not provided
    conversation_id = request.conversation_id or str(uuid.uuid4())
    logger.info(f"Chat request - conversation: {conversation_id}, message length: {len(request.message)}")
    
    async def event_generator():
        try:
            async for chunk in orchestrator.stream_chat_response(conversation_id, request.message):
                # Escape newlines for SSE protocol - they'll be unescaped on the client
                escaped_chunk = chunk.replace('\n', '\\n').replace('\r', '\\r')
                yield f"data: {escaped_chunk}\n\n"
            logger.info(f"Chat response completed for conversation: {conversation_id}")
            yield f"event: done\ndata: {conversation_id}\n\n"
        except Exception as e:
            logger.error(f"Chat error for conversation {conversation_id}: {str(e)}", exc_info=True)
            # Send sanitized error message to client
            safe_error = sanitize_error_message(e)
            yield f"event: error\ndata: {safe_error}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Content-Type-Options": "nosniff",
        }
    )


@app.get("/api/health")
async def health():
    return {"status": "healthy", "provider": config.AI_PROVIDER}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {config.API_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=config.API_PORT)
