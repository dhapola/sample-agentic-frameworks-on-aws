"""
OpenSearch client utilities for shopping agent.
Supports both local Docker OpenSearch and Amazon OpenSearch Service 3.1.
"""

import os
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
from dotenv import load_dotenv

load_dotenv()


def get_opensearch_client() -> OpenSearch:
    """
    Initialize OpenSearch client with environment configuration.
    Automatically detects and configures for either:
    - Local Docker OpenSearch (no auth)
    - Amazon OpenSearch Service 3.1 (with AWS IAM or basic auth)

    Returns:
        OpenSearch: Configured OpenSearch client
    """
    host = os.getenv('OPENSEARCH_HOST', 'localhost')
    port = int(os.getenv('OPENSEARCH_PORT', '9200'))
    use_ssl = os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true'
    verify_certs = os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true'
    username = os.getenv('OPENSEARCH_USERNAME', '')
    password = os.getenv('OPENSEARCH_PASSWORD', '')

    # Determine if we're using AWS OpenSearch Service
    # Safely check if the hostname (not arbitrary parts of URL) ends with AWS domains
    hostname = host if '://' not in host else urlparse(f'https://{host}' if not host.startswith(('http://', 'https://')) else host).hostname or host
    is_aws_opensearch = hostname.endswith('.es.amazonaws.com') or hostname.endswith('.aoss.amazonaws.com')

    if is_aws_opensearch:
        # Amazon OpenSearch Service configuration
        region = os.getenv('AWS_REGION_NAME', 'us-east-1')

        # Try AWS IAM authentication first
        if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
            credentials = boto3.Session(
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=region
            ).get_credentials()

            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                'es',
                session_token=credentials.token
            )

            return OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=60,
                max_retries=3,
                retry_on_timeout=True
            )

        # Fall back to basic auth if provided
        elif username and password:
            return OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_auth=(username, password),
                use_ssl=True,
                verify_certs=verify_certs,
                connection_class=RequestsHttpConnection,
                timeout=60,
                max_retries=3,
                retry_on_timeout=True
            )
        else:
            raise ValueError(
                "For Amazon OpenSearch Service, provide either AWS credentials "
                "(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) or basic auth "
                "(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)"
            )
    else:
        # Local Docker OpenSearch configuration
        auth = (username, password) if username and password else None

        return OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=auth,
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            connection_class=RequestsHttpConnection,
            timeout=60
        )


def register_and_deploy_model(client: OpenSearch) -> tuple[str, int]:
    """
    Register and deploy the sentence transformer model for neural search.
    Uses huggingface/sentence-transformers/msmarco-distilbert-base-tas-b
    which is optimized for semantic search.

    Args:
        client: OpenSearch client instance

    Returns:
        tuple: (model_id, vector_dimension)
    """
    MODEL_NAME = "huggingface/sentence-transformers/msmarco-distilbert-base-tas-b"
    MODEL_VERSION = "1.0.3"
    VECTOR_DIM = 768

    print(f"Registering model: {MODEL_NAME}...")

    # Step 1: Register the pretrained model
    register_body = {
        "name": MODEL_NAME,
        "version": MODEL_VERSION,
        "model_format": "TORCH_SCRIPT"
    }

    try:
        response = client.transport.perform_request(
            'POST',
            '/_plugins/_ml/models/_register',
            body=register_body
        )
        task_id = response.get('task_id')
        print(f"Model registration started. Task ID: {task_id}")
    except Exception as e:
        print(f"Error registering model: {e}")
        raise

    # Step 2: Wait for registration to complete
    print("Waiting for model registration to complete...")
    max_wait = 300  # 5 minutes max
    start_time = time.time()
    model_id = None

    while time.time() - start_time < max_wait:
        try:
            task_response = client.transport.perform_request(
                'GET',
                f'/_plugins/_ml/tasks/{task_id}'
            )
            state = task_response.get('state')

            if state == 'COMPLETED':
                model_id = task_response.get('model_id')
                print(f"✓ Model registered successfully. Model ID: {model_id}")
                break
            elif state == 'FAILED':
                error = task_response.get('error', 'Unknown error')
                raise RuntimeError(f"Model registration failed: {error}")

            print(f"  Registration status: {state}")
            time.sleep(5)
        except Exception as e:
            print(f"Error checking registration status: {e}")
            time.sleep(5)

    if not model_id:
        raise TimeoutError("Model registration timed out after 5 minutes")

    # Step 3: Deploy the model
    print(f"Deploying model {model_id}...")
    try:
        deploy_response = client.transport.perform_request(
            'POST',
            f'/_plugins/_ml/models/{model_id}/_deploy'
        )
        deploy_task_id = deploy_response.get('task_id')
        print(f"Model deployment started. Task ID: {deploy_task_id}")
    except Exception as e:
        print(f"Error deploying model: {e}")
        raise

    # Step 4: Wait for deployment to complete
    print("Waiting for model deployment to complete...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            task_response = client.transport.perform_request(
                'GET',
                f'/_plugins/_ml/tasks/{deploy_task_id}'
            )
            state = task_response.get('state')

            if state == 'COMPLETED':
                print(f"✓ Model deployed successfully")
                return model_id, VECTOR_DIM
            elif state == 'FAILED':
                error = task_response.get('error', 'Unknown error')
                raise RuntimeError(f"Model deployment failed: {error}")

            print(f"  Deployment status: {state}")
            time.sleep(5)
        except Exception as e:
            print(f"Error checking deployment status: {e}")
            time.sleep(5)

    raise TimeoutError("Model deployment timed out after 5 minutes")


