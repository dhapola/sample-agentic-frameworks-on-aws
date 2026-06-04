# API Documentation Ingester

Vector embeddings and semantic search for API documentation using LangChain and Qdrant.

## Features

- **Multiple embedding providers** - Bedrock Titan, OpenAI, Cohere, HuggingFace
- **LangChain integration** - Unified embedding interface
- **Qdrant vector database** - Efficient similarity search
- **Batch processing** - Fast parallel embedding generation
- **Document chunking** - Handles long documents
- **Embedded or server mode** - Flexible deployment
- **Semantic search** - Natural language queries
- **Configurable dimensions** - Provider-specific vector sizes
- **Clean-up option** - Fresh start or append mode

## Quick Setup

### Step 1: Install and Start Qdrant

See [QDRANT_SETUP.md](QDRANT_SETUP.md) for detailed instructions.

**Quick start with Finch (macOS):**
```bash
brew install finch
finch vm init
finch run -d -p 6333:6333 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Or with Docker:**
```bash
docker run -d -p 6333:6333 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Verify Qdrant is running:**
```bash
python test_qdrant.py
```

### Step 2: Install Python Dependencies

```bash
./setup.sh  # Unix/macOS
# or
setup.bat   # Windows
```

This will:
1. Install Python dependencies
2. Copy `.env.example` to `.env` (if needed)

## Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

## Qdrant Installation

Before running the ingester, you need to install and configure Qdrant vector database. You can use either **Finch** (Docker alternative for macOS) or **Docker**.

### Option 1: Using Finch (Recommended for macOS)

Finch is a lightweight, open-source container runtime that's an excellent Docker alternative for macOS.

#### Install Finch

```bash
# macOS (using Homebrew)
brew install finch

# Or download from GitHub
# https://github.com/runfinch/finch/releases
```

#### Initialize Finch (First Time Only)

```bash
finch vm init
```

This creates the Finch VM. You only need to do this once.

#### Start Qdrant with Finch

```bash
# Pull and run Qdrant
finch run -d \
  -p 6333:6333 \
  -p 6334:6334 \
  --name qdrant \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

**Explanation:**
- `-d` - Run in detached mode (background)
- `-p 6333:6333` - HTTP API port
- `-p 6334:6334` - gRPC port (optional)
- `--name qdrant` - Container name
- `-v qdrant_storage:/qdrant/storage` - Persistent volume for data
- `qdrant/qdrant` - Official Qdrant image

#### Verify Qdrant is Running

```bash
# Check container status
finch ps

# Expected output:
# CONTAINER ID   IMAGE            STATUS    PORTS                    NAMES
# abc123...      qdrant/qdrant    Up        0.0.0.0:6333->6333/tcp   qdrant

# Test HTTP API
curl http://localhost:6333/

# Or open in browser
open http://localhost:6333/dashboard
```

#### Manage Qdrant with Finch

```bash
# Stop Qdrant
finch stop qdrant

# Start Qdrant (if stopped)
finch start qdrant

# Restart Qdrant
finch restart qdrant

# View logs
finch logs qdrant
finch logs -f qdrant  # Follow logs

# Remove container (data persists in volume)
finch stop qdrant
finch rm qdrant

# Remove container AND data
finch stop qdrant
finch rm qdrant
finch volume rm qdrant_storage
```

---

### Option 2: Using Docker

If you prefer Docker or are on Linux/Windows:

#### Install Docker

- **macOS/Windows**: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: [Docker Engine](https://docs.docker.com/engine/install/)

#### Start Qdrant with Docker

```bash
# Pull and run Qdrant
docker run -d \
  -p 6333:6333 \
  -p 6334:6334 \
  --name qdrant \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

#### Verify Qdrant is Running

```bash
# Check container status
docker ps

# Test HTTP API
curl http://localhost:6333/

# Open dashboard
open http://localhost:6333/dashboard  # macOS
# or visit http://localhost:6333/dashboard in browser
```

#### Manage Qdrant with Docker

