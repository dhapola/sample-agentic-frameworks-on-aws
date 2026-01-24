#!/usr/bin/env python3
"""Test Qdrant server connection"""
from qdrant_client import QdrantClient

try:
    client = QdrantClient(url="http://localhost:6333")
    collections = client.get_collections()
    print("✅ Successfully connected to Qdrant server!")
    print(f"Collections: {[c.name for c in collections.collections]}")
except Exception as e:
    print(f"❌ Failed to connect to Qdrant: {e}")