def create_product_ingest_pipeline(client: OpenSearch, model_id: str) -> str:
    """
    Create ingest pipeline for automatic embedding generation.
    Combines product name, description, category, and style into searchable text.

    Args:
        client: OpenSearch client instance
        model_id: ID of the deployed ML model

    Returns:
        str: Pipeline name
    """
    pipeline_name = "product_embedding_pipeline"

    pipeline_body = {
        "description": "Pipeline for product catalog embeddings",
        "processors": [
            {
                "script": {
                    "source": """
                        String name = ctx.name != null ? ctx.name : '';
                        String description = ctx.description != null ? ctx.description : '';
                        String category = ctx.category != null ? ctx.category : '';
                        String style = ctx.style != null ? ctx.style : '';

                        ctx.combined_text = 'Product: ' + name + '. ' + description +
                                          ' Category: ' + category + '. Style: ' + style + '.';
                    """
                }
            },
            {
                "text_embedding": {
                    "model_id": model_id,
                    "field_map": {
                        "combined_text": "product_vector"
                    }
                }
            },
            {
                "remove": {
                    "field": "combined_text",
                    "ignore_missing": True
                }
            }
        ]
    }

    print(f"Creating ingest pipeline: {pipeline_name}...")

    try:
        # Delete if exists
        try:
            client.ingest.get_pipeline(id=pipeline_name)
            client.ingest.delete_pipeline(id=pipeline_name)
            print(f"  Deleted existing pipeline")
        except:
            pass

        # Create new pipeline
        client.ingest.put_pipeline(id=pipeline_name, body=pipeline_body)
        print(f"✓ Ingest pipeline created: {pipeline_name}")
        return pipeline_name
    except Exception as e:
        print(f"Error creating pipeline: {e}")
        raise


def create_product_index(client: OpenSearch, vector_dim: int) -> str:
    """
    Create product index with k-NN mapping for vector search.
    Compatible with both local OpenSearch and Amazon OpenSearch Service 3.1.

    Args:
        client: OpenSearch client instance
        vector_dim: Vector dimension (768 for msmarco-distilbert-base-tas-b)

    Returns:
        str: Index name
    """
    index_name = os.getenv('OPENSEARCH_INDEX_PRODUCTS', 'shopping_products')

    index_body = {
        "settings": {
            "index": {
                "number_of_shards": 2,
                "number_of_replicas": 1,
                "knn": True,
                "knn.algo_param.ef_search": 100
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "description": {"type": "text"},
                "category": {
                    "type": "keyword",
                    "fields": {"text": {"type": "text"}}
                },
                "style": {"type": "keyword"},
                "price": {"type": "float"},
                "current_stock": {"type": "integer"},
                "gender_affinity": {"type": "keyword"},
                "promoted": {"type": "boolean"},
                "image": {"type": "keyword"},
                "where_visible": {"type": "keyword"},
                "product_vector": {
                    "type": "knn_vector",
                    "dimension": vector_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "l2",
                        "engine": "lucene",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 24
                        }
                    }
                }
            }
        }
    }

    print(f"Creating product index: {index_name}...")

    try:
        # Delete if exists
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
            print(f"  Deleted existing index")

        # Create index
        client.indices.create(index=index_name, body=index_body)
        print(f"✓ Product index created: {index_name}")
        return index_name
    except Exception as e:
        print(f"Error creating index: {e}")
        raise


def test_connection() -> bool:
    """
    Test OpenSearch connection and print cluster info.

    Returns:
        bool: True if connection successful
    """
    try:
        client = get_opensearch_client()
        info = client.info()
        print("✓ Connected to OpenSearch successfully!")
        print(f"  Cluster name: {info.get('cluster_name')}")
        print(f"  Version: {info.get('version', {}).get('number')}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to OpenSearch: {e}")
        return False
