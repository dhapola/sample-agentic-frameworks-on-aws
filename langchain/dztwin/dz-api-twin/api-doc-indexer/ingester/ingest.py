import json
import argparse
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict
from tqdm.asyncio import tqdm as async_tqdm
from concurrent.futures import ThreadPoolExecutor
from embedder import create_embedder
from vector_store import VectorStore
from config import config


def load_documents(data_path: str) -> List[Dict]:
    """Load documents from crawler output"""
    data_dir = Path(data_path)
    index_file = data_dir / "index.json"
    
    if not index_file.exists():
        raise FileNotFoundError(f"Index file not found: {index_file}")
    
    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)
    
    documents = []
    for entry in index:
        file_path = data_dir / entry["file"]
        with open(file_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
            documents.append(doc)
    
    return documents


def chunk_documents(documents: List[Dict], max_chars: int = 1500) -> List[Dict]:
    """Split long documents into chunks
    
    Args:
        max_chars: Max characters per chunk (roughly 375 tokens for 4:1 char:token ratio)
                   Bedrock Titan has 8192 token limit, using 1500 chars (~375 tokens) for safety
    """
    chunks = []
    
    for doc in documents:
        content = doc.get("content", "").strip()
        
        # Skip documents with no content
        if not content:
            continue
        
        # If content is small enough, add as-is
        if len(content) <= max_chars:
            chunks.append({**doc, "content": content})
            continue
        
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        current_chunk = ""
        
        for para in paragraphs:
            # If paragraph itself is too long, split by sentences
            if len(para) > max_chars:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append({**doc, "content": current_chunk.strip()})
                    current_chunk = ""
                
                # Split paragraph into sentences
                sentences = [s.strip() + "." for s in para.split(". ") if s.strip()]
                
                for sentence in sentences:
                    # If single sentence is too long, force split by words
                    if len(sentence) > max_chars:
                        if current_chunk:
                            chunks.append({**doc, "content": current_chunk.strip()})
                            current_chunk = ""
                        
                        # Force split by words
                        words = sentence.split()
                        for word in words:
                            if len(current_chunk) + len(word) + 1 <= max_chars:
                                current_chunk += word + " "
                            else:
                                if current_chunk:
                                    chunks.append({**doc, "content": current_chunk.strip()})
                                current_chunk = word + " "
                        continue
                    
                    # Add sentence to current chunk
                    if len(current_chunk) + len(sentence) + 1 <= max_chars:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append({**doc, "content": current_chunk.strip()})
                        current_chunk = sentence + " "
                continue
            
            # Normal paragraph processing
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append({**doc, "content": current_chunk.strip()})
                current_chunk = para + "\n\n"
        
        # Save final chunk
        if current_chunk:
            chunks.append({**doc, "content": current_chunk.strip()})
    
    return chunks


def batch_process(items: List, batch_size: int):
    """Yield batches of items"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def generate_point_id(content: str, url: str) -> str:
    """Generate unique ID for a point based on content and URL"""
    unique_str = f"{url}:{content[:100]}"
    return hashlib.md5(unique_str.encode()).hexdigest()


async def process_batch_async(batch: List[Dict], embedder, vector_store, executor) -> tuple[int, int]:
    """Process a single batch asynchronously"""
    # Filter valid chunks
    valid_chunks = []
    skipped = 0
    
    for chunk in batch:
        content = chunk["content"].strip()
        # Skip empty content
        if not content:
            skipped += 1
            continue
        # Skip overly long chunks (should not happen with proper chunking, but safety check)
        # Bedrock Titan limit: 8192 tokens, ~32k chars. Use 6000 chars (~1500 tokens) as safe limit
        if len(content) > 6000:
            skipped += 1
            continue
        valid_chunks.append(chunk)
    
    if not valid_chunks:
        return 0, skipped
    
    try:
        # Run embedding in thread pool (since LangChain is sync)
        texts = [chunk["content"] for chunk in valid_chunks]
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(executor, embedder.embed_documents, texts)
        
        # Add to vector store (also in thread pool)
        await loop.run_in_executor(executor, vector_store.add_documents_with_ids, valid_chunks, vectors)
        
        return len(valid_chunks), skipped
    except Exception as e:
        error_msg = str(e)
        if "Too many input tokens" in error_msg or "ValidationException" in error_msg:
            # Process individually
            stored = 0
            for chunk in valid_chunks:
                try:
                    text = chunk["content"]
                    if len(text) > 6000:
                        skipped += 1
                        continue
                    vector = await loop.run_in_executor(executor, embedder.embed_documents, [text])
                    await loop.run_in_executor(executor, vector_store.add_documents_with_ids, [chunk], vector)
                    stored += 1
                except Exception:
                    skipped += 1
            return stored, skipped
        else:
            # Log error and skip batch
            print(f"\nError processing batch: {str(e)[:200]}")
            return 0, len(valid_chunks)


async def main_async(append: bool):
    """Async main function"""
async def main_async(append: bool):
    """Async main function"""
    print("Loading documents...")
    documents = load_documents(config.CRAWLER_DATA_PATH)
    print(f"Loaded {len(documents)} documents")
    
    print("Chunking documents...")
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
    
    # Analyze chunk sizes for diagnostics
    empty_chunks = sum(1 for c in chunks if not c.get("content", "").strip())
    if empty_chunks > 0:
        print(f"Warning: Found {empty_chunks} empty chunks")
    
    chunk_sizes = [len(c.get("content", "")) for c in chunks if c.get("content", "").strip()]
    if chunk_sizes:
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        max_size = max(chunk_sizes)
        print(f"Chunk size stats: avg={avg_size:.0f} chars, max={max_size} chars")
    
    print("Initializing embedder...")
    embedder = create_embedder(config)
    
    print("Initializing vector store...")
    vector_store = VectorStore(config)
    
    if not append:
        if vector_store.collection_exists():
            print("Deleting existing collection...")
            vector_store.delete_collection()
        print("Creating collection...")
        vector_store.create_collection(config.EMBEDDING_DIMENSION)
    
    print("Generating embeddings and storing...")
    
    # Create thread pool for sync operations
    max_workers = min(config.MAX_CONCURRENT_BATCHES, 10)
    executor = ThreadPoolExecutor(max_workers=max_workers)
    
    # Prepare batches
    batches = list(batch_process(chunks, config.BATCH_SIZE))
    
    # Process batches with controlled concurrency
    total_stored = 0
    total_skipped = 0
    
    # Use semaphore to limit concurrent API calls
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_BATCHES)
    
    async def process_with_semaphore(batch):
        async with semaphore:
            return await process_batch_async(batch, embedder, vector_store, executor)
    
    # Process all batches concurrently with progress bar
    tasks = [process_with_semaphore(batch) for batch in batches]
    
    # Use tqdm for async progress tracking
    results = []
    for coro in async_tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing batches"):
        result = await coro
        results.append(result)
    
    # Sum up results
    for stored, skipped in results:
        total_stored += stored
        total_skipped += skipped
    
    executor.shutdown(wait=True)
    
    print(f"\nIngestion complete!")
    print(f"Total documents stored: {total_stored}")
    if total_skipped > 0:
        print(f"Skipped documents: {total_skipped}")
        skip_rate = (total_skipped / len(chunks)) * 100
        print(f"Skip rate: {skip_rate:.1f}%")
        if skip_rate > 30:
            print(f"⚠️  High skip rate detected. Possible causes:")
            print(f"   - Empty chunks from crawler output")
            print(f"   - Duplicate content (hash-based IDs prevent duplicates)")
            print(f"   - Content validation failures")
    
    # Get collection info
    if vector_store.collection_exists():
        info = vector_store.get_collection_info()
        print(f"Collection: {config.QDRANT_COLLECTION_NAME}")
        print(f"Points: {info.points_count:,}")
        print(f"Indexed vectors: {info.indexed_vectors_count:,}")
        print(f"Status: {info.status}")
    
    # Close vector store properly
    vector_store.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest API documentation into vector store")
    parser.add_argument("--append", action="store_true", help="Append to existing collection")
    args = parser.parse_args()
    
    # Run async main
    asyncio.run(main_async(args.append))


if __name__ == "__main__":
    main()
