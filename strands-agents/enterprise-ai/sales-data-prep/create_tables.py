from db_connection import db
import sys


# Drop table statements (in reverse order due to foreign key constraints)
DROP_TABLE_STATEMENTS = [
    "DROP TABLE IF EXISTS daily_sales_report CASCADE;",
    "DROP TABLE IF EXISTS transactions CASCADE;",
    "DROP TABLE IF EXISTS pos_terminals CASCADE;",
    "DROP TABLE IF EXISTS payment_methods CASCADE;",
    "DROP TABLE IF EXISTS payment_gateways CASCADE;",
    "DROP TABLE IF EXISTS merchants CASCADE;",
    "DROP TABLE IF EXISTS state_zones CASCADE;"
]

# Table creation statements
CREATE_TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS merchants (
        merchant_id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        address VARCHAR(255),
        city VARCHAR(100),
        state VARCHAR(100),
        pin_code VARCHAR(10),
        contact_number VARCHAR(20),
        email VARCHAR(100),
        gst_number VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_gateways (
        payment_gateway_id SERIAL PRIMARY KEY,
        gateway_name VARCHAR(100) NOT NULL,
        gateway_type VARCHAR(20) NOT NULL,
        api_endpoint VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_methods (
        payment_method_id SERIAL PRIMARY KEY,
        method_name VARCHAR(50) NOT NULL,
        description VARCHAR(256)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS pos_terminals (
        pos_terminal_id SERIAL PRIMARY KEY,
        merchant_id INTEGER REFERENCES merchants(merchant_id),
        terminal_name VARCHAR(100),
        serial_number VARCHAR(100) NOT NULL UNIQUE,
        terminal_type VARCHAR(10) NOT NULL,
        location VARCHAR(255),
        status VARCHAR(20) DEFAULT 'ACTIVE',
        last_maintenance TIMESTAMP,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id SERIAL PRIMARY KEY,
        pos_terminal_id INTEGER REFERENCES pos_terminals(pos_terminal_id),
        payment_method_id INTEGER REFERENCES payment_methods(payment_method_id),
        amount NUMERIC(10, 2),
        transaction_status VARCHAR(20) DEFAULT 'PENDING',
        transaction_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        card_number_last4 VARCHAR(4),
        upi_transaction_id VARCHAR(100),
        payment_gateway_id INTEGER REFERENCES payment_gateways(payment_gateway_id)
    );
    """
]

def drop_tables():
    """Drop all existing tables to start fresh"""
    print("🗑️  Dropping existing tables...")
    print("-" * 40)
    
    for idx, stmt in enumerate(DROP_TABLE_STATEMENTS, 1):
        try:
            db.execute_sql(stmt)
            table_name = stmt.split()[4].replace("IF", "").replace("EXISTS", "").replace("CASCADE;", "").strip()
            print(f"✅ Dropped table: {table_name}")
        except Exception as e:
            print(f"❌ Error dropping table {idx}: {e}")
    
    print("✅ All tables dropped successfully!\n")

def create_tables():
    """Create all tables with fresh schema"""
    print("🏗️  Creating tables...")
    print("-" * 25)
    
    table_names = [
        "merchants",
        "payment_gateways", 
        "payment_methods",
        "pos_terminals",
        "transactions"
    ]
    
    for idx, stmt in enumerate(CREATE_TABLE_STATEMENTS, 1):
        try:
            db.execute_sql(stmt)
            print(f"✅ Created table: {table_names[idx-1]}")
        except Exception as e:
            print(f"❌ Error creating table {table_names[idx-1]}: {e}")
    
    print("✅ All tables created successfully!\n")

def recreate_tables():
    """Drop existing tables and create fresh ones"""
    print("🔄 Recreating all tables with fresh schema...")
    print("=" * 50)
    drop_tables()
    create_tables()
    print("🎉 Database schema recreated successfully!")
    print("   Ready for fresh data generation.")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "drop":
            drop_tables()
        elif sys.argv[1] == "recreate":
            recreate_tables()
        elif sys.argv[1] == "create":
            create_tables()
        else:
            print("Usage: python create_tables.py [drop|create|recreate]")
            print("  drop     - Drop all existing tables")
            print("  create   - Create tables (default)")
            print("  recreate - Drop and recreate all tables")
    else:
        # Default behavior - recreate tables for fresh start
        recreate_tables()

if __name__ == "__main__":
    main()
