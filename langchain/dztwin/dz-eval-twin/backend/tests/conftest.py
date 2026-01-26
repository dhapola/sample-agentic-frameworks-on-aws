"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from unittest.mock import MagicMock
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.connection import database_manager


@pytest.fixture(scope="function", autouse=True)
def clean_database():
    """Clean database before each test."""
    # Use asyncio.run to execute async cleanup in sync fixture
    async def cleanup():
        if database_manager.is_connected():
            db = database_manager.database
            await db.customers.delete_many({})
            await db.applicationProfiles.delete_many({})
            await db.datasets.delete_many({})
            await db.evaluationRuns.delete_many({})
    
    asyncio.run(cleanup())
    yield


@pytest.fixture(scope="function")
def mock_database():
    """Create a mock database for testing (for tests that don't need real DB)."""
    mock_db = MagicMock(spec=AsyncIOMotorDatabase)
    
    # Mock collections
    mock_db.customers = MagicMock()
    mock_db.applicationProfiles = MagicMock()
    mock_db.datasets = MagicMock()
    mock_db.evaluationRuns = MagicMock()
    
    return mock_db


@pytest.fixture(scope="function")
def mock_repository(mock_database):
    """Create a mock repository for testing."""
    from app.database.repository import DataRepository
    return DataRepository(mock_database)
