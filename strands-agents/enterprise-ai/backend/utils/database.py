"""
Database abstraction layer for AIUI application.
Provides connection pooling and query execution utilities.
Uses username/password authentication with self-managed PostgreSQL.
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from utils.utility import Utility


class DatabaseManager:
    """
    Database manager class that handles connection pooling and query execution.
    Uses SQLAlchemy for connection management and provides utility methods for
    common database operations. Authenticates with self-managed PostgreSQL using
    username and password from environment variables.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one instance of DatabaseManager exists."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, pool_size: int = None, max_overflow: int = None, 
                 pool_timeout: int = None, pool_recycle: int = None):
        """
        Initialize the database manager with connection pooling.
        
        Args:
            pool_size: Maximum number of connections to keep in the pool
            max_overflow: Maximum number of connections to create above pool_size
            pool_timeout: Seconds to wait before giving up on getting a connection
            pool_recycle: Seconds after which a connection is recycled
        """
        if self._initialized:
            return

        self.util = Utility()
            
        # Get configuration from environment variables
        self.db_host = os.environ.get('DB_HOST')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME')
        self.db_username = os.environ.get('DB_USERNAME')
        self.db_password = os.environ.get('DB_PASSWORD')
        
        # Get pool configuration from environment variables or use provided values
        self.pool_size = pool_size or int(os.environ.get('DB_POOL_SIZE', 10))
        self.max_overflow = max_overflow or int(os.environ.get('DB_MAX_OVERFLOW', 0))
        self.pool_timeout = pool_timeout or int(os.environ.get('DB_POOL_TIMEOUT', 30))
        self.pool_recycle = pool_recycle or int(os.environ.get('DB_POOL_RECYCLE', 1800))
        
        # Validate required configuration
        if not all([self.db_host, self.db_name, self.db_username, self.db_password]):
            self.util.log_warning("Missing required database configuration. Database functionality will be disabled.")
            self.util.log_warning(f"Required: DB_HOST, DB_NAME, DB_USERNAME, DB_PASSWORD")
            self.util.log_warning(f"Current: host={self.db_host}, name={self.db_name}, username={bool(self.db_username)}, password={bool(self.db_password)}")
            self.engine = None
            self.Session = None
            self._initialized = True
            return
            
        try:
            # Create connection string with username/password authentication
            connection_string = f"postgresql://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
            
            # Create engine with connection pooling
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                connect_args={
                    'connect_timeout': 10,  # Connection timeout in seconds
                    'application_name': 'aiui-app'  # Identify application in PostgreSQL logs
                },
                echo=os.environ.get('DB_QUERY_LOG_LEVEL', '').upper() == 'DEBUG'  # Enable SQL logging if debug
            )
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            self.util.log_data(f"Database connection pool initialized with size {self.pool_size}")
            self.util.log_data(f"Connected to PostgreSQL at {self.db_host}:{self.db_port}/{self.db_name}")
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                self.util.log_data(f"Database connection test successful. PostgreSQL version: {version}")
                
        except Exception as e:
            self.util.log_error(f"Failed to initialize database connection: {str(e)}")
            self.util.log_error(f"Connection details: {self.db_host}:{self.db_port}/{self.db_name} as {self.db_username}")
            self.engine = None
            self.Session = None
            
        self._initialized = True
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Handles acquiring and releasing connections from the pool.
        
        Yields:
            SQLAlchemy connection object
        """
        if not self.engine:
            raise RuntimeError("Database connection not initialized")
            
        connection = None
        try:
            connection = self.engine.connect()
            yield connection
        except SQLAlchemyError as e:
            self.util.log_error(f"Database connection error: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        Handles creating, committing, and closing sessions.
        
        Yields:
            SQLAlchemy session object
        """
        if not self.Session:
            raise RuntimeError("Database session factory not initialized")
            
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.util.log_error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results as a list of dictionaries.
        
        Args:
            query: SQL query string
            params: Parameters for the query
            
        Returns:
            List of dictionaries representing the query results
        """
        if not self.engine:
            raise RuntimeError("Database connection not initialized")
            
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                result = conn.execute(text(query), params or {})
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                
            execution_time = time.time() - start_time
            self.util.log_data(f"Query executed in {execution_time:.4f} seconds, returned {len(rows)} rows")
            return rows
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.util.log_error(f"Query failed after {execution_time:.4f} seconds: {str(e)}")
            self.util.log_error(f"Query: {query}")
            self.util.log_error(f"Params: {params}")
            raise
    
    def execute_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute a write operation (INSERT, UPDATE, DELETE) and return the number of affected rows.
        
        Args:
            query: SQL query string
            params: Parameters for the query
            
        Returns:
            Number of affected rows
        """
        if not self.engine:
            raise RuntimeError("Database connection not initialized")
            
        start_time = time.time()
        try:
            with self.get_session() as session:
                result = session.execute(text(query), params or {})
                rowcount = result.rowcount
                
            execution_time = time.time() - start_time
            self.util.log_data(f"Write operation executed in {execution_time:.4f} seconds, {rowcount} rows affected")
            return rowcount
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.util.log_error(f"Write operation failed after {execution_time:.4f} seconds: {str(e)}")
            self.util.log_error(f"Query: {query}")
            self.util.log_error(f"Params: {params}")
            raise
    
    def execute_batch(self, query: str, params_list: List[Dict[str, Any]]) -> int:
        """
        Execute a batch operation with multiple parameter sets.
        
        Args:
            query: SQL query string
            params_list: List of parameter dictionaries
            
        Returns:
            Total number of affected rows
        """
        if not self.engine:
            raise RuntimeError("Database connection not initialized")
            
        if not params_list:
            return 0
            
        start_time = time.time()
        total_rows = 0
        
        try:
            with self.get_session() as session:
                for params in params_list:
                    result = session.execute(text(query), params)
                    total_rows += result.rowcount
                    
            execution_time = time.time() - start_time
            self.util.log_data(f"Batch operation executed in {execution_time:.4f} seconds, {total_rows} total rows affected")
            return total_rows
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.util.log_error(f"Batch operation failed after {execution_time:.4f} seconds: {str(e)}")
            self.util.log_error(f"Query: {query}")
            raise
    
    def execute_transaction(self, queries: List[Tuple[str, Optional[Dict[str, Any]]]]) -> bool:
        """
        Execute multiple queries in a single transaction.
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            True if transaction was successful
        """
        if not self.engine:
            raise RuntimeError("Database connection not initialized")
            
        if not queries:
            return True
            
        start_time = time.time()
        
        try:
            with self.get_session() as session:
                for query, params in queries:
                    session.execute(text(query), params or {})
                    
            execution_time = time.time() - start_time
            self.util.log_data(f"Transaction executed in {execution_time:.4f} seconds")
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.util.log_error(f"Transaction failed after {execution_time:.4f} seconds: {str(e)}")
            for i, (query, _) in enumerate(queries):
                self.util.log_error(f"Query {i+1}: {query}")
            raise
    
    def get_pool_status(self) -> Dict[str, int]:
        """
        Get the current status of the connection pool.
        
        Returns:
            Dictionary with pool statistics
        """
        if not self.engine:
            return {"status": "not_initialized"}
            
        return {
            "pool_size": self.engine.pool.size(),
            "checkedin": self.engine.pool.checkedin(),
            "checkedout": self.engine.pool.checkedout(),
            "overflow": self.engine.pool.overflow(),
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the database connection and return connection details.
        
        Returns:
            Dictionary with connection test results
        """
        if not self.engine:
            return {
                "status": "error",
                "message": "Database connection not initialized",
                "connected": False
            }
        
        try:
            with self.get_connection() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1 as test"))
                test_result = result.fetchone()[0]
                
                # Get database info
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                
                # Get current database and user
                result = conn.execute(text("SELECT current_database(), current_user"))
                db_info = result.fetchone()
                current_db, current_user = db_info[0], db_info[1]
                
                return {
                    "status": "success",
                    "message": "Database connection successful",
                    "connected": True,
                    "test_query_result": test_result,
                    "postgresql_version": version,
                    "current_database": current_db,
                    "current_user": current_user,
                    "connection_details": {
                        "host": self.db_host,
                        "port": self.db_port,
                        "database": self.db_name,
                        "username": self.db_username
                    }
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Database connection failed: {str(e)}",
                "connected": False,
                "connection_details": {
                    "host": self.db_host,
                    "port": self.db_port,
                    "database": self.db_name,
                    "username": self.db_username
                }
            }
