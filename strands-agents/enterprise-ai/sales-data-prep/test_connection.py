#!/usr/bin/env python3
"""
Test database connection for sales data preparation system
"""

from db_connection import db
import sys

def test_connection():
    """Test the database connection"""
    print("🔌 Testing Database Connection")
    print("-" * 35)
    
    try:
        # Test basic connection
        result = db.fetch_one("SELECT version();")
        if result:
            version = result[0]
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version.split(',')[0]}")
        
        # Test database name
        result = db.fetch_one("SELECT current_database();")
        if result:
            db_name = result[0]
            print(f"   Database: {db_name}")
        
        # Test user permissions
        result = db.fetch_one("SELECT current_user;")
        if result:
            user = result[0]
            print(f"   User: {user}")
        
        # Test table creation permissions
        try:
            db.execute_sql("CREATE TABLE IF NOT EXISTS connection_test (id SERIAL PRIMARY KEY);")
            db.execute_sql("DROP TABLE IF EXISTS connection_test;")
            print("✅ Database permissions: OK")
        except Exception as e:
            print(f"⚠️  Limited permissions: {e}")
        
        print("✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check if PostgreSQL is running")
        print("   2. Verify .env file configuration:")
        print("      - DB_HOST")
        print("      - DB_PORT") 
        print("      - DB_NAME")
        print("      - DB_USERNAME")
        print("      - DB_PASSWORD")
        print("   3. Ensure database exists and user has access")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)