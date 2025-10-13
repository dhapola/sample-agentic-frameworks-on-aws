"""
Database connection utility using SQLAlchemy for PostgreSQL
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseConnection:
    def __init__(self):
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_name = os.getenv("DB_NAME", "paymentsdb")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_username = os.getenv("DB_USERNAME")
        self.db_password = os.getenv("DB_PASSWORD")
        
        if not self.db_username or not self.db_password:
            raise ValueError("DB_USERNAME and DB_PASSWORD must be set in .env file")
        
        # Create connection string
        self.connection_string = f"postgresql://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        
        # Create engine
        self.engine = create_engine(self.connection_string, echo=False)
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_engine(self):
        """Get SQLAlchemy engine"""
        return self.engine
    
    def get_session(self):
        """Get SQLAlchemy session"""
        return self.SessionLocal()
    
    def execute_sql(self, sql_statement, parameters=None):
        """Execute a single SQL statement"""
        with self.engine.connect() as connection:
            if parameters:
                result = connection.execute(text(sql_statement), parameters)
            else:
                result = connection.execute(text(sql_statement))
            connection.commit()
            return result
    
    def execute_many(self, sql_statement, parameters_list):
        """Execute SQL statement with multiple parameter sets"""
        with self.engine.connect() as connection:
            result = connection.execute(text(sql_statement), parameters_list)
            connection.commit()
            return result
    
    def fetch_all(self, sql_statement, parameters=None):
        """Fetch all results from a SELECT query"""
        with self.engine.connect() as connection:
            if parameters:
                result = connection.execute(text(sql_statement), parameters)
            else:
                result = connection.execute(text(sql_statement))
            return result.fetchall()
    
    def fetch_one(self, sql_statement, parameters=None):
        """Fetch one result from a SELECT query"""
        with self.engine.connect() as connection:
            if parameters:
                result = connection.execute(text(sql_statement), parameters)
            else:
                result = connection.execute(text(sql_statement))
            return result.fetchone()

# Global database connection instance
db = DatabaseConnection()