```bash
# Stop Qdrant
docker stop qdrant

# Start Qdrant (if stopped)
docker start qdrant

# Restart Qdrant
docker restart qdrant

# View logs
docker logs qdrant
docker logs -f qdrant  # Follow logs

# Remove container (data persists in volume)
docker stop qdrant
docker rm qdrant

# Remove container AND data
docker stop qdrant
docker rm qdrant
docker volume rm qdrant_storage
```

---

### Option 3: Using Docker Compose

For easier management, use Docker Compose:

#### Create `docker-compose.yml`

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC (optional)
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped
    environment:
      # Optional: Configure Qdrant
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334

volumes:
  qdrant_storage:
    driver: local
```

#### Manage with Docker Compose

```bash
# Start Qdrant
docker-compose up -d

# Stop Qdrant
docker-compose down

# View logs
docker-compose logs -f qdrant

# Restart Qdrant
docker-compose restart

# Remove everything (including data)
docker-compose down -v
```

---

### Option 4: Qdrant Cloud (Managed Service)

For production deployments, consider [Qdrant Cloud](https://cloud.qdrant.io/):

1. Sign up at https://cloud.qdrant.io/
2. Create a cluster
3. Get your cluster URL and API key
4. Configure in `.env`:

```env
QDRANT_USE_EMBEDDED=false
QDRANT_URL=https://xyz-abc123.cloud.qdrant.io
QDRANT_API_KEY=your-api-key-here
```

**Pros:**
- Managed service (no maintenance)
- High availability
- Automatic scaling
- Built-in monitoring

**Cons:**
- Usage costs
- Data leaves your infrastructure

---

### Verify Qdrant Installation

After starting Qdrant, verify it's working:

```bash
# Test with Python
python -c "
from qdrant_client import QdrantClient
client = QdrantClient(url='http://localhost:6333')
print('✓ Qdrant is running!')
print(f'Collections: {client.get_collections()}')
"
```

**Expected output:**
```
✓ Qdrant is running!
Collections: CollectionsResponse(collections=[])
```

Or use the test script:

```bash
python test_qdrant.py
```

---

### Troubleshooting Qdrant Installation

#### Port Already in Use

```bash
# Check what's using port 6333
lsof -i :6333

# Kill the process or use different port
finch run -d -p 6335:6333 --name qdrant qdrant/qdrant

# Update .env
QDRANT_URL=http://localhost:6335
```

#### Container Won't Start

```bash
# Check logs
finch logs qdrant
# or
docker logs qdrant

# Common issues:
# 1. Port conflict - use different port
# 2. Insufficient memory - increase Docker/Finch memory
# 3. Volume permission issues - check volume permissions
```

#### Connection Refused

```bash
# Verify container is running
finch ps
# or
docker ps

# Check if port is exposed
finch port qdrant
# or
docker port qdrant

# Test connection
curl http://localhost:6333/
```

#### Finch VM Issues (macOS)

```bash
# Check VM status
finch vm status

# Restart VM
finch vm stop
finch vm start

# Recreate VM (if corrupted)
finch vm remove
finch vm init
```

#### Data Persistence Issues

```bash
# Check volume exists
finch volume ls
# or
docker volume ls

# Inspect volume
finch volume inspect qdrant_storage
# or
docker volume inspect qdrant_storage

# Backup volume data
finch run --rm -v qdrant_storage:/data -v $(pwd):/backup alpine tar czf /backup/qdrant_backup.tar.gz /data
```

---

### Qdrant Configuration Options

You can customize Qdrant behavior with environment variables:

```bash
finch run -d \
  -p 6333:6333 \
  --name qdrant \
  -v qdrant_storage:/qdrant/storage \
  -e QDRANT__SERVICE__HTTP_PORT=6333 \
  -e QDRANT__SERVICE__GRPC_PORT=6334 \
  -e QDRANT__LOG_LEVEL=INFO \
  qdrant/qdrant
