#!/usr/bin/env python3
"""Test MongoDB connection"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.database.connection import database_manager


async def test_connection():
    """Test MongoDB connection and list collections"""
    try:
        print("🔌 Connecting to MongoDB...")
        await database_manager.connect()
        print("✅ Successfully connected to MongoDB 8")
        print(f"📊 Database: {database_manager.database.name}")
        
        # List collections
        collections = await database_manager.database.list_collection_names()
        print(f"📁 Collections: {collections if collections else '(none yet)'}")
        
        # Test ping
        result = await database_manager.database.command("ping")
        print(f"🏓 Ping result: {result}")
        
        await database_manager.disconnect()
        print("✅ Connection closed successfully")
        print("\n🎉 MongoDB 8 is ready to use!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_connection())
