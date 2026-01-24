"""Unit tests for DatabaseManager with retry logic and health checks."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.database.connection import DatabaseManager


@pytest.fixture
def db_manager():
    """Create a DatabaseManager instance."""
    return DatabaseManager()


@pytest.mark.asyncio
async def test_connect_success_first_attempt(db_manager):
    """Test successful connection on first attempt."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client_class.return_value = mock_client
        
        # Mock database and index creation
        mock_db = MagicMock()
        mock_db.applicationProfiles.create_index = AsyncMock()
        mock_db.datasets.create_index = AsyncMock()
        mock_db.evaluationRuns.create_index = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        await db_manager.connect()
        
        assert db_manager.is_connected()
        mock_client.admin.command.assert_called_once_with("ping")


@pytest.mark.asyncio
async def test_connect_retry_success(db_manager):
    """Test successful connection after retry."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        
        # First attempt fails, second succeeds
        mock_client.admin.command = AsyncMock(
            side_effect=[
                ConnectionFailure("Connection failed"),
                {"ok": 1}
            ]
        )
        mock_client_class.return_value = mock_client
        
        # Mock database and index creation
        mock_db = MagicMock()
        mock_db.applicationProfiles.create_index = AsyncMock()
        mock_db.datasets.create_index = AsyncMock()
        mock_db.evaluationRuns.create_index = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await db_manager.connect()
        
        assert db_manager.is_connected()
        assert mock_client.admin.command.call_count == 2


@pytest.mark.asyncio
async def test_connect_max_retries_exceeded(db_manager):
    """Test connection failure after max retries."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        
        # All attempts fail
        mock_client.admin.command = AsyncMock(
            side_effect=ConnectionFailure("Connection failed")
        )
        mock_client_class.return_value = mock_client
        
        # Mock database
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(ConnectionError, match="Could not connect to MongoDB"):
                await db_manager.connect()
        
        assert not db_manager.is_connected()


@pytest.mark.asyncio
async def test_connect_server_selection_timeout(db_manager):
    """Test connection with server selection timeout."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        
        # Timeout on first attempt, success on second
        mock_client.admin.command = AsyncMock(
            side_effect=[
                ServerSelectionTimeoutError("Timeout"),
                {"ok": 1}
            ]
        )
        mock_client_class.return_value = mock_client
        
        # Mock database and index creation
        mock_db = MagicMock()
        mock_db.applicationProfiles.create_index = AsyncMock()
        mock_db.datasets.create_index = AsyncMock()
        mock_db.evaluationRuns.create_index = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await db_manager.connect()
        
        assert db_manager.is_connected()


@pytest.mark.asyncio
async def test_connect_unexpected_error(db_manager):
    """Test connection with unexpected error."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client_class.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(RuntimeError, match="Unexpected error"):
            await db_manager.connect()
        
        assert not db_manager.is_connected()


@pytest.mark.asyncio
async def test_disconnect(db_manager):
    """Test disconnecting from database."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client_class.return_value = mock_client
        
        # Mock database and index creation
        mock_db = MagicMock()
        mock_db.applicationProfiles.create_index = AsyncMock()
        mock_db.datasets.create_index = AsyncMock()
        mock_db.evaluationRuns.create_index = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        await db_manager.connect()
        assert db_manager.is_connected()
        
        await db_manager.disconnect()
        assert not db_manager.is_connected()
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_connected_and_healthy(db_manager):
    """Test health check when connected and database is healthy."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client_class.return_value = mock_client
        
        # Mock database and index creation
        mock_db = MagicMock()
        mock_db.applicationProfiles.create_index = AsyncMock()
        mock_db.datasets.create_index = AsyncMock()
        mock_db.evaluationRuns.create_index = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        await db_manager.connect()
        
        result = await db_manager.health_check()
        
        assert result is True


@pytest.mark.asyncio
async def test_health_check_not_connected(db_manager):
    """Test health check when not connected."""
    result = await db_manager.health_check()
    
    assert result is False


@pytest.mark.asyncio
async def test_health_check_connection_lost(db_manager):
    """Test health check when connection is lost."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        
        # First ping succeeds (for connect), second fails (for health check)
        mock_client.admin.command = AsyncMock(
            side_effect=[
                {"ok": 1},  # connect ping
                ConnectionFailure("Connection lost")  # health check ping
            ]
        )
        mock_client_class.return_value = mock_client
        
        # Mock database and index creation
        mock_db = MagicMock()
        mock_db.applicationProfiles.create_index = AsyncMock()
        mock_db.datasets.create_index = AsyncMock()
        mock_db.evaluationRuns.create_index = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        await db_manager.connect()
        
        result = await db_manager.health_check()
        
        assert result is False


def test_database_property_when_connected(db_manager):
    """Test accessing database property when connected."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client_class.return_value = mock_client
        
        db_manager._client = mock_client
        db_manager._database = mock_db
        
        result = db_manager.database
        
        assert result == mock_db


def test_database_property_when_not_connected(db_manager):
    """Test accessing database property when not connected."""
    with pytest.raises(RuntimeError, match="Database not connected"):
        _ = db_manager.database


@pytest.mark.asyncio
async def test_index_creation(db_manager):
    """Test that indexes are created on connection."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client_class.return_value = mock_client
        
        # Mock database and index creation
        mock_db = MagicMock()
        mock_db.applicationProfiles.create_index = AsyncMock()
        mock_db.datasets.create_index = AsyncMock()
        mock_db.evaluationRuns.create_index = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        await db_manager.connect()
        
        # Verify indexes were created
        mock_db.applicationProfiles.create_index.assert_called_once_with("customerId")
        mock_db.datasets.create_index.assert_called_once_with("customerId")
        # evaluationRuns should have 3 indexes
        assert mock_db.evaluationRuns.create_index.call_count == 3


@pytest.mark.asyncio
async def test_exponential_backoff(db_manager):
    """Test that retry delay increases exponentially."""
    with patch('app.database.connection.AsyncIOMotorClient') as mock_client_class:
        mock_client = MagicMock()
        
        # All attempts fail
        mock_client.admin.command = AsyncMock(
            side_effect=ConnectionFailure("Connection failed")
        )
        mock_client_class.return_value = mock_client
        
        # Mock database
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(ConnectionError):
                await db_manager.connect()
        
        # Verify exponential backoff: 2.0, 4.0
        assert len(sleep_times) == 2
        assert sleep_times[0] == 2.0
        assert sleep_times[1] == 4.0
