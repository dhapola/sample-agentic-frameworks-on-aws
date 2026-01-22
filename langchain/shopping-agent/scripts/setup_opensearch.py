"""
Complete OpenSearch setup script for shopping agent.
Sets up ML model, ingest pipeline, and product index.
Compatible with both local Docker and Amazon OpenSearch Service 3.1.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.opensearch_client import (
    get_opensearch_client,
    register_and_deploy_model,
    create_product_ingest_pipeline,
    create_product_index,
    test_connection
)
from dotenv import load_dotenv

load_dotenv()


def update_env_file(model_id: str):
    """
    Update .env file with the deployed model ID.

    Args:
        model_id: The deployed ML model ID
    """
    env_path = os.path.join(os.path.dirname(__file__), '../.env')

    if not os.path.exists(env_path):
        print(f"⚠ .env file not found at {env_path}")
        print(f"  Please manually add: OPENSEARCH_MODEL_ID={model_id}")
        return

    # Read existing content
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Update or add MODEL_ID
    model_id_line = f"OPENSEARCH_MODEL_ID={model_id}\n"
    updated = False

    for i, line in enumerate(lines):
        if line.startswith('OPENSEARCH_MODEL_ID='):
            lines[i] = model_id_line
            updated = True
            break

    if not updated:
        lines.append(model_id_line)

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(lines)

    print(f"✓ Updated .env with OPENSEARCH_MODEL_ID={model_id}")


def main():
    """Main setup execution"""

    print("="*70)
    print("OpenSearch Shopping Agent Setup")
    print("="*70)

    # Step 1: Test connection
    print("\n1. Testing OpenSearch connection...")
    if not test_connection():
        print("\n✗ Setup failed: Cannot connect to OpenSearch")
        print("\nPlease verify:")
        print("  - OpenSearch is running (docker-compose up -d for local)")
        print("  - Environment variables are set correctly in .env")
        print("  - Network connectivity for Amazon OpenSearch Service")
        sys.exit(1)

    # Step 2: Get client
    client = get_opensearch_client()
    info = client.info()
    print(f"\n✓ Connected to OpenSearch {info['version']['number']}")
    print(f"  Cluster: {info.get('cluster_name')}")

    # Step 3: Check ML Commons plugin
    print("\n2. Checking ML Commons plugin...")
    try:
        plugins = client.cat.plugins(format='json')
        ml_plugin_found = any(
            'ml-commons' in str(plugin).lower() or 'opensearch-ml' in str(plugin).lower()
            for plugin in plugins
        )

        if ml_plugin_found:
            print("✓ ML Commons plugin is available")
        else:
            print("⚠ ML Commons plugin not detected")
            print("  This is required for neural search functionality")
            print("  Continuing anyway - it may be available...")
    except Exception as e:
        print(f"⚠ Could not verify ML Commons plugin: {e}")
        print("  Continuing anyway...")

    # Step 4: Register and deploy ML model
    print("\n3. Registering and deploying ML model...")
    print("  This may take several minutes...")

    try:
        model_id, vector_dim = register_and_deploy_model(client)
        print(f"✓ Model deployed successfully")
        print(f"  Model ID: {model_id}")
        print(f"  Vector dimension: {vector_dim}")

        # Update .env file
        update_env_file(model_id)

    except Exception as e:
        print(f"\n✗ Model deployment failed: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure cluster has sufficient memory (>2GB)")
        print("  - Check ML Commons plugin is properly installed")
        print("  - For AWS OpenSearch, ensure ML node type is configured")
        sys.exit(1)

    # Step 5: Create ingest pipeline
    print("\n4. Creating ingest pipeline...")
    try:
        pipeline_name = create_product_ingest_pipeline(client, model_id)
        print(f"✓ Ingest pipeline created: {pipeline_name}")
    except Exception as e:
        print(f"\n✗ Pipeline creation failed: {e}")
        sys.exit(1)

    # Step 6: Create product index
    print("\n5. Creating product index...")
    try:
        index_name = create_product_index(client, vector_dim)
        print(f"✓ Product index created: {index_name}")
    except Exception as e:
        print(f"\n✗ Index creation failed: {e}")
        sys.exit(1)

    # Step 7: Verify setup
    print("\n6. Verifying setup...")
    try:
        # Check index exists
        if client.indices.exists(index=index_name):
            print(f"✓ Index {index_name} exists")

        # Check pipeline exists
        pipeline = client.ingest.get_pipeline(id=pipeline_name)
        if pipeline:
            print(f"✓ Pipeline {pipeline_name} exists")

        # Check model status
        model_status = client.transport.perform_request(
            'GET',
            f'/_plugins/_ml/models/{model_id}'
        )
        if model_status.get('model_state') == 'DEPLOYED':
            print(f"✓ Model {model_id} is deployed and ready")

    except Exception as e:
        print(f"⚠ Verification had warnings: {e}")

    # Success!
    print("\n" + "="*70)
    print("✓ OpenSearch setup complete!")
    print("="*70)
    print(f"\nNext steps:")
    print(f"  1. Run: python scripts/load_products_to_opensearch.py")
    print(f"  2. This will load the product catalog into OpenSearch")
    print(f"  3. Then you can test the shopping agent")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
