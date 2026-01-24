# Chat Widget Backend

FastAPI backend with LangChain integration for multiple AI providers and RAG support.

## Features

- **Multiple AI providers** - Bedrock, OpenAI, Anthropic, Gemini, Azure OpenAI, Cohere
- **LangChain integration** - Unified interface across all providers
- **Streaming responses** - Server-Sent Events (SSE) for real-time streaming
- **RAG support** - Semantic search with Qdrant vector database
- **Conversation memory** - Context-aware multi-turn conversations
- **Auto-generated docs** - Swagger UI and ReDoc
- **Structured logging** - Configurable logging with LLM request/response tracking
- **CORS support** - Configurable cross-origin resource sharing

## Quick Setup

```bash
./start.sh  # Unix/macOS
# or
start.bat   # Windows
```

This will:
1. Create virtual environment (if needed)
2. Install dependencies
3. Copy `.env.example` to `.env` (if needed)
4. Start the server on port 3000

## Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start server
python main.py
```

## Configuration

### Environment Variables

Create `.env` file (copy from `.env.example`):

```env
# AI Provider Selection
AI_PROVIDER=bedrock  # bedrock, openai, anthropic, gemini, azure, cohere

# AWS Bedrock (Default)
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Google Gemini
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# RAG Configuration
RAG_ENABLED=false
QDRANT_URL=http://localhost:6333  # Leave empty for embedded mode
QDRANT_COLLECTION=api_docs
RAG_TOP_K=5  # Number of relevant documents to retrieve

# Server Configuration
API_PORT=3000
CORS_ORIGINS=*  # Comma-separated list of allowed origins

# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=  # Optional: path to log file (logs/app.log)
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_LLM_REQUESTS=false  # Enable detailed LLM request/response logging
```

## Supported AI Providers

### AWS Bedrock (Default)
Uses AWS credentials from environment or IAM role.

```env
AI_PROVIDER=bedrock
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
```

**Supported Models:**
- `anthropic.claude-3-5-sonnet-20241022-v2:0` (Recommended)
- `anthropic.claude-3-5-haiku-20241022-v1:0`
- `anthropic.claude-3-opus-20240229-v1:0`
- `meta.llama3-1-70b-instruct-v1:0`
- `mistral.mistral-large-2402-v1:0`

### OpenAI
```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Supported Models:**
- `gpt-4o` - Most capable
- `gpt-4o-mini` - Fast and cost-effective
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### Anthropic
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**Supported Models:**
- `claude-3-5-sonnet-20241022` (Recommended)
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`

### Google Gemini
```env
AI_PROVIDER=gemini
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash
```

**Supported Models:**
- `gemini-1.5-pro` - Most capable
- `gemini-1.5-flash` - Fast and efficient
- `gemini-1.0-pro`

### Azure OpenAI
```env
AI_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Cohere
```env
AI_PROVIDER=cohere
COHERE_API_KEY=...
COHERE_MODEL=command-r-plus
```

## API Endpoints

### Core Endpoints

#### `GET /`
API information and version.

**Response:**
```json
{
  "message": "AI Chat Widget API",
  "version": "1.0.0"
}
```

#### `POST /api/conversations`
Create a new conversation.

**Response:**
```json
{
  "conversation_id": "uuid",
  "created_at": "2024-01-01T00:00:00",
  "message_count": 0
}
```

#### `GET /api/conversations/{conversation_id}`
Get conversation history.

**Response:**
```json
[
  {
    "role": "user",
    "content": "Hello",
    "timestamp": "2024-01-01T00:00:00"
  },
  {
    "role": "assistant",
    "content": "Hi! How can I help?",
    "timestamp": "2024-01-01T00:00:01"
  }
]
```

#### `POST /api/chat`
Send a message and receive streaming response.

**Request:**
```json
{
  "message": "What is your API?",
  "conversation_id": "uuid"  // Optional
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: What
data:  is
data:  your
data:  API
data: ?
event: done
data: conversation-id-uuid
```

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "provider": "bedrock"
}
```

### API Documentation

Interactive API documentation available when server is running:

- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc

## RAG (Retrieval-Augmented Generation)

### Setup

1. **Crawl and ingest documentation** (see [api-doc-indexer](../api-doc-indexer/))
   ```bash
   cd ../api-doc-indexer/crawler
   python crawler.py
   
   cd ../ingester
   python ingest.py
   ```

2. **Enable RAG in backend**
   ```env
   RAG_ENABLED=true
   QDRANT_URL=http://localhost:6333  # Or leave empty for embedded
   QDRANT_COLLECTION=api_docs
   RAG_TOP_K=5
   ```

3. **Restart backend**
   ```bash
   ./start.sh
   ```

### How RAG Works

1. User sends a message
2. Backend generates embedding for the query
3. Qdrant searches for similar documents (top-k)
4. Retrieved documents are added as context
5. AI generates response using both conversation history and retrieved context

### RAG Configuration

- `RAG_ENABLED` - Enable/disable RAG
- `QDRANT_URL` - Qdrant server URL (empty for embedded mode)
- `QDRANT_COLLECTION` - Collection name in Qdrant
- `RAG_TOP_K` - Number of documents to retrieve (default: 5)

## File Structure

```
backend/
├── main.py              # FastAPI app, routes, SSE streaming
├── orchestrator.py      # Conversation flow, context management
├── ai_provider.py       # AI provider factory and implementations
├── rag_service.py       # RAG integration with Qdrant
├── config.py            # Pydantic settings, environment config
├── logger.py            # Structured logging configuration
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
├── start.sh/bat        # Startup scripts
├── test_connection.py  # Connection tests
└── verify_setup.py     # Setup verification
```

### Key Components

#### `main.py`
- FastAPI application setup
- CORS middleware configuration
- REST API endpoints
- SSE streaming for chat responses
- Request/response models

#### `orchestrator.py`
- Conversation state management
- Message history tracking
- RAG integration
- AI provider coordination
- Streaming response handling

#### `ai_provider.py`
- `BaseAIProvider` abstract class
- Provider-specific implementations
- Factory pattern for provider creation
- LangChain integration
- Streaming support

#### `rag_service.py`
- Qdrant client initialization
- Embedding generation
- Semantic search
- Context formatting
- Error handling

#### `config.py`
- Pydantic Settings for type-safe config
- Environment variable loading
- Provider-specific settings
- Validation and defaults

#### `logger.py`
- Structured logging setup
- File and console handlers
- Configurable log levels
- LLM request/response logging

## Development

### Running Tests

```bash
# Test API connection
python test_connection.py

