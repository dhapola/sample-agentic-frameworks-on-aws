# Tech Stack

## Backend

**Framework**: FastAPI (Python 3.13+)
- Modern async Python web framework
- Auto-generated OpenAPI docs (Swagger UI + ReDoc)
- Pydantic v2 for data validation with field validators
- Security headers middleware for XSS/clickjacking protection

**AI Integration**: LangChain
- Unified interface across multiple AI providers (Bedrock, OpenAI, Anthropic, Gemini)
- Streaming support via async generators (`astream`)
- Provider factory pattern for extensibility
- System prompts with markdown formatting instructions and RAG context injection
- Conditional imports to avoid missing dependency errors

**RAG Integration**: 
- `rag_service.py` - Semantic search over documentation using Qdrant
- BedrockEmbeddings (Titan v2) for query vectorization
- Context injection into LLM system prompts with source attribution
- `query_points` API for vector search (Qdrant new API)
- Top-K retrieval with configurable limit

**Security Features**:
- Input sanitization with prompt injection pattern detection
- XSS protection via DOMPurify on frontend
- Security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy)
- Error message sanitization with PII redaction
- Origin validation for postMessage communication
- UUID v4 validation for conversation IDs with Pydantic field validators
- Message length limits (1-4000 chars)

**Dependencies**:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `langchain-core` + provider-specific packages (`langchain-aws`, `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`)
- `boto3` - AWS SDK for Bedrock
- `pydantic` v2 + `pydantic-settings` - Environment-based configuration with validation
- `qdrant-client` - Vector database client

**Configuration**: Environment variables via `.env` file
- Pydantic Settings v2 for type-safe config with `SettingsConfigDict`
- Provider-specific settings (API keys, model IDs, regions)
- RAG configuration (enabled flag, Qdrant URL/API key, collection name, top-k)
- Logging configuration (level, file path, format, LLM request logging toggle)
- CORS origins configuration

## Frontend

**Stack**: Vanilla JavaScript (ES6+)
- No framework dependencies (marked.js and DOMPurify loaded dynamically via CDN)
- Native Web APIs (fetch, postMessage, SSE)
- ES6 module system with dynamic imports

**Dependencies**:
- `marked` (v11.1.1) - Markdown rendering with GFM support (CDN, dynamically loaded)
- `DOMPurify` (v3.0.8) - XSS protection for rendered HTML (CDN, dynamically loaded)
- `terser` - Minification for production builds (dev dependency)

**Security Features**:
- DOMPurify sanitization with strict allowed tags/attributes whitelist
- Origin validation for postMessage (localhost/127.0.0.1 in dev, configurable for prod)
- URL scheme validation (http/https/mailto/tel/callto/sms/cid/xmpp via regex)
- Fallback markdown parser with HTML escaping when marked.js fails to load
- Graceful degradation if DOMPurify fails to load

**Architecture**:
- `chat-plugin.js` - Entry point, creates FAB, manages iframe lifecycle, handles fullscreen toggle
- `widget.js` - Chat UI logic inside iframe, handles streaming, markdown rendering, session persistence
- `chat-api.js` - API client with SSE streaming support and async generator pattern
- CSS isolation via iframe prevents conflicts with host page
- Lazy loading: iframe content loads only when FAB is clicked

**Streaming Implementation**:
- SSE (Server-Sent Events) for real-time token streaming
- Newline escaping/unescaping for SSE protocol compatibility (`\\n` ↔ `\n`)
- Progressive text rendering during streaming, markdown parsing on completion
- Event-based protocol: `data:`, `event: done`, `event: error`
- Error handling with sanitized error messages

**UI Features**:
- Resizable and fullscreen modes with smooth transitions
- Session persistence via sessionStorage
- Auto-resizing textarea (max 120px height)
- Typing indicator with animated dots
- Conversation history loading on widget open
- Configurable themes and positioning

## API Doc Indexer

### Crawler

