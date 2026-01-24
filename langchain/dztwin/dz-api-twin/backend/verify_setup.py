#!/usr/bin/env python3
"""
Verify backend setup and dependencies before starting the server.
"""
import sys
import os
from pathlib import Path

def check_env_file():
    """Check if .env file exists"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Run: cp .env.example .env")
        return False
    print("✓ .env file exists")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("langchain", "LangChain"),
        ("boto3", "Boto3"),
    ]
    
    all_ok = True
    for module, name in required:
        try:
            __import__(module)
            print(f"✓ {name} installed")
        except ImportError:
            print(f"❌ {name} not installed")
            all_ok = False
    
    # Check botocore[crt]
    try:
        import awscrt
        print("✓ botocore[crt] installed")
    except ImportError:
        print("❌ botocore[crt] not installed")
        print("   Run: pip install 'botocore[crt]'")
        all_ok = False
    
    return all_ok

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    try:
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✓ AWS credentials configured (Account: {identity['Account']})")
        return True
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("   Run: aws configure")
        return False

def check_config():
    """Check if configuration is valid"""
    try:
        from config import get_config
        config = get_config()
        print(f"✓ Configuration loaded")
        print(f"  - AI Provider: {config.AI_PROVIDER}")
        print(f"  - AWS Region: {config.AWS_REGION}")
        print(f"  - RAG Enabled: {config.RAG_ENABLED}")
        print(f"  - Port: {config.API_PORT}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    print("Backend Setup Verification")
    print("=" * 50)
    
    checks = [
        ("Environment file", check_env_file),
        ("Dependencies", check_dependencies),
        ("AWS credentials", check_aws_credentials),
        ("Configuration", check_config),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        results.append(check_func())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✓ All checks passed! Ready to start the backend.")
        print("\nRun: python main.py")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
