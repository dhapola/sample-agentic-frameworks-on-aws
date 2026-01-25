# Tech Stack

## Backend

**Framework**: FastAPI (Python 3.13+)
- Modern async Python web framework
- Auto-generated OpenAPI docs (Swagger UI + ReDoc)
- Pydantic for data validation
- Security headers middleware for XSS/clickjacking protection

**AI Integration**: LangChain
- Unified interface across multiple AI providers
- Streaming support via async generators
- Provider factory pattern for extensibility
- System prompts with markdown formatting instructions

**RAG Integration**: 
- `rag_service.py` - Semantic search over documentation
- Qdrant vector database integration
- Context injection into LLM prompts
- Source attribution in responses

**Security Features**:
- Input sanitization with prompt injection detection
- XSS protection via DOMPurify on frontend
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- Error message sanitization
- Origin validation for postMessage
- UUID validation for conversation IDs

**Dependencies**:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `langchain` + provider-specific packages (`langchain-aws`, `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`)
- `boto3` - AWS SDK for Bedrock
- `pydantic-settings` - Environment-based configuration
- `qdrant-client` - Vector database client

**Configuration**: Environment variables via `.env` file
- Pydantic Settings for type-safe config
- Provider-specific settings (API keys, model IDs, etc.)
- RAG configuration (enabled flag, Qdrant URL, collection name, top-k)
- Logging configuration (level, file, LLM request logging)

## Frontend

**Stack**: Vanilla JavaScript (ES6+)
- No framework dependencies (except marked.js and DOMPurify loaded via CDN)
- Native Web APIs (fetch, postMessage, SSE)
- ES6 module system for code organization

**Dependencies**:
- `marked` (v11.1.1) - Markdown rendering for bot responses (CDN)
- `DOMPurify` (v3.0.8) - XSS protection for rendered HTML (CDN)
- `terser` - Minification for production builds

**Security Features**:
- DOMPurify sanitization of all rendered markdown
- Origin validation for postMessage communication
- Allowed tags/attributes whitelist for HTML
- URL scheme validation (http/https/mailto only)
- Fallback markdown parser with HTML escaping

**Architecture**:
- `chat-plugin.js` - Entry point, creates FAB and manages iframe lifecycle
- `widget.js` - Chat UI logic inside iframe, handles streaming and markdown rendering
- `chat-api.js` - API client with SSE streaming support
- CSS isolation via iframe prevents conflicts with host page

**Streaming Implementation**:
- SSE (Server-Sent Events) for real-time token streaming
- Newline escaping/unescaping for SSE protocol compatibility
- Progressive rendering with final markdown parsing
- Error handling with sanitized error messages

## API Doc Indexer

### Crawler

**Stack**: Python 3.13+
- Web crawler using Crawl4AI for LLM-optimized extraction
- Async architecture for fast crawling
- Clean markdown output for AI applications

**Dependencies**:
- `crawl4ai` - LLM-friendly web crawler
- `python-dotenv` - Environment variable management
- `playwright` - Browser automation (installed separately)

**Architecture**:
- `crawler.py` - Async crawler with Crawl4AI integration
- `config.py` - Environment-based configuration
- Self-contained module with own `.env` file
- MD5 hash-based file naming for uniqueness

### Ingester

**Stack**: Python 3.13+
- Vector embeddings using LangChain
- Qdrant vector database for storage and search
- Multiple embedding provider support
- Async/concurrent processing for performance

**Dependencies**:
- `qdrant-client` - Vector database client
- `langchain` + `langchain-core` - AI framework
- `langchain-aws` - AWS Bedrock embeddings
- `langchain-openai` - OpenAI embeddings (optional)
- `langchain-huggingface` - HuggingFace embeddings (optional)
- `boto3` - AWS SDK for Bedrock
- `python-dotenv` - Environment management
- `tqdm` - Progress bars (async support)

**Architecture**:
- `embedder.py` - LangChain embedding providers with factory pattern
- `vector_store.py` - Qdrant integration (embedded or server mode)
- `ingest.py` - Async pipeline with concurrent batch processing
- `search.py` - CLI tool for semantic search
- `browse.py` - Web UI for browsing indexed documents
- `diagnose.py` - Data quality analysis tool
- `benchmark.py` - Performance estimation tool
- `config.py` - Environment-based configuration
- Self-contained module with own `.env` file

**Performance**:
- Async/concurrent processing (5 batches simultaneously by default)
- ThreadPoolExecutor for sync LangChain operations
- Hash-based point IDs (MD5) for safe concurrent upserts and deduplication
- Optimized batch sizes (100 chunks per batch)
- Semaphore-based concurrency control
- 12-24x faster than sequential processing

**Chunking Strategy**:
- Max 1500 characters per chunk (~375 tokens)
- Paragraph-based splitting with fallback to sentences
- Word-level splitting for oversized content
- Preserves context with overlap
- Validates chunk sizes before embedding

**Embedding Providers**:
- AWS Bedrock (Titan v2) - Default, 1024 dimensions
- OpenAI (text-embedding-3-small) - 1536 dimensions
- HuggingFace (local models) - Variable dimensions

