import os
import json
from datetime import datetime
from typing import Dict, Optional, List, Any
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, 
    Column, 
    String, 
    Text, 
    DateTime, 
    Boolean, 
    JSON,
    MetaData,
    Table,
    inspect,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine

# Load environment variables from .env file
load_dotenv()

# Get database connection parameters from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "eaidb")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Create SQLAlchemy base
Base = declarative_base()


class ChatHistory(Base):
    """SQLAlchemy model for chat_history table."""
    __tablename__ = 'chat_history'
    
    thread_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False)
    thread_title = Column(Text)
    ui_msgs = Column(JSON, nullable=False)
    agent_msgs = Column(JSON, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<ChatHistory(thread_id='{self.thread_id}', user_id='{self.user_id}')>"


class DatabaseManager:
    """Class to manage database operations using SQLAlchemy."""
    
    def __init__(self, host: str, port: str, database_name: str, username: str, password: str):
        """Initialize the database manager with connection parameters."""
        self.host = host
        self.port = port
        self.database_name = database_name
        self.username = username
        self.password = password
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        
        # URL encode the password to handle special characters
        encoded_password = quote_plus(password)
        
        # Create database URL
        self.database_url = f"postgresql://{username}:{encoded_password}@{host}:{port}/{database_name}"
        self.postgres_url = f"postgresql://{username}:{encoded_password}@{host}:{port}/postgres"
    
    def create_database_if_not_exists(self) -> bool:
        """Create the database if it doesn't exist."""
        try:
            # Connect to postgres database to create our target database
            postgres_engine = create_engine(
                self.postgres_url,
                isolation_level="AUTOCOMMIT"  # Required for CREATE DATABASE
            )
            
            # Check if database exists
            with postgres_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"), 
                    {"db_name": self.database_name}
                )
                exists = result.fetchone()
                
                if not exists:
                    # Create the database
                    conn.execute(text(f"CREATE DATABASE {self.database_name}"))
                    print(f"Database '{self.database_name}' created successfully.")
                else:
                    print(f"Database '{self.database_name}' already exists.")
            
            postgres_engine.dispose()
            return True
            
        except SQLAlchemyError as e:
            print(f"Error creating database: {e}")
            return False
    
    def initialize_engine(self) -> bool:
        """Initialize SQLAlchemy engine and session factory."""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL query logging
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600    # Recycle connections every hour
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            print("Database engine initialized successfully.")
            return True
            
        except SQLAlchemyError as e:
            print(f"Error initializing database engine: {e}")
            return False
    
    def create_tables(self) -> bool:
        """Create all tables defined in the models."""
        try:
            if not self.engine:
                print("Database engine not initialized.")
                return False
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            print("All tables created successfully.")
            return True
            
        except SQLAlchemyError as e:
            print(f"Error creating tables: {e}")
            return False
    
    def get_session(self) -> Optional[Session]:
        """Get a database session."""
        if not self.SessionLocal:
            print("Session factory not initialized.")
            return None
        
        return self.SessionLocal()
    
    def execute_raw_query(self, query: str, params: Optional[Dict] = None) -> bool:
        """Execute a raw SQL query."""
        try:
            if not self.engine:
                print("Database engine not initialized.")
                return False
            
            with self.engine.connect() as conn:
                if params:
                    conn.execute(text(query), params)
                else:
                    conn.execute(text(query))
                conn.commit()
            
            return True
            
        except SQLAlchemyError as e:
            print(f"Error executing query: {e}")
            return False
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            if not self.engine:
                return False
            
            inspector = inspect(self.engine)
            return table_name in inspector.get_table_names()
            
        except SQLAlchemyError as e:
            print(f"Error checking table existence: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> Optional[List[Dict]]:
        """Get information about table columns."""
        try:
            if not self.engine:
                return None
            
            inspector = inspect(self.engine)
            if table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                return columns
            else:
                print(f"Table '{table_name}' does not exist.")
                return None
                
        except SQLAlchemyError as e:
            print(f"Error getting table info: {e}")
            return None
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            print("Database connections closed.")


class ChatHistoryRepository:
    """Repository class for chat_history operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_chat_history(self, thread_id: str, user_id: str, thread_title: str,
                          ui_msgs: Dict, agent_msgs: Dict) -> bool:
        """Create a new chat history record."""
        session = self.db_manager.get_session()
        if not session:
            return False
        
        try:
            chat_history = ChatHistory(
                thread_id=thread_id,
                user_id=user_id,
                thread_title=thread_title,
                ui_msgs=ui_msgs,
                agent_msgs=agent_msgs
            )
            
            session.add(chat_history)
            session.commit()
            print(f"Chat history created for thread_id: {thread_id}")
            return True
            
        except SQLAlchemyError as e:
            print(f"Error creating chat history: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_chat_history(self, thread_id: str) -> Optional[ChatHistory]:
        """Get chat history by thread_id."""
        session = self.db_manager.get_session()
        if not session:
            return None
        
        try:
            chat_history = session.query(ChatHistory).filter(
                ChatHistory.thread_id == thread_id,
                ChatHistory.deleted == False
            ).first()
            return chat_history
            
        except SQLAlchemyError as e:
            print(f"Error getting chat history: {e}")
            return None
        finally:
            session.close()
    
    def get_user_chat_histories(self, user_id: str) -> List[ChatHistory]:
        """Get all chat histories for a user."""
        session = self.db_manager.get_session()
        if not session:
            return []
        
        try:
            chat_histories = session.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.deleted == False
            ).order_by(ChatHistory.date.desc()).all()
            return chat_histories
            
        except SQLAlchemyError as e:
            print(f"Error getting user chat histories: {e}")
            return []
        finally:
            session.close()
    
    def update_chat_history(self, thread_id: str, **kwargs) -> bool:
        """Update chat history record."""
        session = self.db_manager.get_session()
        if not session:
            return False
        
        try:
            chat_history = session.query(ChatHistory).filter(
                ChatHistory.thread_id == thread_id
            ).first()
            
            if not chat_history:
                print(f"Chat history not found for thread_id: {thread_id}")
                return False
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(chat_history, key):
                    setattr(chat_history, key, value)
            
            session.commit()
            print(f"Chat history updated for thread_id: {thread_id}")
            return True
            
        except SQLAlchemyError as e:
            print(f"Error updating chat history: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def delete_chat_history(self, thread_id: str, soft_delete: bool = True) -> bool:
        """Delete chat history (soft delete by default)."""
        session = self.db_manager.get_session()
        if not session:
            return False
        
        try:
            if soft_delete:
                # Soft delete - mark as deleted
                chat_history = session.query(ChatHistory).filter(
                    ChatHistory.thread_id == thread_id
                ).first()
                
                if chat_history:
                    chat_history.deleted = True
                    session.commit()
                    print(f"Chat history soft deleted for thread_id: {thread_id}")
                    return True
                else:
                    print(f"Chat history not found for thread_id: {thread_id}")
                    return False
            else:
                # Hard delete - remove from database
                deleted_count = session.query(ChatHistory).filter(
                    ChatHistory.thread_id == thread_id
                ).delete()
                
                session.commit()
                if deleted_count > 0:
                    print(f"Chat history hard deleted for thread_id: {thread_id}")
                    return True
                else:
                    print(f"Chat history not found for thread_id: {thread_id}")
                    return False
                    
        except SQLAlchemyError as e:
            print(f"Error deleting chat history: {e}")
            session.rollback()
            return False
        finally:
            session.close()


def validate_environment_variables() -> bool:
    """Validate that all required environment variables are set."""
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file.")
        return False
    
    return True


def main():
    """Main function to build the database and tables."""
    print("Starting database setup with SQLAlchemy...")
    
    # Validate environment variables
    if not validate_environment_variables():
        return
    
    # Initialize the database manager
    db_manager = DatabaseManager(
        host=DB_HOST,
        port=DB_PORT,
        database_name=DB_NAME,
        username=DB_USERNAME,
        password=DB_PASSWORD
    )
    
    try:
        # Create database if it doesn't exist
        if not db_manager.create_database_if_not_exists():
            print("Failed to create database.")
            return
        
        # Initialize engine and session factory
        if not db_manager.initialize_engine():
            print("Failed to initialize database engine.")
            return
        
        # Create all tables
        if not db_manager.create_tables():
            print("Failed to create tables.")
            return
        
        # Verify table creation
        if db_manager.check_table_exists('chat_history'):
            print("✓ chat_history table verified.")
            
            # Show table info
            table_info = db_manager.get_table_info('chat_history')
            if table_info:
                print("Table columns:")
                for col in table_info:
                    print(f"  - {col['name']}: {col['type']}")
        
        print("Database setup completed successfully with SQLAlchemy!")
        
        # Example usage of the repository
        print("\n--- Testing ChatHistoryRepository ---")
        chat_repo = ChatHistoryRepository(db_manager)
        
        # Test creating a chat history record
        test_success = chat_repo.create_chat_history(
            thread_id="test_thread_001",
            user_id="test_user_001",
            thread_title="Test Chat Session",
            ui_msgs={"messages": ["Hello", "How are you?"]},
            agent_msgs={"responses": ["Hi there!", "I'm doing well, thank you!"]}
        )
        
        if test_success:
            print("✓ Test chat history record created successfully.")
            
            # Test retrieving the record
            retrieved = chat_repo.get_chat_history("test_thread_001")
            if retrieved:
                print(f"✓ Retrieved chat history: {retrieved.thread_title}")
            else:
                print("✗ Failed to retrieve chat history.")
        
    except Exception as e:
        print(f"Error during database setup: {e}")
    finally:
        # Clean up
        db_manager.close()


if __name__ == "__main__":
    main()
