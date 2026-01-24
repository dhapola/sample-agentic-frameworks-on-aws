from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
from orchestrator import get_orchestrator
from config import get_config
from logger import logger

app = FastAPI(title="AI Chat Widget API", version="1.0.0")
logger.info("Starting AI Chat Widget API")

# CORS
config = get_config()
logger.info(f"Configuring CORS with origins: {config.CORS_ORIGINS}")
logger.info(f"AI Provider: {config.AI_PROVIDER}")
if config.RAG_ENABLED:
    logger.info(f"RAG enabled with collection: {config.QDRANT_COLLECTION}")
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


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
                yield f"data: {chunk}\n\n"
            logger.info(f"Chat response completed for conversation: {conversation_id}")
            yield f"event: done\ndata: {conversation_id}\n\n"
        except Exception as e:
            logger.error(f"Chat error for conversation {conversation_id}: {str(e)}", exc_info=True)
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/health")
async def health():
    return {"status": "healthy", "provider": config.AI_PROVIDER}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {config.API_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=config.API_PORT)
