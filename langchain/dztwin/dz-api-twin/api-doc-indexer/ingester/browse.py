#!/usr/bin/env python3
"""
Browse and explore stored documents in Qdrant
"""
import argparse
from qdrant_client import QdrantClient
from embedder import create_embedder
from config import config


def list_documents(limit=10):
    """List sample documents"""
    client = QdrantClient(url=config.QDRANT_URL if not config.QDRANT_USE_EMBEDDED else None,
                         path="./qdrant_storage" if config.QDRANT_USE_EMBEDDED else None)
    
    results = client.scroll(
        collection_name=config.QDRANT_COLLECTION_NAME,
        limit=limit,
        with_payload=True,
        with_vectors=False
    )
    
    print(f"\n📄 Sample Documents (showing {len(results[0])} of {limit}):\n")
    for i, point in enumerate(results[0], 1):
        print(f"{i}. {point.payload.get('title', 'No title')}")
        print(f"   URL: {point.payload.get('url', 'N/A')}")
        print(f"   Content: {point.payload.get('content', '')[:150]}...")
        print()


def collection_stats():
    """Show collection statistics"""
    client = QdrantClient(url=config.QDRANT_URL if not config.QDRANT_USE_EMBEDDED else None,
                         path="./qdrant_storage" if config.QDRANT_USE_EMBEDDED else None)
    
    info = client.get_collection(config.QDRANT_COLLECTION_NAME)
    
    print("\n📊 Collection Statistics:\n")
    print(f"Collection Name: {config.QDRANT_COLLECTION_NAME}")
    print(f"Points Count: {info.points_count:,}")
    print(f"Indexed Vectors: {info.indexed_vectors_count:,}")
    print(f"Segments: {info.segments_count}")
    print(f"Status: {info.status}")
    print(f"Vector Size: {info.config.params.vectors.size}")
    print(f"Distance: {info.config.params.vectors.distance}")
    print()


def search_documents(query, limit=5):
    """Search documents by semantic similarity"""
    client = QdrantClient(url=config.QDRANT_URL if not config.QDRANT_USE_EMBEDDED else None,
                         path="./qdrant_storage" if config.QDRANT_USE_EMBEDDED else None)
    
    embedder = create_embedder(config)
    query_vector = embedder.embed_query(query)
    
    results = client.query_points(
        collection_name=config.QDRANT_COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True
    )
    
    print(f"\n🔍 Search Results for: '{query}'\n")
    for i, result in enumerate(results.points, 1):
        print(f"{i}. Score: {result.score:.4f}")
        print(f"   Title: {result.payload.get('title', 'No title')}")
        print(f"   URL: {result.payload.get('url', 'N/A')}")
        print(f"   Content: {result.payload.get('content', '')[:200]}...")
        print()


def list_urls():
    """List all unique URLs in the collection"""
    client = QdrantClient(url=config.QDRANT_URL if not config.QDRANT_USE_EMBEDDED else None,
                         path="./qdrant_storage" if config.QDRANT_USE_EMBEDDED else None)
    
    results = client.scroll(
        collection_name=config.QDRANT_COLLECTION_NAME,
        limit=1000,
        with_payload=['url'],
        with_vectors=False
    )
    
    urls = sorted(set(point.payload['url'] for point in results[0]))
    
    print(f"\n🔗 Unique URLs ({len(urls)} total):\n")
    for url in urls:
        print(f"  • {url}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Browse stored documents in Qdrant")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    parser.add_argument("--list", type=int, metavar="N", help="List N sample documents")
    parser.add_argument("--urls", action="store_true", help="List all unique URLs")
    parser.add_argument("--search", type=str, metavar="QUERY", help="Search documents")
    parser.add_argument("--limit", type=int, default=5, help="Number of search results (default: 5)")
    
    args = parser.parse_args()
    
    if args.stats:
        collection_stats()
    elif args.list:
        list_documents(args.list)
    elif args.urls:
        list_urls()
    elif args.search:
        search_documents(args.search, args.limit)
    else:
        # Default: show stats
        collection_stats()
        list_documents(5)


if __name__ == "__main__":
    main()
