"""MongoDB connection manager"""

import asyncio
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connection lifecycle with retry logic and health checks"""

    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._max_retries: int = 3
        self._retry_delay: float = 2.0

    async def connect(self) -> None:
        """Establish connection to MongoDB with retry logic"""
        last_error = None
        
        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(f"Attempting to connect to MongoDB (attempt {attempt}/{self._max_retries})")
                
                self._client = AsyncIOMotorClient(
                    settings.mongodb_url,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000,
                )
                self._database = self._client[settings.mongodb_db_name]

                # Verify connection
                await self._client.admin.command("ping")
                logger.info(f"Connected to MongoDB database: {settings.mongodb_db_name}")

                # Create indexes for multi-tenancy
                await self._create_indexes()
                
                return

            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                logger.warning(
                    f"Failed to connect to MongoDB (attempt {attempt}/{self._max_retries}): {e}"
                )
                
                # Clean up failed connection attempt
                self._client = None
                self._database = None
                
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay)
                    self._retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to MongoDB after {self._max_retries} attempts")
                    raise ConnectionError(
                        f"Could not connect to MongoDB after {self._max_retries} attempts: {last_error}"
                    ) from last_error
                    
            except Exception as e:
                logger.error(f"Unexpected error connecting to MongoDB: {e}")
                raise

    async def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("Disconnected from MongoDB")

    def is_connected(self) -> bool:
        """Check if database connection is active"""
        return self._client is not None and self._database is not None

    async def health_check(self) -> bool:
        """
        Perform health check on database connection.
        
        Returns:
            True if database is healthy and responsive, False otherwise
        """
        if not self.is_connected():
            logger.warning("Health check failed: Database not connected")
            return False
        
        try:
            # Ping the database to verify it's responsive
            await self._client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if self._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._database

    async def _create_indexes(self) -> None:
        """Create database indexes for efficient queries and tenant isolation"""
        if self._database is None:
            return

        # Application profiles - tenant isolation
        await self._database.applicationProfiles.create_index("customerId")

        # Datasets - tenant isolation
        await self._database.datasets.create_index("customerId")

        # Evaluation runs - tenant isolation and common queries
        await self._database.evaluationRuns.create_index("customerId")
        await self._database.evaluationRuns.create_index([("customerId", 1), ("status", 1)])
        await self._database.evaluationRuns.create_index([("customerId", 1), ("startTime", -1)])

        logger.info("Database indexes created successfully")


# Global database manager instance
database_manager = DatabaseManager()