```

**Common options:**
- `QDRANT__LOG_LEVEL` - Logging level (DEBUG, INFO, WARN, ERROR)
- `QDRANT__SERVICE__MAX_REQUEST_SIZE_MB` - Max request size (default: 32)
- `QDRANT__STORAGE__PERFORMANCE__MAX_SEARCH_THREADS` - Search threads

See [Qdrant Configuration](https://qdrant.tech/documentation/guides/configuration/) for all options.

---

### Production Deployment Recommendations

For production use:

1. **Use Server Mode** (not embedded):
   ```env
   QDRANT_USE_EMBEDDED=false
   QDRANT_URL=http://localhost:6333
   ```

2. **Enable Persistence**:
   - Always use volumes (`-v qdrant_storage:/qdrant/storage`)
   - Backup volumes regularly

3. **Resource Limits**:
   ```bash
   finch run -d \
     -p 6333:6333 \
     --name qdrant \
     -v qdrant_storage:/qdrant/storage \
     --memory="4g" \
     --cpus="2" \
     qdrant/qdrant
   ```

4. **Monitoring**:
   - Enable Qdrant metrics endpoint
   - Monitor container logs
   - Set up health checks

5. **Security**:
   - Use API keys for authentication
   - Restrict network access
   - Enable TLS for production

6. **High Availability**:
   - Consider Qdrant Cloud
   - Or set up Qdrant cluster
   - Use load balancer

---

## Configuration

### Environment Variables

Create `.env` file (copy from `.env.example`):

```env
# Embedding Provider (bedrock, openai, cohere, huggingface)
EMBEDDING_PROVIDER=bedrock
EMBEDDING_DIMENSION=1024

# AWS Bedrock (Default)
AWS_REGION=us-west-2
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# OpenAI (Optional)
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Cohere (Optional)
COHERE_API_KEY=...
COHERE_EMBEDDING_MODEL=embed-english-v3.0

# HuggingFace (Optional)
HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Qdrant Configuration
QDRANT_USE_EMBEDDED=false
QDRANT_URL=  # Leave empty for embedded mode
QDRANT_API_KEY=  # Optional for cloud/server mode
QDRANT_COLLECTION_NAME=api_docs

# Data Configuration
CRAWLER_DATA_PATH=../crawler/data
BATCH_SIZE=100

# Performance Configuration
# MAX_CONCURRENT_BATCHES: Number of batches to process concurrently
# Higher = faster but may hit rate limits. Start with 5, adjust based on your AWS limits.
MAX_CONCURRENT_BATCHES=5
```

### Configuration Options

#### Embedding Provider

- `EMBEDDING_PROVIDER` - Provider to use
  - `bedrock` (default) - AWS Bedrock Titan
  - `openai` - OpenAI embeddings
  - `cohere` - Cohere embeddings
  - `huggingface` - HuggingFace local models

- `EMBEDDING_DIMENSION` - Vector dimension
  - Must match provider's output dimension
  - See [Embedding Providers](#embedding-providers) section

#### Qdrant Configuration

- `QDRANT_USE_EMBEDDED` (default: `false`) - Use embedded Qdrant
  - `true` - Embedded mode (data in `./qdrant_storage/`)
  - `false` - Server mode (requires `QDRANT_URL`)

- `QDRANT_URL` - Qdrant server URL
  - Leave empty for embedded mode
  - Example: `http://localhost:6333`
  - For cloud: `https://xyz.cloud.qdrant.io`

- `QDRANT_API_KEY` - API key for cloud/server
  - Optional for local server
  - Required for Qdrant Cloud

- `QDRANT_COLLECTION_NAME` (default: `api_docs`) - Collection name
  - Alphanumeric and underscores only
  - Created automatically if doesn't exist

#### Data Configuration

- `CRAWLER_DATA_PATH` (default: `../crawler/data`) - Path to crawled data
  - Relative or absolute path
  - Must contain `index.json` and page files

- `BATCH_SIZE` (default: `100`) - Batch size for embedding
  - Higher = faster but more memory
  - Lower = slower but less memory
  - Recommended: 50-150 for most providers
  - Optimized for concurrent processing

- `MAX_CONCURRENT_BATCHES` (default: `5`) - Concurrent batch processing
  - Number of batches to process simultaneously
  - Higher = faster but may hit API rate limits
  - Lower = more stable, fewer throttling errors
  - Recommended: 3-10 depending on provider limits

## Embedding Providers

