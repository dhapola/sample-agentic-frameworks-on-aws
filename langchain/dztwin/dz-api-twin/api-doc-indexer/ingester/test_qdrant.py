#!/usr/bin/env python3
"""
Test Qdrant server connection and configuration
Run this after starting Qdrant to verify everything works
"""

import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def print_info(text):
    print(f"{BLUE}ℹ{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")

def test_qdrant_connection():
    """Test Qdrant server connection and functionality"""
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'Qdrant Connection Test'.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Test 1: Basic connection
    print_info("Test 1: Connecting to Qdrant server...")
    try:
        client = QdrantClient(url="http://localhost:6333")
        print_success("Connected to Qdrant at http://localhost:6333")
    except Exception as e:
        print_error(f"Failed to connect: {e}")
        print_info("Make sure Qdrant is running:")
        print_info("  finch run -d -p 6333:6333 --name qdrant qdrant/qdrant")
        print_info("  or")
        print_info("  docker run -d -p 6333:6333 --name qdrant qdrant/qdrant")
        return False
    
    # Test 2: List collections
    print_info("\nTest 2: Listing collections...")
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if collection_names:
            print_success(f"Found {len(collection_names)} collection(s):")
            for name in collection_names:
                print(f"  • {name}")
                
                # Get collection info
                try:
                    info = client.get_collection(name)
                    print(f"    - Points: {info.points_count}")
                except Exception as e:
                    print_warning(f"    - Could not get details: {e}")
        else:
            print_info("No collections found (this is normal for a fresh install)")
    except Exception as e:
        print_error(f"Failed to list collections: {e}")
        return False
    
    # Test 3: Create test collection
    print_info("\nTest 3: Creating test collection...")
    test_collection = "test_connection"
    
    try:
        # Delete if exists
        try:
            client.delete_collection(test_collection)
            print_info(f"Deleted existing '{test_collection}' collection")
        except:
            pass
        
        # Create new collection
        client.create_collection(
            collection_name=test_collection,
            vectors_config=models.VectorParams(
                size=384,  # Small dimension for testing
                distance=models.Distance.COSINE
            )
        )
        print_success(f"Created test collection '{test_collection}'")
    except Exception as e:
        print_error(f"Failed to create collection: {e}")
        return False
    
    # Test 4: Insert test vector
    print_info("\nTest 4: Inserting test vector...")
    try:
        test_vector = [0.1] * 384  # Simple test vector
        
        client.upsert(
            collection_name=test_collection,
            points=[
                models.PointStruct(
                    id=1,
                    vector=test_vector,
                    payload={"test": "data", "source": "connection_test"}
                )
            ]
        )
        print_success("Inserted test vector")
    except Exception as e:
        print_error(f"Failed to insert vector: {e}")
        return False
    
    # Test 5: Search test
    print_info("\nTest 5: Testing vector search...")
    try:
        results = client.query_points(
            collection_name=test_collection,
            query=test_vector,
            limit=1
        ).points
        
        if results and len(results) > 0:
            print_success(f"Search successful! Found {len(results)} result(s)")
            print(f"  • Score: {results[0].score}")
            print(f"  • Payload: {results[0].payload}")
        else:
            print_warning("Search returned no results")
    except Exception as e:
        print_error(f"Search failed: {e}")
        return False
    
    # Test 6: Clean up
    print_info("\nTest 6: Cleaning up test collection...")
    try:
        client.delete_collection(test_collection)
        print_success(f"Deleted test collection '{test_collection}'")
    except Exception as e:
        print_warning(f"Failed to delete test collection: {e}")
    
    # Summary
    print(f"\n{GREEN}{'='*60}{RESET}")
    print(f"{GREEN}{'All tests passed! ✓'.center(60)}{RESET}")
    print(f"{GREEN}{'='*60}{RESET}\n")
    
    print_info("Qdrant is ready for use!")
    print_info("Next steps:")
    print_info("  1. Configure .env file with QDRANT_URL=http://localhost:6333")
    print_info("  2. Run: python ingest.py")
    print_info("  3. Run: python search.py 'your query'")
    
    return True

if __name__ == "__main__":
    try:
        success = test_qdrant_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
