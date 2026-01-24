# Project Structure

## Root Layout

```
.
├── backend/          # FastAPI backend
├── frontend/         # Chat widget frontend
├── api-doc-indexer/  # API documentation crawler
├── setup.sh/bat      # Automated setup scripts
├── README.md         # Main documentation
└── QUICKSTART.md     # 5-minute setup guide
```

## Backend Structure

```
backend/
├── main.py                  # FastAPI app, REST endpoints
├── orchestrator.py          # Conversation flow, context management
├── ai_provider.py           # AI provider implementations (factory pattern)
├── config.py                # Environment-based configuration (Pydantic)
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── .env                    # Local config (gitignored)
├── start.sh/bat            # Startup scripts with auto-setup
├── test_*.py               # Test scripts
├── Dockerfile              # Container config
└── docker-compose.yml      # Docker orchestration
```

**Key Patterns**:
- `main.py` - Route definitions, request/response models
- `orchestrator.py` - Business logic, conversation state
- `ai_provider.py` - Provider abstraction, LangChain integration
- `config.py` - Single source of truth for configuration

## Frontend Structure

```
frontend/
├── chat-plugin.js          # Entry point (script tag injection)
├── widget.html             # Chat UI (loaded in iframe)
├── widget.css              # Widget styles (isolated)
├── widget.js               # Widget logic (event handling, UI updates)
├── customer_config.css     # Theme customization (CSS variables)
├── resize-handles.css      # Resize functionality styles
├── api/
│   └── chat-api.js         # API client (fetch + SSE)
├── example.html            # Demo/integration example
├── package.json            # NPM config
└── README.md               # Frontend docs
```

**Key Patterns**:
- `chat-plugin.js` - Creates FAB, manages iframe lifecycle, parent-child communication
- `widget.js` - Handles user interactions, message rendering, streaming
- `chat-api.js` - Encapsulates all backend communication
- Iframe isolation prevents CSS/JS conflicts with host page

## API Doc Indexer Structure

```
api-doc-indexer/
├── crawler/
│   ├── crawler.py              # Crawl4AI-based web crawler
│   ├── config.py               # Crawler configuration
│   ├── requirements.txt        # Crawler dependencies
│   ├── setup.sh/bat            # Setup scripts
│   ├── .env.example           # Environment template
│   ├── .env                   # Local config (gitignored)
│   ├── .gitignore             # Ignore data and env files
│   ├── __init__.py            # Package initialization
│   ├── README.md              # Crawler documentation
│   └── data/                  # Crawled data storage (gitignored)
│       ├── index.json         # Master index of all pages
│       └── *.json             # Individual page data files
│
└── ingester/
    ├── embedder.py             # LangChain embeddings
    ├── vector_store.py         # Qdrant integration
    ├── config.py               # Ingester configuration
    ├── ingest.py              # Main ingestion script
    ├── search.py              # Search CLI tool
    ├── requirements.txt        # Ingester dependencies
    ├── setup.sh/bat            # Setup scripts
    ├── .env.example           # Environment template
    ├── .env                   # Local config (gitignored)
    ├── .gitignore             # Ignore storage and env files
    ├── __init__.py            # Package initialization
    ├── README.md              # Ingester documentation
    └── qdrant_storage/        # Vector DB storage (gitignored)
```

**Key Patterns**:
- `crawler.py` - Async crawler with Crawl4AI integration
- `embedder.py` - LangChain-based embedding generation
- `vector_store.py` - Qdrant vector database operations
- `ingest.py` - Pipeline: load → embed → store
- `search.py` - CLI tool for semantic search
- Self-contained modules with own `.env` files
- JSON storage with MD5 hash filenames
- Vector embeddings with configurable providers

## Code Organization Principles

### Backend

1. **Separation of Concerns**:
   - Routes in `main.py`
   - Business logic in `orchestrator.py`
   - Provider abstraction in `ai_provider.py`
   - Configuration in `config.py`

