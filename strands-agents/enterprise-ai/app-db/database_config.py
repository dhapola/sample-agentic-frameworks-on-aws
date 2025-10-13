"""
Database configuration and connection management using SQLAlchemy.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Database configuration class."""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.database_name = os.getenv("DB_NAME", "eaidb")
        self.username = os.getenv("DB_USERNAME")
        self.password = os.getenv("DB_PASSWORD")
        
        if not all([self.username, self.password]):
            raise ValueError("DB_USERNAME and DB_PASSWORD must be set in environment variables")
        
        self.database_url = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database_name}"
    
    def __repr__(self):
        return f"DatabaseConfig(host={self.host}, port={self.port}, database={self.database_name})"


class DatabaseConnection:
    """Singleton database connection manager."""
    
    _instance: Optional['DatabaseConnection'] = None
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, config: DatabaseConfig) -> bool:
        """Initialize database connection."""
        try:
            self._engine = create_engine(
                config.database_url,
                echo=False,  # Set to True for SQL logging
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )
            
            # Test connection
            with self._engine.connect() as conn:
                conn.execute("SELECT 1")
            
            print("Database connection initialized successfully.")
            return True
            
        except SQLAlchemyError as e:
            print(f"Error initializing database connection: {e}")
            return False
    
    def get_engine(self) -> Optional[Engine]:
        """Get database engine."""
        return self._engine
    
    def get_session(self) -> Optional[Session]:
        """Get database session."""
        if not self._session_factory:
            print("Database not initialized.")
            return None
        return self._session_factory()
    
    def close(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            print("Database connections closed.")


# Global database connection instance
db_connection = DatabaseConnection()


def get_db_session() -> Optional[Session]:
    """Convenience function to get database session."""
    return db_connection.get_session()


def init_database() -> bool:
    """Initialize database with configuration from environment."""
    try:
        config = DatabaseConfig()
        return db_connection.initialize(config)
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
