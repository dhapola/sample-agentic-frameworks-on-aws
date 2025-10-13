"""
Database migration utilities for schema changes.
"""
import os
from typing import List, Dict, Any
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from database_config import init_database, db_connection
from models import Base


class DatabaseMigration:
    """Database migration utility class."""
    
    def __init__(self):
        self.engine = None
    
    def initialize(self) -> bool:
        """Initialize database connection."""
        if not init_database():
            return False
        
        self.engine = db_connection.get_engine()
        return self.engine is not None
    
    def get_existing_tables(self) -> List[str]:
        """Get list of existing tables in the database."""
        if not self.engine:
            return []
        
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except SQLAlchemyError as e:
            print(f"Error getting table names: {e}")
            return []
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        if not self.engine:
            return []
        
        try:
            inspector = inspect(self.engine)
            return inspector.get_columns(table_name)
        except SQLAlchemyError as e:
            print(f"Error getting columns for table {table_name}: {e}")
            return []
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        return table_name in self.get_existing_tables()
    
    def create_all_tables(self) -> bool:
        """Create all tables defined in models."""
        if not self.engine:
            print("Database engine not initialized.")
            return False
        
        try:
            Base.metadata.create_all(bind=self.engine)
            print("All tables created successfully.")
            return True
        except SQLAlchemyError as e:
            print(f"Error creating tables: {e}")
            return False
    
    def drop_all_tables(self) -> bool:
        """Drop all tables (use with caution!)."""
        if not self.engine:
            print("Database engine not initialized.")
            return False
        
        try:
            Base.metadata.drop_all(bind=self.engine)
            print("All tables dropped successfully.")
            return True
        except SQLAlchemyError as e:
            print(f"Error dropping tables: {e}")
            return False
    
    def execute_sql(self, sql_statement: str) -> bool:
        """Execute a raw SQL statement."""
        if not self.engine:
            print("Database engine not initialized.")
            return False
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql_statement))
                conn.commit()
            print(f"SQL executed successfully: {sql_statement[:50]}...")
            return True
        except SQLAlchemyError as e:
            print(f"Error executing SQL: {e}")
            return False
    
    def migrate_from_old_schema(self) -> bool:
        """Migrate from old boto3/psycopg2 schema to SQLAlchemy schema."""
        print("Starting migration from old schema...")
        
        # Check if old tables exist and migrate data if needed
        existing_tables = self.get_existing_tables()
        
        if 'chat_history' in existing_tables:
            print("chat_history table already exists.")
            
            # Check if the table has the correct schema
            columns = self.get_table_columns('chat_history')
            column_names = [col['name'] for col in columns]
            
            expected_columns = ['thread_id', 'user_id', 'thread_title', 'ui_msgs', 'agent_msgs', 'date', 'deleted']
            missing_columns = [col for col in expected_columns if col not in column_names]
            
            if missing_columns:
                print(f"Missing columns in chat_history: {missing_columns}")
                # Add missing columns if needed
                for col in missing_columns:
                    if col == 'deleted':
                        sql = "ALTER TABLE chat_history ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT FALSE;"
                        self.execute_sql(sql)
            else:
                print("chat_history table schema is up to date.")
        else:
            print("chat_history table does not exist. Creating new table...")
            self.create_all_tables()
        
        print("Migration completed.")
        return True
    
    def backup_table(self, table_name: str, backup_suffix: str = "_backup") -> bool:
        """Create a backup of a table."""
        if not self.table_exists(table_name):
            print(f"Table {table_name} does not exist.")
            return False
        
        backup_table_name = f"{table_name}{backup_suffix}"
        sql = f"CREATE TABLE {backup_table_name} AS SELECT * FROM {table_name};"
        
        return self.execute_sql(sql)
    
    def restore_table(self, table_name: str, backup_suffix: str = "_backup") -> bool:
        """Restore a table from backup."""
        backup_table_name = f"{table_name}{backup_suffix}"
        
        if not self.table_exists(backup_table_name):
            print(f"Backup table {backup_table_name} does not exist.")
            return False
        
        # Drop existing table and restore from backup
        sql_drop = f"DROP TABLE IF EXISTS {table_name};"
        sql_restore = f"CREATE TABLE {table_name} AS SELECT * FROM {backup_table_name};"
        
        return self.execute_sql(sql_drop) and self.execute_sql(sql_restore)
    
    def show_database_info(self):
        """Show information about the database."""
        print("\n=== Database Information ===")
        
        if not self.engine:
            print("Database engine not initialized.")
            return
        
        # Show existing tables
        tables = self.get_existing_tables()
        print(f"Existing tables ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")
        
        # Show details for each table
        for table in tables:
            print(f"\nTable: {table}")
            columns = self.get_table_columns(table)
            print("  Columns:")
            for col in columns:
                nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                print(f"    - {col['name']}: {col['type']} {nullable}")
        
        print("\n" + "="*30)


def main():
    """Main migration function."""
    print("=== Database Migration Utility ===\n")
    
    migration = DatabaseMigration()
    
    if not migration.initialize():
        print("Failed to initialize database connection.")
        return
    
    try:
        # Show current database state
        migration.show_database_info()
        
        # Perform migration
        print("\nPerforming migration...")
        migration.migrate_from_old_schema()
        
        # Show updated database state
        print("\nAfter migration:")
        migration.show_database_info()
        
    except Exception as e:
        print(f"Error during migration: {e}")
    
    finally:
        db_connection.close()


if __name__ == "__main__":
    main()