# Verify setup
python verify_setup.py
```

### Debugging

Enable detailed logging:
```env
LOG_LEVEL=DEBUG
LOG_LLM_REQUESTS=true
LOG_FILE=logs/app.log
```

This will log:
- All HTTP requests
- LLM requests with full prompts
- LLM responses
- RAG search queries and results
- Error stack traces

### Hot Reload

For development with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 3000
```

## Troubleshooting

### Common Issues

#### 1. AWS Credentials Not Found

**Error:** `Could not load credentials to authenticate with AWS client`

**Solutions:**
- Run `aws configure` to set up credentials
- Or set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Or use IAM role if running on EC2/ECS

#### 2. Missing botocore[crt]

**Error:** `Missing Dependency: Using the login credential provider requires an additional dependency`

**Solution:**
```bash
pip install 'botocore[crt]'
```

#### 3. Bedrock Access Denied

**Error:** `AccessDeniedException` when calling Bedrock

**Solutions:**
- Ensure your AWS account has Bedrock access enabled
- Request model access in AWS Console: Bedrock → Model access
- Verify your IAM user/role has `bedrock:InvokeModel` permission

#### 4. Provider Initialization Fails

**Solutions:**
- Check API keys in `.env`
- Verify AWS credentials for Bedrock
- Check network connectivity
- Try a different provider (set `AI_PROVIDER=openai` if you have OpenAI key)

#### 5. RAG Not Working

**Solutions:**
- Verify Qdrant is running: `finch ps` (or `docker ps`)
- Check collection exists: `python -c "from qdrant_client import QdrantClient; print(QdrantClient('http://localhost:6333').get_collections())"`
- Verify ingestion completed successfully
- Temporarily disable RAG: `RAG_ENABLED=false` in `.env`

#### 6. CORS Errors

**Solutions:**
- Update `CORS_ORIGINS` in `.env`
- Use comma-separated list: `http://localhost:8000,https://example.com`
- Use `*` for development (not recommended for production)

#### 7. Port Already in Use

**Error:** `Address already in use`

**Solutions:**
```bash
# Find process using port 3000
lsof -i :3000
# Kill the process
kill -9 <PID>
```

Or change the port in `.env`:
```env
API_PORT=3001
```

### Verification Commands

```bash
# Check Python version (requires 3.13+)
python --version

# Check if packages are installed
pip list | grep -E "fastapi|langchain|boto3"

# Check AWS credentials
aws sts get-caller-identity

# Test backend connectivity
python test_connection.py

# Verify complete setup
python verify_setup.py
```

### Debug Logging

Enable detailed logging in `.env`:
```env
LOG_LEVEL=DEBUG
LOG_LLM_REQUESTS=true
LOG_FILE=logs/app.log
```

This will log:
- All HTTP requests
- LLM requests with full prompts
- LLM responses
- RAG search queries and results
- Error stack traces

## Production Deployment

### Docker

```bash
docker build -t chat-backend .
docker run -p 3000:3000 --env-file .env chat-backend
```

### Environment Variables

For production, set:
```env
LOG_LEVEL=WARNING
LOG_FILE=logs/production.log
CORS_ORIGINS=https://yourdomain.com
```

### Security

- Use environment-specific API keys
- Restrict CORS origins
- Enable HTTPS
- Implement rate limiting
- Add authentication if needed

## Dependencies

Core dependencies:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `langchain` - AI framework
- `langchain-aws` - Bedrock integration
- `langchain-openai` - OpenAI integration
- `langchain-anthropic` - Anthropic integration
- `langchain-google-genai` - Gemini integration
- `langchain-cohere` - Cohere integration
- `qdrant-client` - Vector database client
- `boto3` - AWS SDK
- `pydantic-settings` - Configuration management

See [requirements.txt](requirements.txt) for complete list.