**Stack**: Python 3.13+
- Web crawler using Crawl4AI for LLM-optimized extraction
- Async architecture with `AsyncWebCrawler` for fast crawling
- BeautifulSoup + html2text fallback for manual markdown conversion
- Clean markdown output for AI applications

**Dependencies**:
- `crawl4ai` - LLM-friendly web crawler with browser automation
- `beautifulsoup4` - HTML parsing for fallback extraction
- `html2text` - HTML to markdown conversion
- `python-dotenv` - Environment variable management
- `playwright` - Browser automation (installed separately via `playwright install`)

**Architecture**:
- `crawler.py` - Async crawler with Crawl4AI integration and fallback extraction
- `config.py` - Pydantic-based environment configuration
- Self-contained module with own `.env` file
- MD5 hash-based file naming for uniqueness
- Domain-restricted crawling with URL normalization
- Configurable depth, delay, and page limits

**Crawling Strategy**:
- BFS (breadth-first search) with depth tracking
- Network idle wait strategy with additional JS execution delay
- Manual link extraction from HTML when Crawl4AI fails
- Main content detection (markdown-body, article, main tags)
- Polite crawling with configurable delays (default 1.0s)

### Ingester

**Stack**: Python 3.13+
- Vector embeddings using LangChain with multiple provider support
- Qdrant vector database for storage and search (embedded or server mode)
- Async/concurrent processing with ThreadPoolExecutor for performance
- Batch processing with semaphore-based concurrency control

**Dependencies**:
- `qdrant-client` - Vector database client
- `langchain-core` - AI framework core
- `langchain-aws` - AWS Bedrock embeddings (default)
- `langchain-openai` - OpenAI embeddings (optional)
- `langchain-huggingface` - HuggingFace embeddings (optional)
- `boto3` - AWS SDK for Bedrock
- `python-dotenv` - Environment management
- `tqdm` - Progress bars with async support (`tqdm.asyncio`)

**Architecture**:
- `embedder.py` - LangChain embedding providers with factory pattern and abstract base class
- `vector_store.py` - Qdrant integration with hash-based point IDs for deduplication
- `ingest.py` - Async pipeline with concurrent batch processing and semaphore control
- `search.py` - CLI tool for semantic search with query vectorization
- `browse.py` - Web UI for browsing indexed documents
- `diagnose.py` - Data quality analysis tool (chunk size stats, empty content detection)
- `benchmark.py` - Performance estimation tool
- `config.py` - Pydantic-based environment configuration
- Self-contained module with own `.env` file

**Performance**:
- Async/concurrent processing (5 batches simultaneously by default, configurable)
- ThreadPoolExecutor for sync LangChain operations (max 10 workers)
- Hash-based point IDs (MD5) for safe concurrent upserts and automatic deduplication
- Optimized batch sizes (100 chunks per batch by default)
- Semaphore-based concurrency control to prevent API rate limiting
- 12-24x faster than sequential processing
- Progress tracking with `tqdm.asyncio`

**Chunking Strategy**:
- Max 1500 characters per chunk (~375 tokens at 4:1 char:token ratio)
- Paragraph-based splitting (double newlines) with fallback to sentences
- Word-level splitting for oversized content
- Preserves context with proper boundaries
- Validates chunk sizes before embedding (6000 char hard limit for safety)
- Skips empty chunks and overly long content

**Embedding Providers**:
- AWS Bedrock (Titan v2) - Default, 1024 dimensions, `amazon.titan-embed-text-v2:0`
- OpenAI (text-embedding-3-small) - 1536 dimensions
- HuggingFace (local models) - Variable dimensions, `sentence-transformers/all-MiniLM-L6-v2` default

**Vector Store**:
- Qdrant with cosine distance similarity
- Hash-based point IDs prevent duplicates during concurrent ingestion
- Upsert operation for safe concurrent writes
- Collection management (create, delete, exists check, info retrieval)
- Embedded mode for development, server mode for production

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
