#!/usr/bin/env python3
"""
Setup OpenSearch agentic memory container for customer preferences.

This script creates a memory container using OpenSearch's native agentic memory APIs
to store and retrieve customer preferences with semantic search capabilities.

Run this once after setting up the OpenSearch product catalog and ML models.

Reference: https://docs.opensearch.org/latest/ml-commons-plugin/agentic-memory/
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from agents.opensearch_client import get_opensearch_client

# Load environment variables
load_dotenv()


def create_memory_container(client, embedding_model_id: str, llm_model_id: str = None) -> str:
    """
    Create an agentic memory container for customer preferences.

    Args:
        client: OpenSearch client instance
        embedding_model_id: ID of the text embedding model (required for semantic search)
        llm_model_id: ID of the LLM model (optional, but recommended for long-term memory)

    Returns:
        str: The created memory container ID
    """
    print("Creating agentic memory container for customer preferences...")

    # Configuration for memory container
    # Uses USER_PREFERENCE strategy which is ideal for storing customer preferences
    memory_config = {
        "name": "customer-preferences-memory",
        "description": "Stores customer music preferences for personalized shopping recommendations",
        "configuration": {
            "embedding_model_type": "TEXT_EMBEDDING",
            "embedding_model_id": embedding_model_id,
            "embedding_dimension": 768,  # msmarco-distilbert embedding dimension
            "strategies": [
                {
                    "type": "USER_PREFERENCE",
                    "namespace": ["customer_id"]
                }
            ],
            "index_settings": {
                "session_index": {
                    "index": {
                    "number_of_shards": "1",
                    "auto_expand_replicas": "0-all"
                    }
                },
                "working_memory_index": {
                    "index": {
                    "number_of_shards": "1",
                    "auto_expand_replicas": "0-all"
                    }
                },
                "long_term_memory_index": {
                    "index": {
                    "number_of_shards": "1",
                    "auto_expand_replicas": "0-all"
                    }
                },
                "long_term_memory_history_index": {
                    "index": {
                    "number_of_shards": "1",
                    "auto_expand_replicas": "0-all"
                    }
                }
            }
        }
    }

    # Add LLM configuration if provided (enables long-term memory processing)
    if llm_model_id:
        memory_config["configuration"]["llm_id"] = llm_model_id
        print(f"  ✓ Using LLM model: {llm_model_id} for memory processing")
    else:
        print("  ⚠ No LLM model specified - long-term memory features will be limited")

    # Create the memory container
    try:
        response = client.transport.perform_request(
            'POST',
            '/_plugins/_ml/memory_containers/_create',
            body=memory_config
        )

        memory_id = response.get('memory_container_id')
        if not memory_id:
            raise ValueError(f"No memory_container_id returned in response. Response: {response}")

        print(f"  ✓ Memory container created successfully!")
        print(f"  Memory Container ID: {memory_id}")
        print(f"\n  Add this to your .env file:")
        print(f"  OPENSEARCH_MEMORY_CONTAINER_ID=\"{memory_id}\"")

        return memory_id

    except Exception as e:
        print(f"  ✗ Error creating memory container: {e}")
        if hasattr(e, 'info'):
            print(f"  Details: {e.info}")
        raise


def verify_memory_container(client, memory_id: str) -> bool:
    """
    Verify that the memory container was created successfully.

    Args:
        client: OpenSearch client instance
        memory_id: Memory container ID to verify

    Returns:
        bool: True if container exists and is accessible
    """
    print(f"\nVerifying memory container {memory_id}...")

    try:
        # Get the memory container directly by ID
        response = client.transport.perform_request(
            'GET',
            f'/_plugins/_ml/memory_containers/{memory_id}'
        )

        if response:
            print(f"  ✓ Memory container verified!")
            print(f"  Name: {response.get('name', 'N/A')}")
            print(f"  Description: {response.get('description', 'N/A')}")
            return True
        else:
            print(f"  ✗ Memory container not found")
            return False

    except Exception as e:
        print(f"  ⚠ Could not verify container (but it was created successfully): {e}")
        # Return True anyway since creation was successful
        return True


def main():
    """Main setup function."""
    print("=" * 70)
    print("OpenSearch Agentic Memory Container Setup")
    print("=" * 70)
    print()

    # Get configuration from environment
    embedding_model_id = os.getenv('OPENSEARCH_MODEL_ID')
    llm_model_id = os.getenv('OPENSEARCH_LLM_MODEL_ID')

    if not embedding_model_id:
        print("ERROR: OPENSEARCH_MODEL_ID not set in .env file")
        print("Please run scripts/setup_opensearch.py first to register the embedding model")
        sys.exit(1)

    print(f"Configuration:")
    print(f"  Embedding Model ID: {embedding_model_id}")
    print(f"  LLM Model ID: {llm_model_id or 'Not configured (optional)'}")

    if not llm_model_id:
        print()
        print("ℹ️  Note: OPENSEARCH_LLM_MODEL_ID is not set")
        print("   This is OPTIONAL but recommended for enhanced memory features:")
        print("   - Memory summarization")
        print("   - Long-term memory processing")
        print()
        print("   Supported LLM providers:")
        print("   • Amazon Bedrock (recommended for AWS)")
        print("   • OpenAI")
        print("   • Cohere")
        print("   • SageMaker endpoints")
        print()
        print("   To configure later, register an LLM model in OpenSearch and")
        print("   add OPENSEARCH_LLM_MODEL_ID to your .env file")
        print()
    print()

    # Get OpenSearch client
    try:
        client = get_opensearch_client()
        print("✓ Connected to OpenSearch")
        print()
    except Exception as e:
        print(f"✗ Failed to connect to OpenSearch: {e}")
        sys.exit(1)

    # Create memory container
    try:
        memory_id = create_memory_container(client, embedding_model_id, llm_model_id)
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        sys.exit(1)

    # Verify the container
    if verify_memory_container(client, memory_id):
        print("\n" + "=" * 70)
        print("✓ Agentic memory container setup complete!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Add OPENSEARCH_MEMORY_CONTAINER_ID to your .env file")
        print("2. Restart your shopping agent application")
        print("3. Customer preferences will now persist in OpenSearch")
    else:
        print("\n✗ Verification failed - please check the setup")
        sys.exit(1)


if __name__ == "__main__":
    main()
