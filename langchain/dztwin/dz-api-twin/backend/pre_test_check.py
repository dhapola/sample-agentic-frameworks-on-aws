#!/usr/bin/env python3
"""
Pre-Test Environment Verification Script
Validates all components are ready for manual testing
"""

import sys
import os
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")

def print_info(text):
    print(f"{BLUE}ℹ{RESET} {text}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_header("Checking Backend Configuration")
    
    env_path = Path(__file__).parent / '.env'
    if not env_path.exists():
        print_error(".env file not found")
        print_info("Copy .env.example to .env and configure it")
        return False
    
    print_success(".env file exists")
    
    # Check required variables
    required_vars = [
        'AI_PROVIDER',
        'AWS_REGION',
        'BEDROCK_MODEL_ID',
        'RAG_ENABLED',
        'QDRANT_URL',
        'QDRANT_COLLECTION_NAME'
    ]
    
    with open(env_path) as f:
        env_content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if var not in env_content or f"{var}=" not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print_error(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print_success("All required environment variables present")
    
    # Check specific values
    if 'AI_PROVIDER=bedrock' in env_content:
        print_success("AI Provider: bedrock ✓")
    else:
        print_warning("AI Provider is not set to 'bedrock'")
    
    if 'RAG_ENABLED=true' in env_content:
        print_success("RAG: enabled ✓")
    else:
        print_warning("RAG is not enabled")
    
    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    print_header("Checking Python Dependencies")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'langchain_core',
        'langchain_aws',
        'boto3',
        'qdrant_client',
        'pydantic',
        'pydantic_settings'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} installed")
        except ImportError:
            missing_packages.append(package)
            print_error(f"{package} NOT installed")
    
    if missing_packages:
        print_error(f"\nMissing packages: {', '.join(missing_packages)}")
        print_info("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    print_header("Checking AWS Credentials")
    
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        
        # Try to create a Bedrock client
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print_error("AWS credentials not found")
            print_info("Configure AWS credentials using:")
            print_info("  - AWS CLI: aws configure")
            print_info("  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            print_info("  - IAM role (if running on EC2)")
            return False
        
        print_success(f"AWS credentials found (Access Key: {credentials.access_key[:8]}...)")
        
        # Try to create Bedrock Runtime client
        try:
            from config import get_config
            config = get_config()
            
            bedrock = boto3.client(
                service_name='bedrock-runtime',
                region_name=config.aws_region
            )
            print_success(f"Bedrock client created for region: {config.aws_region}")
            return True
            
        except Exception as e:
            print_error(f"Failed to create Bedrock client: {str(e)}")
            return False
            
    except ImportError:
        print_error("boto3 not installed")
        return False

def check_qdrant():
    """Check if Qdrant is running and accessible"""
    print_header("Checking Qdrant Vector Database")
    
    try:
        from qdrant_client import QdrantClient
        from config import get_config
        
        config = get_config()
        
        try:
            client = QdrantClient(url=config.qdrant_url)
            print_success(f"Connected to Qdrant at {config.qdrant_url}")
            
            # Check if collection exists
            try:
                collection_info = client.get_collection(config.qdrant_collection_name)
                vectors_count = collection_info.vectors_count
                print_success(f"Collection '{config.qdrant_collection_name}' found")
                print_info(f"  Documents indexed: {vectors_count}")
                
                if vectors_count == 0:
                    print_warning("Collection is empty - no documents indexed yet")
                    print_info("Run the ingester to index documentation")
                    return True
                
                return True
                
            except Exception as e:
                print_error(f"Collection '{config.qdrant_collection_name}' not found")
                print_info("Run the ingester to create and populate the collection")
                return False
                
        except Exception as e:
            print_error(f"Cannot connect to Qdrant: {str(e)}")
            print_info("Start Qdrant with: finch run -d -p 6333:6333 --name qdrant qdrant/qdrant")
            return False
            
    except ImportError:
        print_error("qdrant_client not installed")
        return False

def check_frontend():
    """Check if frontend files exist"""
    print_header("Checking Frontend Files")
    
    frontend_path = Path(__file__).parent.parent / 'frontend'
    
    required_files = [
        'chat-plugin.js',
        'widget.html',
        'widget.css',
        'widget.js',
        'api/chat-api.js',
        'example.html'
    ]
    
    all_exist = True
    for file in required_files:
        file_path = frontend_path / file
        if file_path.exists():
            print_success(f"{file} exists")
        else:
            print_error(f"{file} NOT found")
            all_exist = False
    
    return all_exist

def check_ports():
    """Check if required ports are available"""
    print_header("Checking Port Availability")
    
    import socket
    
    ports_to_check = {
        3000: 'Backend API',
        8000: 'Frontend Dev Server',
        6333: 'Qdrant'
    }
    
    for port, service in ports_to_check.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print_success(f"Port {port} ({service}) is in use - service likely running")
        else:
            print_warning(f"Port {port} ({service}) is available - service not running")

def main():
    print_header("Pre-Test Environment Verification")
    print_info("This script checks if your environment is ready for manual testing\n")
    
    checks = [
        ("Environment Configuration", check_env_file),
        ("Python Dependencies", check_dependencies),
        ("AWS Credentials", check_aws_credentials),
        ("Qdrant Vector Database", check_qdrant),
        ("Frontend Files", check_frontend),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Error during {name} check: {str(e)}")
            results.append((name, False))
    
    # Check ports separately (informational only)
    check_ports()
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        if result:
            print_success(f"{name}: PASS")
        else:
            print_error(f"{name}: FAIL")
    
    print(f"\n{BLUE}Score: {passed}/{total} checks passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}✓ Environment is ready for testing!{RESET}")
        print(f"{GREEN}{'='*60}{RESET}\n")
        print_info("Next steps:")
        print_info("1. Start backend: cd backend && python main.py")
        print_info("2. Start frontend: cd frontend && npm run dev")
        print_info("3. Open: http://localhost:8000/example.html")
        print_info("4. Follow MANUAL_TEST_PLAN.md")
        return 0
    else:
        print(f"\n{RED}{'='*60}{RESET}")
        print(f"{RED}✗ Environment has issues - fix them before testing{RESET}")
        print(f"{RED}{'='*60}{RESET}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