### AWS Bedrock (Default)

Uses AWS credentials from environment or IAM role.

```env
EMBEDDING_PROVIDER=bedrock
AWS_REGION=us-west-2
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
EMBEDDING_DIMENSION=1024
```

**Supported Models:**
- `amazon.titan-embed-text-v2:0` - 1024 dimensions (recommended)
- `amazon.titan-embed-text-v1` - 1536 dimensions
- `cohere.embed-english-v3` - 1024 dimensions
- `cohere.embed-multilingual-v3` - 1024 dimensions

**Pros:**
- No API key needed (uses AWS credentials)
- High quality embeddings
- Low latency
- Cost-effective

**Cons:**
- Requires AWS account
- Region-specific availability

### OpenAI

```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

**Supported Models:**
- `text-embedding-3-small` - 1536 dimensions (recommended)
- `text-embedding-3-large` - 3072 dimensions
- `text-embedding-ada-002` - 1536 dimensions (legacy)

**Pros:**
- High quality embeddings
- Well-documented
- Reliable

**Cons:**
- Requires API key
- Usage costs
- Rate limits

### Cohere

```env
EMBEDDING_PROVIDER=cohere
COHERE_API_KEY=...
COHERE_EMBEDDING_MODEL=embed-english-v3.0
EMBEDDING_DIMENSION=1024
```

**Supported Models:**
- `embed-english-v3.0` - 1024 dimensions (recommended)
- `embed-multilingual-v3.0` - 1024 dimensions
- `embed-english-light-v3.0` - 384 dimensions

**Pros:**
- Optimized for search
- Multilingual support
- Competitive pricing

**Cons:**
- Requires API key
- Less widely used

### HuggingFace

```env
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

**Supported Models:**
- `sentence-transformers/all-MiniLM-L6-v2` - 384 dimensions (fast)
- `sentence-transformers/all-mpnet-base-v2` - 768 dimensions (quality)
- `BAAI/bge-small-en-v1.5` - 384 dimensions
- `BAAI/bge-base-en-v1.5` - 768 dimensions

**Pros:**
- Free (runs locally)
- No API key needed
- Privacy (data stays local)
- Many models available

**Cons:**
- Slower than API-based
- Requires local compute
- Model download required

## Usage

### Ingest Documentation

```bash
# Clean and ingest (default - removes old data)
python ingest.py

# Append to existing data
python ingest.py --append
```

**Output:**
```
Loading documents...
Loaded 42 documents
Chunking documents...
Created 156 chunks
Initializing embedder...
Initializing vector store...
Creating collection...
Generating embeddings and storing...
Processing batches: 100%|████████| 5/5 [00:15<00:00,  3.12s/it]

Ingestion complete!
Total documents stored: 156
Collection: api_docs
Vectors: 156
```

### Search Documentation

```bash
# Basic search
python search.py "how to authenticate"

# Limit results
python search.py "create customer" --limit 10

# Detailed results
python search.py "error handling" --limit 5
```

**Output:**
```
Query: how to authenticate
Found 5 results:

[1] Score: 0.8542
URL: https://docs.stripe.com/api/authentication
Content: # Authentication

Authenticate your API requests by including your secret key...

[2] Score: 0.7891
URL: https://docs.stripe.com/api/errors
Content: # Errors

Stripe uses conventional HTTP response codes...
```

### Browse Collection

```bash
# Show collection statistics
python browse.py --stats

# List sample documents
python browse.py --list 10

# List all unique URLs
python browse.py --urls

# Search with browse tool
python browse.py --search "authentication" --limit 5
```

**Statistics Output:**
```
📊 Collection Statistics:

Collection Name: api_docs
Points Count: 16,226
Indexed Vectors: 14,696
Segments: 2
Status: green
Vector Size: 1024
Distance: Cosine
```

## How It Works

### Ingestion Pipeline

1. **Load Documents**
   - Read `index.json` from crawler output
   - Load all page JSON files
   - Extract content and metadata

2. **Chunk Documents**
   - Split long documents (>1000 chars)
   - Preserve paragraph boundaries
   - Maintain metadata (URL, title, depth)

