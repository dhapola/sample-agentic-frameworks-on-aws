# AI Chat Widget with RAG

An AI-powered embeddable chat widget with RAG (Retrieval-Augmented Generation) support. Drop-in customer support solution that works on any website with a single script tag.

## Features

### Chat Widget
- **One-line integration** - Single script tag, zero configuration
- **Lazy loading** - Widget loads only when clicked (performance optimized)
- **Iframe isolation** - Zero CSS/JS conflicts with host page
- **Streaming responses** - Real-time token-by-token AI responses
- **Session persistence** - Conversations persist across page reloads
- **Resizable & fullscreen** - Flexible UI modes
- **Customizable** - 10+ themes with full CSS variable support

### AI Integration
- **Multiple providers** - AWS Bedrock, OpenAI, Anthropic, Google Gemini, Azure OpenAI, Cohere
- **LangChain powered** - Unified interface across all providers
- **Conversation memory** - Context-aware responses
- **Streaming support** - Server-Sent Events (SSE) for real-time streaming

### RAG (Retrieval-Augmented Generation)
- **Semantic search** - Vector-based search over your documentation
- **Source attribution** - Automatic citation with clickable documentation links
- **Multiple embedding providers** - Bedrock Titan, OpenAI, Cohere, HuggingFace
- **Qdrant vector database** - Efficient similarity search
- **Reduced hallucinations** - Grounded responses from your docs
- **Configurable relevance** - Adjustable top-k results

### API Documentation Indexer
- **Crawl4AI powered** - LLM-optimized web crawling
- **Clean markdown output** - AI-friendly content extraction
- **Async architecture** - Fast parallel processing
- **Domain-restricted** - Stays within your documentation site
- **Configurable depth** - Control crawl scope and limits

## Quick Start

### 1. Backend Setup

```bash
cd backend
./start.sh  # Unix/macOS
# or
start.bat   # Windows
```

Configure `.env` with your AI provider:

```env
AI_PROVIDER=bedrock
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Integration

Add to your website:

```html
<script>
  window.ChatPluginConfig = {
    apiUrl: 'http://localhost:3000/api',
    position: 'bottom-right',
    theme: 'default',
    title: 'API Twin',
    autoOpen: false
  };
</script>
<script src="http://localhost:8000/chat-plugin.js"></script>
```

Visit `http://localhost:8000/example.html` for a demo.

## RAG Setup (Optional)

### 1. Crawl API Documentation

```bash
cd api-doc-indexer/crawler
./setup.sh  # Unix/macOS or setup.bat for Windows

# Configure .env
cp .env.example .env
# Edit .env with your API documentation URL
```

Example `.env`:
```env
API_DOC_URL=https://docs.stripe.com/api
API_DOC_MAX_DEPTH=3
API_DOC_MAX_PAGES=100
```

Run crawler:
```bash
python crawler.py
```

### 2. Ingest into Vector Store

```bash
cd api-doc-indexer/ingester
./setup.sh  # Unix/macOS or setup.bat for Windows

# Configure .env
cp .env.example .env
```

Example `.env`:
```env
EMBEDDING_PROVIDER=bedrock
AWS_REGION=us-west-2
QDRANT_USE_EMBEDDED=false
CRAWLER_DATA_PATH=../crawler/data
```

Run ingestion:
```bash
python ingest.py
```

Test search:
```bash
python search.py "how to authenticate"
```

### 3. Enable RAG in Backend

Update `backend/.env`:
```env
RAG_ENABLED=true
QDRANT_URL=http://localhost:6333  # Or leave empty for embedded mode
QDRANT_COLLECTION=api_docs
RAG_TOP_K=5
```

Restart backend to apply changes.

## Architecture

```
┌─────────────┐
│   Website   │
│  (Host Page)│
└──────┬──────┘
       │ <script> tag
       ▼
┌─────────────────┐
│  Chat Plugin    │
│  (chat-plugin.js)│
│  - FAB Button   │
│  - Iframe Mgmt  │
└──────┬──────────┘
       │ Lazy load
       ▼
┌─────────────────┐      ┌──────────────┐
│  Chat Widget    │◄────►│   Backend    │
│  (iframe)       │ SSE  │   (FastAPI)  │
│  - UI Logic     │      │  - LangChain │
│  - API Client   │      │  - RAG       │
└─────────────────┘      └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              ┌──────────┐          ┌─────────────┐
              │ AI Model │          │   Qdrant    │
              │ (Bedrock,│          │  (Vector DB)│
              │  OpenAI, │          │             │
              │  etc.)   │          └─────────────┘
              └──────────┘
```

### RAG Pipeline

```
API Docs → Crawl4AI → Markdown → LangChain Embeddings → Qdrant → Semantic Search
```

