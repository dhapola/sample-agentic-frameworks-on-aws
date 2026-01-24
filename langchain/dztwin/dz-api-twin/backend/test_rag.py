#!/usr/bin/env python3
"""Test RAG service connection and search"""
import asyncio
from config import get_config
from rag_service import RAGService

async def test_rag():
    config = get_config()
    rag = RAGService(config)
    
    print(f"RAG Enabled: {rag.enabled}")
    
    if not rag.enabled:
        print("❌ RAG is not enabled")
        return
    
    print(f"Qdrant URL: {config.QDRANT_URL}")
    print(f"Collection: {config.QDRANT_COLLECTION}")
    print(f"Top K: {config.RAG_TOP_K}")
    
    # Check collection exists
    try:
        collections = rag.client.get_collections()
        print(f"\n✅ Connected to Qdrant")
        print(f"Available collections: {[c.name for c in collections.collections]}")
        
        if config.QDRANT_COLLECTION in [c.name for c in collections.collections]:
            info = rag.client.get_collection(config.QDRANT_COLLECTION)
            print(f"\n✅ Collection '{config.QDRANT_COLLECTION}' exists")
            print(f"Points count: {info.points_count}")
            print(f"Vector size: {info.config.params.vectors.size}")
        else:
            print(f"\n❌ Collection '{config.QDRANT_COLLECTION}' not found")
            print("Run the ingester to create and populate the collection:")
            print("  cd api-doc-indexer/ingester")
            print("  python ingest.py")
            return
    except Exception as e:
        print(f"\n❌ Failed to connect to Qdrant: {e}")
        return
    
    # Test search
    print("\n" + "="*60)
    print("Testing RAG search...")
    print("="*60)
    
    test_query = "how to deploy a model in sagemaker"
    print(f"\nQuery: {test_query}")
    
    try:
        context = await rag.search(test_query)
        if context:
            print(f"\n✅ Search successful!")
            print(f"Context length: {len(context)} characters")
            print(f"\nFirst 500 characters of context:")
            print("-" * 60)
            print(context[:500])
            print("-" * 60)
        else:
            print("\n⚠️  Search returned no results")
    except Exception as e:
        print(f"\n❌ Search failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag())