3. **Generate Embeddings**
   - Process in batches (configurable)
   - Use selected embedding provider
   - Create vector representations

4. **Store in Qdrant**
   - Create collection (if needed)
   - Store vectors with metadata
   - Enable similarity search

### Search Process

1. **Query Embedding**
   - Generate embedding for search query
   - Use same provider as ingestion

2. **Similarity Search**
   - Search Qdrant for similar vectors
   - Use cosine similarity
   - Return top-k results

3. **Format Results**
   - Extract content and metadata
   - Sort by relevance score
   - Display with URLs

## Qdrant Modes

### Embedded Mode (Default)

Data stored locally in `./qdrant_storage/`:

```env
QDRANT_USE_EMBEDDED=false
```

**Pros:**
- No server setup needed
- Fast local access
- Simple deployment

**Cons:**
- Single process access
- Limited scalability
- No remote access

**Use for:**
- Development
- Testing
- Single-machine deployments

### Server Mode

Connect to Qdrant server:

```env
QDRANT_USE_EMBEDDED=false
QDRANT_URL=http://localhost:6333
```

**Pros:**
- Multi-client access
- Better scalability
- Remote access
- Production-ready

**Cons:**
- Requires server setup
- Network latency
- More complex deployment

**Use for:**
- Production
- Multi-user access
- Distributed systems

### Qdrant Cloud

Connect to Qdrant Cloud:

```env
QDRANT_USE_EMBEDDED=false
QDRANT_URL=https://xyz.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
```

**Pros:**
- Managed service
- High availability
- Automatic scaling
- No maintenance

**Cons:**
- Usage costs
- Network latency
- Data leaves premises

## Advanced Usage

### Custom Chunking

Edit `ingest.py` to customize chunking:

```python
def chunk_documents(documents: List[Dict], max_length: int = 1000):
    # Adjust max_length for your needs
    # Smaller = more precise search
    # Larger = more context
```

### Batch Size Tuning

Adjust based on your system:

```env
# Fast machine with lots of RAM
BATCH_SIZE=64

# Slower machine or limited RAM
BATCH_SIZE=16
```

### Collection Management

```python
from vector_store import VectorStore
from config import config

store = VectorStore(config)

# Check if collection exists
exists = store.collection_exists()

# Get collection info
info = store.get_collection_info()
print(f"Vectors: {info.vectors_count}")

# Delete collection
store.delete_collection()
```

## Integration with Backend

After ingestion, enable RAG in backend:

```bash
cd ../../backend
```

Update `backend/.env`:
```env
RAG_ENABLED=true
QDRANT_URL=http://localhost:6333  # Or empty for embedded
QDRANT_COLLECTION=api_docs
RAG_TOP_K=5
```

Restart backend:
```bash
./start.sh
```

See [backend README](../../backend/README.md) for details.

## Troubleshooting

### Embedding provider fails

**Symptoms:**
- Import errors
- Authentication errors
- Model not found

**Solutions:**
1. Check API keys in `.env`
2. Verify AWS credentials for Bedrock
3. Install provider-specific packages:
   ```bash
   pip install langchain-openai  # For OpenAI
   pip install langchain-cohere  # For Cohere
   pip install langchain-huggingface  # For HuggingFace
   ```

### Qdrant connection fails

**Symptoms:**
- Connection refused
- Timeout errors

