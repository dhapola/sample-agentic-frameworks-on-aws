# Product Overview

## What is this?

An AI-powered embeddable chat widget with RAG (Retrieval-Augmented Generation) support. Think of it as a drop-in customer support solution that works on any website with a single script tag, powered by multiple AI providers and enhanced with semantic search over your API documentation.

## Core Value

- **For developers**: One-line integration, zero configuration hassle, multiple AI providers
- **For end users**: Clean, responsive chat interface with real-time AI responses and accurate information from documentation
- **For businesses**: Customizable branding, multiple AI provider support, RAG-powered accuracy, reduced hallucinations

## Key Features

### Chat Widget
- Script tag injection with lazy loading (widget loads only when clicked)
- Floating Action Button (FAB) UI with iframe isolation
- Streaming AI responses (token-by-token display)
- Multiple AI providers: AWS Bedrock, OpenAI, Gemini, Anthropic, Azure OpenAI, Cohere
- Session persistence across page loads
- Resizable and fullscreen modes
- Event-driven architecture for custom integrations
- 10+ preset themes with full CSS customization

### AI & RAG
- LangChain integration for unified AI provider interface
- Context-aware conversations with memory
- Streaming responses via Server-Sent Events
- RAG support with vector search
- Semantic search over API documentation
- Reduced hallucinations with grounded responses

### API Documentation Indexer
- Web crawler using Crawl4AI for LLM-optimized extraction
- Clean markdown output for AI applications
- Vector embeddings with multiple providers (Bedrock Titan, OpenAI, Cohere, HuggingFace)
- Qdrant vector database for efficient semantic search
- Configurable crawling depth and limits
- Async architecture for fast processing

## Architecture Philosophy

- **Frontend**: Vanilla JavaScript, iframe isolation for zero conflicts
- **Backend**: FastAPI with LangChain for unified AI provider interface
- **RAG Pipeline**: Crawl4AI → LangChain Embeddings → Qdrant → Semantic Search
- **Integration**: Minimal friction - one script tag, optional configuration
- **Extensibility**: Event system allows custom behavior without modifying core code
- **Provider Agnostic**: Factory pattern supports multiple AI and embedding providers
