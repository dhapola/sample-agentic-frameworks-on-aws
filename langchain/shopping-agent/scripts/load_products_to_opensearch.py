"""
Load products from YAML catalog into OpenSearch with automatic embeddings.
Works with both local Docker OpenSearch and Amazon OpenSearch Service 3.1.
"""

import os
import sys
import yaml
from pathlib import Path
from opensearchpy import helpers
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.opensearch_client import get_opensearch_client
from dotenv import load_dotenv

load_dotenv()


def load_products_from_yaml(yaml_path: str) -> list[dict]:
    """
    Load products from YAML file.

    Args:
        yaml_path: Path to products YAML file

    Returns:
        list: List of product dictionaries
    """
    print(f"Loading products from {yaml_path}...")

    with open(yaml_path, 'r') as f:
        products = yaml.safe_load(f)

    print(f"✓ Loaded {len(products)} products")
    return products


def prepare_bulk_actions(products: list[dict], index_name: str, pipeline_name: str) -> list[dict]:
    """
    Prepare bulk indexing actions with pipeline for embedding generation.

    Args:
        products: List of product dictionaries
        index_name: Target index name
        pipeline_name: Ingest pipeline name for embeddings

    Returns:
        list: Bulk indexing actions
    """
    print("Preparing bulk indexing actions...")

    actions = []
    for product in tqdm(products, desc="Preparing products"):
        action = {
            "_index": index_name,
            "_id": product.get('id', product.get('product_id')),  # Handle different ID fields
            "_source": product,
            "pipeline": pipeline_name  # Use pipeline for automatic embedding generation
        }
        actions.append(action)

    print(f"✓ Prepared {len(actions)} indexing actions")
    return actions


def bulk_index_products(
    client,
    actions: list[dict],
    chunk_size: int = 50,
    max_retries: int = 3
) -> tuple[int, list]:
    """
    Bulk index products into OpenSearch.

    Args:
        client: OpenSearch client
        actions: List of bulk actions
        chunk_size: Number of documents per bulk request
        max_retries: Maximum number of retries for failed documents

    Returns:
        tuple: (successful_count, failed_documents)
    """
    print(f"\nIndexing {len(actions)} products (chunk size: {chunk_size})...")

    try:
        success, failed = helpers.bulk(
            client,
            actions,
            chunk_size=chunk_size,
            request_timeout=120,
            max_retries=max_retries,
            raise_on_error=False,
            stats_only=False
        )

        print(f"\n✓ Successfully indexed: {success} products")

        if failed:
            print(f"✗ Failed to index: {len(failed)} products")
            print("\nFirst 5 failures:")
            for i, item in enumerate(failed[:5], 1):
                error_info = item.get('index', {}).get('error', 'Unknown error')
                doc_id = item.get('index', {}).get('_id', 'Unknown ID')
                print(f"  {i}. Document ID: {doc_id}")
                print(f"     Error: {error_info}")

        return success, failed

    except Exception as e:
        print(f"✗ Bulk indexing failed: {e}")
        raise


def verify_indexing(client, index_name: str, expected_count: int):
    """
    Verify that products were indexed correctly.

    Args:
        client: OpenSearch client
        index_name: Index to verify
        expected_count: Expected number of documents
    """
    print(f"\nVerifying index: {index_name}...")

    # Refresh index
    client.indices.refresh(index=index_name)

    # Get count
    count_response = client.count(index=index_name)
    actual_count = count_response['count']

    print(f"  Expected documents: {expected_count}")
    print(f"  Actual documents: {actual_count}")

    if actual_count == expected_count:
        print("✓ Index verification passed")
    else:
        print(f"⚠ Index count mismatch: {actual_count}/{expected_count}")

    # Get a sample document
    sample = client.search(
        index=index_name,
        body={"size": 1, "query": {"match_all": {}}}
    )

    if sample['hits']['hits']:
        doc = sample['hits']['hits'][0]['_source']
        print(f"\nSample product:")
        print(f"  ID: {doc.get('id')}")
        print(f"  Name: {doc.get('name')}")
        print(f"  Category: {doc.get('category')}")
        print(f"  Price: ${doc.get('price', 0):.2f}")
        print(f"  Has vector: {'product_vector' in doc}")

        if 'product_vector' in doc:
            vector_dim = len(doc['product_vector'])
            print(f"  Vector dimension: {vector_dim}")


def main():
    """Main execution function"""

    print("="*70)
    print("Product Data Ingestion to OpenSearch")
    print("="*70)

    # Configuration
    yaml_path = os.path.join(
        os.path.dirname(__file__),
        '../data/products-data.yml'
    )
    index_name = os.getenv('OPENSEARCH_INDEX_PRODUCTS', 'shopping_products')
    pipeline_name = "product_embedding_pipeline"

    # Step 1: Connect to OpenSearch
    print("\n1. Connecting to OpenSearch...")
    client = get_opensearch_client()
    info = client.info()
    print(f"✓ Connected to OpenSearch {info['version']['number']}")

    # Step 2: Load products
    print("\n2. Loading product catalog...")
    products = load_products_from_yaml(yaml_path)

    # Step 3: Prepare bulk actions
    print("\n3. Preparing indexing actions...")
    actions = prepare_bulk_actions(products, index_name, pipeline_name)

    # Step 4: Bulk index
    print("\n4. Indexing products...")
    success_count, failed = bulk_index_products(client, actions)

    # Step 5: Verify
    print("\n5. Verifying index...")
    verify_indexing(client, index_name, len(products))

    print("\n" + "="*70)
    print(f"✓ Product ingestion complete!")
    print(f"  Total products: {len(products)}")
    print(f"  Successfully indexed: {success_count}")
    print(f"  Failed: {len(failed) if failed else 0}")
    print("="*70)


if __name__ == "__main__":
    main()
