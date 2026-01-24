#!/usr/bin/env python3
"""
Quick test to verify backend is running and responding correctly.
"""
import requests
import json

BASE_URL = "http://localhost:3000"

def test_health():
    """Test health endpoint"""
    print("Testing /api/health...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_chat():
    """Test chat endpoint"""
    print("\nTesting /api/chat...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "Hello, test message"},
            stream=True,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("Streaming response:")
            for line in response.iter_lines():
                if line:
                    print(f"  {line.decode('utf-8')}")
        else:
            print(f"Error response: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Backend Connection Test")
    print("=" * 50)
    
    health_ok = test_health()
    chat_ok = test_chat()
    
    print("\n" + "=" * 50)
    print(f"Health check: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Chat test: {'✓ PASS' if chat_ok else '✗ FAIL'}")
    
    if health_ok and chat_ok:
        print("\n✓ Backend is working correctly!")
    else:
        print("\n✗ Backend has issues. Check if:")
        print("  1. Backend is running (python backend/main.py)")
        print("  2. Port 3000 is not blocked")
        print("  3. .env file is configured correctly")