## Common Commands

### Backend

```bash
# Setup (first time)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start server (auto-setup)
./start.sh  # Unix/macOS
start.bat   # Windows

# Manual start
python main.py

# Run tests
python test_api.py
python test_bedrock_auth.py
python test_orchestrator.py

# View API docs
# http://localhost:3000/docs (Swagger)
# http://localhost:3000/redoc (ReDoc)
```

### Frontend

```bash
# Setup (first time)
cd frontend
npm install

# Start dev server
npm run dev  # Serves on http://localhost:8000

# Build for production
npm run build  # Minifies JS files

# Alternative dev server
npx serve -p 8000
```

### API Doc Indexer

#### Crawler

```bash
# Setup (first time)
cd api-doc-indexer/crawler
./setup.sh  # Unix/macOS
setup.bat   # Windows

# Or manual setup
pip install -r requirements.txt
playwright install

# Configure
cp .env.example .env
# Edit .env with your API doc URL

# Run crawler
python crawler.py

# Check crawled data
ls -la data/
cat data/index.json
```

#### Ingester

```bash
# Setup (first time)
cd api-doc-indexer/ingester
./setup.sh  # Unix/macOS
setup.bat   # Windows

# Start Qdrant server (using Finch - Docker alternative for macOS)
finch vm init  # First time only
finch run -d -p 6333:6333 -p 6334:6334 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant

# Verify Qdrant is running
finch ps
python test_qdrant.py

# Configure
cp .env.example .env
# Edit .env: Set EMBEDDING_PROVIDER=bedrock (or openai, cohere, huggingface)
# Set QDRANT_USE_EMBEDDED=false for server mode (recommended for production)

# Analyze crawler data quality
python diagnose.py

# Estimate processing time
python benchmark.py

# Run ingestion (cleans up old data by default)
python ingest.py

# Append to existing data
python ingest.py --append

# Search documentation
python search.py "how to authenticate"
python search.py "create customer" --limit 10

# Manage Qdrant server
finch stop qdrant    # Stop server
finch start qdrant   # Start server
finch logs qdrant    # View logs
finch rm qdrant      # Remove container (data persists in volume)
```

### Full Stack

```bash
# Terminal 1: Backend
cd backend && ./start.sh

# Terminal 2: Frontend
cd frontend && npm run dev

# Open demo
# http://localhost:8000/example.html
```

## Development Tools

- **API Testing**: Swagger UI at `/docs`, test scripts in `backend/test_*.py`
- **Hot Reload**: Backend uses `uvicorn --reload`, frontend uses `serve` with live reload
- **Container Runtime**: Finch (Docker alternative for macOS) - lightweight, open-source container runtime
- **Vector Database**: Qdrant server mode for production, embedded mode for development
- **Performance Tools**: `benchmark.py` for time estimation, `diagnose.py` for data quality analysis

## Environment Setup

Backend requires `.env` file (copy from `.env.example`):
```env
AI_PROVIDER=bedrock
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
API_PORT=3000
```

Frontend config via global object:
```javascript
window.ChatPluginConfig = {
  apiUrl: 'http://localhost:3000/api',
  position: 'bottom-right'
};
```

Crawler requires `.env` file (copy from `.env.example`):
```env
API_DOC_URL=https://docs.stripe.com/api
API_DOC_STORAGE_PATH=./data
API_DOC_MAX_DEPTH=3
API_DOC_CRAWL_DELAY=1.0
API_DOC_MAX_PAGES=100
API_DOC_VERBOSE=false
```

Ingester requires `.env` file (copy from `.env.example`):
```env
# Embedding provider
EMBEDDING_PROVIDER=bedrock
EMBEDDING_DIMENSION=1024

# AWS Bedrock (default)
AWS_REGION=us-west-2
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# Qdrant (server mode recommended for production)
QDRANT_USE_EMBEDDED=false
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=api_docs

# Data
CRAWLER_DATA_PATH=../crawler/data
BATCH_SIZE=100

# Performance (concurrent batch processing)
MAX_CONCURRENT_BATCHES=5
```

**Note**: Use `QDRANT_USE_EMBEDDED=true` for development/testing only. For production or high-concurrency ingestion, use server mode with Finch/Docker.

## Logging

**Backend Logging**:
- Structured logging with configurable levels (DEBUG, INFO, WARNING, ERROR)
- File and console output support
- LLM request/response logging (optional, controlled by `LOG_LLM_REQUESTS`)
- Sanitized logging to prevent sensitive data exposure
- Request tracking with conversation IDs
- RAG search query logging with document scores

**Log Configuration**:
```env
LOG_LEVEL=INFO
LOG_FILE=logs/backend.log  # Optional file output
LOG_LLM_REQUESTS=true      # Enable detailed LLM logging
```

**What Gets Logged**:
- API requests and responses
- AI provider initialization
- RAG search queries and results
- Conversation creation and retrieval
- Error traces with sanitized messages
- Session cleanup operations