## Component Documentation

- **[Backend](backend/README.md)** - FastAPI server, AI providers, RAG service
- **[Frontend](frontend/README.md)** - Chat widget, UI components, API client
- **[Crawler](api-doc-indexer/crawler/README.md)** - Web crawler for API docs
- **[Ingester](api-doc-indexer/ingester/README.md)** - Vector embeddings and search

## Configuration

### Backend Environment Variables

```env
# AI Provider (bedrock, openai, anthropic, gemini, azure, cohere)
AI_PROVIDER=bedrock

# AWS Bedrock
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# RAG
RAG_ENABLED=false
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=api_docs
RAG_TOP_K=5

# Server
API_PORT=3000
CORS_ORIGINS=*

# Logging
LOG_LEVEL=INFO
LOG_LLM_REQUESTS=true
```

### Frontend Configuration

```javascript
window.ChatPluginConfig = {
  apiUrl: 'http://localhost:3000/api',  // Required
  position: 'bottom-right',              // bottom-right, bottom-left, top-right, top-left
  theme: 'default',                      // Theme name
  title: 'Chat Support',                 // Header title
  subtitle: 'We\'re here to help',       // Header subtitle
  placeholder: 'Type your message...',   // Input placeholder
  autoOpen: false                        // Auto-open on page load
};
```

## API Endpoints

- `GET /` - API information
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/{id}` - Get conversation history
- `POST /api/chat` - Send message (streaming SSE response)
- `GET /api/health` - Health check
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

## Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev     # Development server
npm run build   # Production build (minified)
```

## Testing

### Quick Testing (5 minutes)

Follow the [Testing Quick Start Guide](TESTING_QUICKSTART.md) to verify your setup:

```bash
# 1. Verify environment
cd backend && python pre_test_check.py

# 2. Start services
# Terminal 1: cd backend && python main.py
# Terminal 2: cd frontend && npm run dev

# 3. Open test page
open http://localhost:8000/example.html

# 4. Run basic tests from TESTING_QUICKSTART.md
```

### Comprehensive Testing

For full manual testing with 45+ test cases, see:
- **[Manual Test Plan](MANUAL_TEST_PLAN.md)** - Complete test suite with detailed steps
- **[Test Queries](TEST_QUERIES.md)** - 100+ pre-written test queries organized by category

## Troubleshooting

### Markdown Not Rendering Properly

**Symptom**: Chat responses appear as bold text in a single heading instead of formatted markdown.

**Cause**: Newlines are being lost during SSE (Server-Sent Events) streaming.

**Solution**: This has been fixed in the latest version. If you still see issues:
1. Ensure you're running the latest code
2. Check browser console for errors
3. Verify `marked.js` loaded successfully (look for "✅ Marked.js loaded successfully" in console)
4. Clear browser cache and reload

### Source Links Not Appearing

**Symptom**: RAG responses don't include source citations.

**Cause**: RAG might not be properly configured or no relevant documents found.

**Solution**:
1. Verify RAG is enabled: `RAG_ENABLED=true` in `backend/.env`
2. Check Qdrant is running: `curl http://localhost:6333/collections`
3. Verify documents are indexed: `cd api-doc-indexer/ingester && python search.py "test"`
4. Check backend logs for "RAG search query" messages
5. Ensure your question relates to indexed documentation

### Streaming Not Working

**Symptom**: Response appears all at once instead of streaming.

**Cause**: SSE connection issues or browser compatibility.

**Solution**:
1. Check browser console for SSE connection errors
2. Verify CORS is properly configured in backend
3. Test with a different browser
4. Check network tab for `text/event-stream` content type

### Backend Connection Errors

**Symptom**: "Failed to fetch" or connection refused errors.

**Cause**: Backend not running or CORS misconfiguration.

**Solution**:
1. Verify backend is running: `curl http://localhost:3000/api/health`
2. Check `CORS_ORIGINS` in `backend/.env` includes your frontend URL
3. Ensure firewall isn't blocking port 3000
4. Check backend logs for errors

For more detailed troubleshooting, see component-specific README files:
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Crawler README](api-doc-indexer/crawler/README.md)
- [Ingester README](api-doc-indexer/ingester/README.md)

## Tech Stack

- **Backend**: Python 3.13+, FastAPI, LangChain, Pydantic
- **Frontend**: Vanilla JavaScript (ES6+), marked.js
- **Crawler**: Python 3.13+, Crawl4AI, Playwright
- **Ingester**: Python 3.13+, LangChain, Qdrant
- **AI Providers**: AWS Bedrock, OpenAI, Anthropic, Google Gemini, Azure OpenAI, Cohere
- **Vector DB**: Qdrant (embedded or server mode)

## License

MIT
