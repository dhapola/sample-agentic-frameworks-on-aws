import argparse
from embedder import create_embedder
from vector_store import VectorStore
from config import config


def main():
    parser = argparse.ArgumentParser(description="Search API documentation")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Number of results")
    args = parser.parse_args()
    
    print(f"Searching for: {args.query}\n")
    
    embedder = create_embedder(config)
    vector_store = VectorStore(config)
    
    if not vector_store.collection_exists():
        print("Error: Collection does not exist. Run ingest.py first.")
        return
    
    query_vector = embedder.embed_query(args.query)
    results = vector_store.search(query_vector, limit=args.limit)
    
    if not results:
        print("No results found.")
        return
    
    for i, result in enumerate(results, 1):
        print(f"Result {i} (Score: {result['score']:.4f})")
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Content: {result['content'][:200]}...")
        print("-" * 80)


if __name__ == "__main__":
    main()