2. **Provider Pattern**:
   - `BaseAIProvider` abstract class
   - Provider-specific implementations (BedrockProvider, OpenAIProvider, etc.)
   - Factory for provider instantiation

3. **Configuration**:
   - Environment variables via `.env`
   - Pydantic models for validation
   - Provider-specific config sections

### Frontend

1. **Module Separation**:
   - Plugin initialization (chat-plugin.js)
   - Widget UI logic (widget.js)
   - API communication (chat-api.js)

2. **Event-Driven**:
   - postMessage for parent-child communication
   - Custom event system for extensibility
   - SSE for streaming responses

3. **Styling**:
   - Base styles in `widget.css`
   - Customization via `customer_config.css` (CSS variables)
   - Iframe provides complete isolation

### API Doc Indexer

1. **Self-Contained Modules**:
   - Independent configuration (own `.env` files)
   - Standalone execution (no backend dependency)
   - Modular design for RAG integration

2. **Crawler Module**:
   - Async architecture with Crawl4AI
   - LLM-optimized content extraction
   - Domain-restricted crawling
   - Configurable depth and page limits
   - Polite crawling with delays

3. **Ingester Module**:
   - LangChain embedding providers
   - Factory pattern for provider abstraction
   - Qdrant vector database integration
   - Batch processing for efficiency
   - Clean-up before ingestion (default)

4. **Data Management**:
   - JSON-based storage for crawled data
   - MD5 hash filenames for uniqueness
   - Master index for quick lookups
   - Vector embeddings in Qdrant
   - Semantic search capabilities

## File Naming Conventions

- **Backend**: Snake_case for Python files (`ai_provider.py`, `test_api.py`)
- **Frontend**: Kebab-case for JS/CSS files (`chat-plugin.js`, `widget.css`)
- **API Doc Indexer**: Snake_case for Python files (`crawler.py`, `config.py`)
- **Config**: Lowercase with dots (`.env`, `.gitignore`)
- **Docs**: UPPERCASE for root-level docs (`README.md`, `QUICKSTART.md`)

## Import Patterns

### Backend
```python
# Standard library first
from typing import Optional, List
from datetime import datetime

# Third-party packages
from fastapi import FastAPI
from pydantic import BaseModel

# Local modules
from config import get_config
from orchestrator import get_orchestrator
```

### Frontend
```javascript
// ES6 modules
import { ChatAPI } from './api/chat-api.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked@12.0.0/lib/marked.esm.js';
```

### API Doc Indexer
```python
# Standard library first
from pathlib import Path
from typing import Set, Dict, List
from abc import ABC, abstractmethod

# Third-party packages
from crawl4ai import AsyncWebCrawler
from qdrant_client import QdrantClient
from langchain_aws import BedrockEmbeddings

# Local modules
from config import config
```

## Storage Patterns

**Current (Development)**:
- In-memory dictionaries (`conversations_db`, `messages_db`)
- Session storage in browser for persistence

**Production Recommendation**:
- Replace with PostgreSQL/MongoDB
- Add Redis for caching
- Implement proper session management

**API Doc Indexer**:
- JSON files with MD5 hash filenames (crawler output)
- Master index file for quick lookups
- Vector embeddings in Qdrant (ingester output)
- Embedded or server mode for Qdrant
- Semantic search with cosine similarity

## Testing Structure

- `test_api.py` - API endpoint tests
- `test_bedrock_auth.py` - AWS Bedrock authentication tests
- `test_orchestrator.py` - Conversation flow tests
- `example.html` - Frontend integration testing

## Configuration Files

- `.env` - Backend environment variables (gitignored)
- `.env.example` - Template for environment setup
- `package.json` - Frontend dependencies and scripts
- `requirements.txt` - Backend Python dependencies
- `customer_config.css` - Theme customization (CSS variables)
- `api-doc-indexer/crawler/.env` - Crawler configuration (gitignored)
- `api-doc-indexer/crawler/.env.example` - Crawler config template
- `api-doc-indexer/ingester/.env` - Ingester configuration (gitignored)
- `api-doc-indexer/ingester/.env.example` - Ingester config template
