#!/usr/bin/env python3
"""Clear test database before running tests."""

import asyncio
from app.database.connection import database_manager


async def clear_test_database():
    """Clear all collections in the test database."""
    print("Connecting to database...")
    await database_manager.connect()
    
    db = database_manager.database
    
    print("Clearing collections...")
    await db.customers.delete_many({})
    await db.applicationProfiles.delete_many({})
    await db.datasets.delete_many({})
    await db.evaluationRuns.delete_many({})
    
    print("✅ Database cleared successfully")
    
    await database_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(clear_test_database())