**Solutions:**
1. Check `QDRANT_USE_EMBEDDED` setting
2. Verify Qdrant server is running:
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```
3. Check `QDRANT_URL` is correct
4. Verify network connectivity

### Out of memory

**Symptoms:**
- Process killed
- Memory errors

**Solutions:**
1. Reduce `BATCH_SIZE` (try 16 or 8)
2. Use smaller embedding model
3. Chunk documents more aggressively
4. Process fewer documents at once

### Search returns no results

**Symptoms:**
- Empty search results
- Low relevance scores

**Solutions:**
1. Verify ingestion completed successfully
2. Check collection exists and has vectors
3. Try different search queries
4. Verify embedding provider matches ingestion
5. Check `EMBEDDING_DIMENSION` is correct

### Dimension mismatch

**Symptoms:**
- "Dimension mismatch" error
- Vector size errors

**Solutions:**
1. Verify `EMBEDDING_DIMENSION` matches provider
2. Delete and recreate collection
3. Re-run ingestion with correct dimension

## Best Practices

### Embedding Provider Selection

- **Bedrock** - Best for AWS users, cost-effective
- **OpenAI** - Best quality, well-documented
- **Cohere** - Best for search optimization
- **HuggingFace** - Best for privacy, free

### Batch Size

- Start with default (32)
- Increase for faster processing (if RAM allows)
- Decrease if out of memory errors

### Chunking

- Default (1000 chars) works for most cases
- Smaller chunks = more precise search
- Larger chunks = more context

### Collection Management

- Use descriptive collection names
- Clean up old collections
- Monitor vector count
- Backup important collections

## File Structure

```
ingester/
├── embedder.py          # LangChain embedding providers
├── vector_store.py      # Qdrant integration
├── config.py            # Configuration management
├── ingest.py           # Main ingestion script
├── search.py           # Search CLI tool
├── requirements.txt     # Python dependencies
├── setup.sh/bat        # Setup scripts
├── .env.example        # Environment template
├── .env                # Local config (gitignored)
├── .gitignore          # Ignore storage and env files
├── __init__.py         # Package initialization
├── README.md           # This file
└── qdrant_storage/     # Vector DB storage (gitignored)
```

## Dependencies

- `qdrant-client` - Vector database client
- `langchain` + `langchain-core` - AI framework
- `langchain-aws` - AWS Bedrock embeddings
- `langchain-openai` - OpenAI embeddings (optional)
- `langchain-cohere` - Cohere embeddings (optional)
- `langchain-huggingface` - HuggingFace embeddings (optional)
- `boto3` - AWS SDK for Bedrock
- `python-dotenv` - Environment management
- `pydantic-settings` - Configuration validation
- `tqdm` - Progress bars

See [requirements.txt](requirements.txt) for complete list.

## Performance

### Optimization Features

The ingester uses async/concurrent processing for **12-24x faster** performance:

- **Async/concurrent processing** - Process 5 batches simultaneously (configurable)
- **Thread pool execution** - Non-blocking embedding generation with ThreadPoolExecutor
- **Optimized batch sizes** - 100 chunks per batch (reduced from 32)
- **Hash-based IDs** - MD5-based deterministic IDs prevent collisions
- **Semaphore control** - Prevents API rate limit throttling
- **Progress tracking** - Real-time async progress bars with tqdm

### Performance Metrics

| Dataset Size | Chunks | Time (Before) | Time (After) | Speedup |
|--------------|--------|---------------|--------------|---------|
| 100 docs | 600 | 20 min | 2 min | **10x** |
| 500 docs | 3000 | 1.5 hours | 8 min | **11x** |
| 826 docs | 4956 | 2-4 hours | 10-20 min | **12-24x** |
| 1000 docs | 6000 | 3 hours | 15 min | **12x** |
| 5000 docs | 30000 | 15 hours | 75 min | **12x** |

**Throughput:** ~100+ chunks/minute (up from ~7 chunks/minute)

### Performance Tuning

Run benchmark to estimate processing time:
```bash
python benchmark.py
```

**Configuration options:**

```env
# For maximum speed (if you have high AWS limits)
BATCH_SIZE=150
MAX_CONCURRENT_BATCHES=10

# For stability (if you see throttling errors)
BATCH_SIZE=50
MAX_CONCURRENT_BATCHES=3

# For large datasets (10k+ documents)
BATCH_SIZE=200
MAX_CONCURRENT_BATCHES=8
```

**Tuning guidelines:**
- Start with defaults (`BATCH_SIZE=100`, `MAX_CONCURRENT_BATCHES=5`)
- Increase `MAX_CONCURRENT_BATCHES` for faster processing (watch for throttling)
- Increase `BATCH_SIZE` to reduce API calls (watch for memory usage)
- Use Bedrock for best cost/performance ratio
- Monitor AWS CloudWatch for throttling metrics

### How Optimization Works

**Async Architecture:**
```python
# Old (sequential) - 2-4 hours
for batch in batches:
    vectors = embedder.embed_documents(texts)  # Blocks
    vector_store.add_documents(chunks, vectors)  # Blocks

