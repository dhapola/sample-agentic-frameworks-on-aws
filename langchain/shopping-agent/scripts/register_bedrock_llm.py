#!/usr/bin/env python3
"""
Register and deploy Amazon Bedrock Claude model to OpenSearch for agentic memory.

This script:
1. Creates a Bedrock connector in OpenSearch
2. Registers the Claude 3.5 Haiku model
3. Deploys the model for use
4. Tests the model deployment
5. Outputs the model ID for use in .env

Prerequisites:
- AWS credentials with Bedrock access in .env
- OpenSearch running and accessible
- Bedrock Claude 3.5 Haiku enabled in us-west-2

Reference: https://docs.opensearch.org/latest/ml-commons-plugin/remote-models/bedrock/
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from agents.opensearch_client import get_opensearch_client

# Load environment variables
load_dotenv()


def create_bedrock_connector(client, region: str, access_key: str, secret_key: str, session_token: str = None):
    """
    Create a connector for Amazon Bedrock Claude model.

    Args:
        client: OpenSearch client instance
        region: AWS region (e.g., "us-west-2")
        access_key: AWS access key ID
        secret_key: AWS secret access key
        session_token: Optional AWS session token (for temporary credentials)

    Returns:
        str: Connector ID
    """
    print("Step 1: Creating Bedrock connector...")
    print(f"  Region: {region}")
    print(f"  Model: Claude 3.5 Haiku (anthropic.claude-3-5-haiku-20241022-v1:0)")

    connector_body = {
        "name": "Amazon Bedrock Claude 3.5 Haiku Connector",
        "description": "Connector for Amazon Bedrock Claude 3.5 Haiku for agentic memory processing",
        "version": "1.0",
        "protocol": "aws_sigv4",
        "parameters": {
            "region": region,
            "service_name": "bedrock",
            "model": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
            "anthropic_version": "bedrock-2023-05-31"
        },
        "credential": {
            "access_key": access_key,
            "secret_key": secret_key
        },
        "actions": [
            {
                "action_type": "predict",
                "method": "POST",
                "url": f"https://bedrock-runtime.{region}.amazonaws.com/model/us.anthropic.claude-3-5-haiku-20241022-v1:0/invoke",
                "headers": {
                    "content-type": "application/json",
                    "x-amz-content-sha256": "required"
                },
                "request_body": """{
                    "anthropic_version": "${parameters.anthropic_version}",
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": "${parameters.prompt}"
                        }
                    ]
                }""",
                "pre_process_function": "\n    StringBuilder builder = new StringBuilder();\n    builder.append(\"\\\"\");\n    String first = params.text;\n    builder.append(first);\n    builder.append(\"\\\"\");\n    def parameters = \"{\" +\"\\\"prompt\\\":\" + builder + \"}\";\n    return  \"{\" +\"\\\"parameters\\\":\" + parameters + \"}\";",
                "post_process_function": "\n      def dataType = \"text/docs\";\n      def dataArray = [];\n      if (params.content != null && params.content.size() > 0) {\n        for (item in params.content) {\n          if (item.type == \"text\") {\n            def output = item.text;\n            dataArray.add(output);\n          }\n        }\n      }\n      if (dataArray.size() > 0) {\n        return dataArray.get(0);\n      }\n      return \"\";"
            }
        ]
    }

    # Add session token if provided
    if session_token:
        connector_body["credential"]["session_token"] = session_token

    try:
        response = client.transport.perform_request(
            'POST',
            '/_plugins/_ml/connectors/_create',
            body=connector_body
        )

        connector_id = response.get('connector_id')
        if not connector_id:
            raise ValueError("No connector_id returned in response")

        print(f"  ✓ Connector created successfully!")
        print(f"  Connector ID: {connector_id}")
        return connector_id

    except Exception as e:
        print(f"  ✗ Error creating connector: {e}")
        if hasattr(e, 'info'):
            print(f"  Details: {e.info}")
        raise


def register_model(client, connector_id: str):
    """
    Register the Bedrock model with OpenSearch.

    Args:
        client: OpenSearch client instance
        connector_id: Connector ID from create_bedrock_connector

    Returns:
        tuple: (model_id, task_id)
    """
    print("\nStep 2: Registering Bedrock model...")

    register_body = {
        "name": "Bedrock Claude 3.5 Haiku",
        "function_name": "remote",
        "description": "Claude 3.5 Haiku via Amazon Bedrock for agentic memory processing and summarization",
        "connector_id": connector_id
    }

    try:
        response = client.transport.perform_request(
            'POST',
            '/_plugins/_ml/models/_register',
            body=register_body
        )

        task_id = response.get('task_id')
        status = response.get('status')

        if not task_id:
            raise ValueError("No task_id returned in response")

        print(f"  ✓ Model registration initiated!")
        print(f"  Task ID: {task_id}")
        print(f"  Status: {status}")

        return task_id

    except Exception as e:
        print(f"  ✗ Error registering model: {e}")
        if hasattr(e, 'info'):
            print(f"  Details: {e.info}")
        raise


def wait_for_registration(client, task_id: str, timeout: int = 60):
    """
    Wait for model registration to complete.

    Args:
        client: OpenSearch client instance
        task_id: Task ID from register_model
        timeout: Maximum wait time in seconds

    Returns:
        str: Model ID
    """
    print("\nStep 3: Waiting for registration to complete...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = client.transport.perform_request(
                'GET',
                f'/_plugins/_ml/tasks/{task_id}'
            )

            state = response.get('state')
            model_id = response.get('model_id')

            print(f"  Status: {state}", end='\r')

            if state == 'COMPLETED':
                print(f"\n  ✓ Registration completed!")
                print(f"  Model ID: {model_id}")
                return model_id
            elif state == 'FAILED':
                error = response.get('error', 'Unknown error')
                raise RuntimeError(f"Registration failed: {error}")

            time.sleep(2)

        except Exception as e:
            if 'COMPLETED' not in str(e):
                print(f"\n  ✗ Error checking registration status: {e}")
                raise

    raise TimeoutError(f"Registration did not complete within {timeout} seconds")


def deploy_model(client, model_id: str):
    """
    Deploy the registered model.

    Args:
        client: OpenSearch client instance
        model_id: Model ID from wait_for_registration

    Returns:
        str: Task ID for deployment
    """
    print("\nStep 4: Deploying model...")

    try:
        response = client.transport.perform_request(
            'POST',
            f'/_plugins/_ml/models/{model_id}/_deploy'
        )

        task_id = response.get('task_id')
        status = response.get('status')

        if not task_id:
            raise ValueError("No task_id returned in response")

        print(f"  ✓ Model deployment initiated!")
        print(f"  Task ID: {task_id}")
        print(f"  Status: {status}")

        return task_id

    except Exception as e:
        print(f"  ✗ Error deploying model: {e}")
        if hasattr(e, 'info'):
            print(f"  Details: {e.info}")
        raise


def wait_for_deployment(client, model_id: str, task_id: str, timeout: int = 120):
    """
    Wait for model deployment to complete.

    Args:
        client: OpenSearch client instance
        model_id: Model ID
        task_id: Task ID from deploy_model
        timeout: Maximum wait time in seconds

    Returns:
        bool: True if deployment successful
    """
    print("\nStep 5: Waiting for deployment to complete...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check task status
            response = client.transport.perform_request(
                'GET',
                f'/_plugins/_ml/tasks/{task_id}'
            )

            state = response.get('state')
            print(f"  Status: {state}", end='\r')

            if state == 'COMPLETED':
                # Verify model is deployed
                model_response = client.transport.perform_request(
                    'GET',
                    f'/_plugins/_ml/models/{model_id}'
                )

                model_state = model_response.get('model_state')
                if model_state == 'DEPLOYED':
                    print(f"\n  ✓ Deployment completed!")
                    print(f"  Model State: {model_state}")
                    return True
                else:
                    print(f"\n  ⚠ Model state: {model_state}")
                    time.sleep(2)
                    continue

            elif state == 'FAILED':
                error = response.get('error', 'Unknown error')
                raise RuntimeError(f"Deployment failed: {error}")

            time.sleep(3)

        except Exception as e:
            if 'COMPLETED' not in str(e) and 'DEPLOYED' not in str(e):
                print(f"\n  ✗ Error checking deployment status: {e}")
                raise

    raise TimeoutError(f"Deployment did not complete within {timeout} seconds")


def test_model(client, model_id: str):
    """
    Test the deployed model with a sample prediction.

    Args:
        client: OpenSearch client instance
        model_id: Model ID to test

    Returns:
        bool: True if test successful
    """
    print("\nStep 6: Testing model...")

    test_body = {
        "parameters": {
            "prompt": "Summarize this customer preference: Likes blue and black colors, wears size M, enjoys hiking and outdoor activities."
        }
    }

    try:
        response = client.transport.perform_request(
            'POST',
            f'/_plugins/_ml/models/{model_id}/_predict',
            body=test_body
        )

        # Extract prediction result
        inference_results = response.get('inference_results', [])
        if inference_results and len(inference_results) > 0:
            output = inference_results[0].get('output', [])
            if output and len(output) > 0:
                result = output[0].get('dataAsMap', {}).get('response', output[0])
                print(f"  ✓ Model test successful!")
                print(f"  Sample output: {str(result)[:100]}...")
                return True

        print(f"  ⚠ Unexpected response format: {response}")
        return False

    except Exception as e:
        print(f"  ✗ Error testing model: {e}")
        if hasattr(e, 'info'):
            print(f"  Details: {e.info}")
        return False


def main():
    """Main setup function."""
    print("=" * 70)
    print("Amazon Bedrock Claude 3.5 Haiku - OpenSearch Registration")
    print("=" * 70)
    print()

    # Get AWS credentials from environment
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    session_token = os.getenv('AWS_SESSION_TOKEN')  # Optional
    region = os.getenv('AWS_REGION_NAME', 'us-west-2')

    # Validation
    if not access_key or not secret_key:
        print("ERROR: AWS credentials not found in .env file")
        print()
        print("Please add the following to your .env file:")
        print("  AWS_ACCESS_KEY_ID=\"your-access-key\"")
        print("  AWS_SECRET_ACCESS_KEY=\"your-secret-key\"")
        print("  AWS_REGION_NAME=\"us-west-2\"  # Optional, defaults to us-west-2")
        print()
        print("Make sure your AWS account has:")
        print("  ✓ Amazon Bedrock access enabled")
        print("  ✓ Claude 3.5 Haiku model access in us-west-2")
        print("  ✓ Permissions: bedrock:InvokeModel")
        sys.exit(1)

    print(f"Configuration:")
    print(f"  AWS Region: {region}")
    print(f"  Access Key: {access_key[:10]}...")
    print(f"  Model: Claude 3.5 Haiku (anthropic.claude-3-5-haiku-20241022-v1:0)")
    print()

    # Get OpenSearch client
    try:
        client = get_opensearch_client()
        print("✓ Connected to OpenSearch")
        print()
    except Exception as e:
        print(f"✗ Failed to connect to OpenSearch: {e}")
        sys.exit(1)

    try:
        # Step 1: Create connector
        connector_id = create_bedrock_connector(
            client,
            region=region,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token
        )

        # Step 2: Register model
        task_id = register_model(client, connector_id)

        # Step 3: Wait for registration
        model_id = wait_for_registration(client, task_id)

        # Step 4: Deploy model
        deploy_task_id = deploy_model(client, model_id)

        # Step 5: Wait for deployment
        wait_for_deployment(client, model_id, deploy_task_id)

        # Step 6: Test model
        test_model(client, model_id)

        # Success!
        print("\n" + "=" * 70)
        print("✓ Bedrock Claude 3.5 Haiku setup complete!")
        print("=" * 70)
        print()
        print("Next steps:")
        print(f"1. Add this to your .env file:")
        print(f"   OPENSEARCH_LLM_MODEL_ID=\"{model_id}\"")
        print()
        print("2. Run the memory container setup:")
        print("   python scripts/setup_opensearch_memory_container.py")
        print()
        print("3. The LLM will now be used for:")
        print("   • Memory summarization")
        print("   • Long-term memory processing")
        print("   • Enhanced preference extraction")

    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        print()
        print("Troubleshooting:")
        print("• Verify AWS credentials have Bedrock access")
        print("• Check Claude 3.5 Haiku is enabled in your AWS account")
        print("• Ensure us-west-2 region has Bedrock service available")
        print("• Check OpenSearch cluster has sufficient resources")
        sys.exit(1)


if __name__ == "__main__":
    main()