# New (concurrent) - 10-20 minutes
async def process_batch_async(batch):
    vectors = await loop.run_in_executor(executor, embedder.embed_documents, texts)
    await loop.run_in_executor(executor, vector_store.add_documents_with_ids, chunks, vectors)

# Process 5 batches simultaneously
semaphore = asyncio.Semaphore(5)
tasks = [process_with_semaphore(batch) for batch in batches]
results = await asyncio.gather(*tasks)
```

**Hash-Based IDs:**
```python
# Old (collision-prone)
point = PointStruct(id=i, ...)  # i resets per batch!

# New (deterministic)
unique_str = f"{doc['url']}:{doc['content'][:100]}"
unique_id = int(hashlib.md5(unique_str.encode()).hexdigest()[:16], 16)
point = PointStruct(id=unique_id, ...)
```

### Troubleshooting Performance

**ThrottlingException from Bedrock:**
```env
MAX_CONCURRENT_BATCHES=3  # Reduce from 5
```

**Out of memory:**
```env
BATCH_SIZE=50  # Reduce from 100
MAX_CONCURRENT_BATCHES=3  # Reduce from 5
```

**Still slow after optimization:**
- Check network latency to AWS (use same region)
- Verify Qdrant mode (server mode recommended for production)
- Check document sizes (very large docs slow chunking)
- Monitor AWS CloudWatch for throttling

## Search & Browse

### Search Command

Search for documentation using semantic similarity:

```bash
# Basic search
python search.py "how to train a model"

# Search with more results
python search.py "deploy model" --limit 10

# Find authentication methods
python search.py "authentication methods" --limit 5
```

**Output:**
```
Searching for: how to train a model

Result 1 (Score: 0.8542)
Title: Training Guide
URL: https://docs.example.com/training
Content: To train a model, first prepare your dataset...
--------------------------------------------------------------------------------
Result 2 (Score: 0.7891)
...
```

### Browse Command

Explore and analyze the collection:

```bash
# Show collection statistics
python browse.py --stats

# List sample documents
python browse.py --list 10

# List all unique URLs
python browse.py --urls

# Search with browse tool
python browse.py --search "authentication" --limit 5
```

**Statistics output:**
```
📊 Collection Statistics:

Collection Name: api_docs
Points Count: 16,226
Indexed Vectors: 14,696
Segments: 2
Status: green
Vector Size: 1024
Distance: Cosine
```

### Understanding Search Results

**Score interpretation:**
- **0.7 - 1.0**: Highly relevant (exact or near-exact match)
- **0.5 - 0.7**: Very relevant (strong semantic match)
- **0.3 - 0.5**: Moderately relevant (related content)
- **0.0 - 0.3**: Weakly relevant (tangentially related)

**Tips for better searches:**
1. Use natural language: "how to deploy a model" works better than "deploy"
2. Be specific: "train PyTorch model" vs "train model"
3. Try variations: If results aren't good, rephrase your query
4. Adjust limit: Use `--limit 10` to see more results

### Search Troubleshooting

**"Collection does not exist":**
```bash
python ingest.py  # Run ingestion first
```

**No results found:**
- Try broader search terms
- Use different phrasing
- Check if the topic is in the crawled documentation

**Connection errors:**
```bash
finch ps  # Check if qdrant container is running
finch start qdrant  # Start if stopped
```

## Limitations

- **Embedding provider required** - Can't run without credentials
- **Memory intensive** - Large batches require RAM
- **Single collection** - One collection per configuration
- **No incremental updates** - Must re-ingest for updates

## Future Enhancements

- [ ] Incremental ingestion (only new/changed docs)
- [ ] Multiple collection support
- [ ] Hybrid search (vector + keyword)
- [ ] Metadata filtering
- [ ] Re-ranking
- [ ] Query expansion
- [ ] Caching
- [ ] Monitoring and metrics

## License

MIT
