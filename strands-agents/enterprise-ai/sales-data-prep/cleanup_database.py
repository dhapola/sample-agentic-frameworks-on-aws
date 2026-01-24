#!/usr/bin/env python3
"""
Database cleanup utility for sales data preparation system
"""

from db_connection import db
import sys

def get_table_counts():
    """Get current record counts for all tables"""
    tables = [
        'merchants',
        'payment_gateways', 
        'payment_methods',
        'pos_terminals',
        'transactions',
        'state_zones',
        'daily_sales_report'
    ]
    
    counts = {}
    for table in tables:
        try:
            result = db.fetch_one(f"SELECT COUNT(*) FROM {table}")
            counts[table] = result[0] if result else 0
        except Exception:
            counts[table] = 0
    
    return counts

def show_current_data():
    """Display current data in the database"""
    print("📊 Current Database Status")
    print("=" * 30)
    
    counts = get_table_counts()
    total_records = sum(counts.values())
    
    if total_records == 0:
        print("✅ Database is empty - ready for fresh data generation")
        return False
    
    print("Current record counts:")
    for table, count in counts.items():
        if count > 0:
            print(f"  📋 {table}: {count:,} records")
    
    print(f"\n📈 Total records: {total_records:,}")
    return True

def truncate_all_tables():
    """Truncate all tables to remove data but keep schema"""
    print("\n🧹 Truncating all tables...")
    print("-" * 35)
    
    # Order matters due to foreign key constraints
    tables_to_truncate = [
        'daily_sales_report',
        'transactions', 
        'pos_terminals',
        'merchants',
        'payment_methods',
        'payment_gateways',
        'state_zones'
    ]
    
    try:
        # Disable foreign key checks temporarily
        #db.execute_sql("SET session_replication_role = replica;")
        
        for table in tables_to_truncate:
            try:
                db.execute_sql(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                print(f"✅ Truncated: {table}")
            except Exception as e:
                print(f"⚠️  Could not truncate {table}: {e}")
        
        # Re-enable foreign key checks
        db.execute_sql("SET session_replication_role = DEFAULT;")
        
        print("✅ All tables truncated successfully!")
        
    except Exception as e:
        print(f"❌ Error during truncation: {e}")
        # Try to re-enable foreign key checks
        try:
            db.execute_sql("SET session_replication_role = DEFAULT;")
        except:
            pass

def drop_all_tables():
    """Drop all tables completely"""
    print("\n🗑️  Dropping all tables...")
    print("-" * 30)
    
    drop_statements = [
        "DROP TABLE IF EXISTS daily_sales_report CASCADE;",
        "DROP TABLE IF EXISTS transactions CASCADE;",
        "DROP TABLE IF EXISTS pos_terminals CASCADE;",
        "DROP TABLE IF EXISTS payment_methods CASCADE;",
        "DROP TABLE IF EXISTS payment_gateways CASCADE;",
        "DROP TABLE IF EXISTS merchants CASCADE;",
        "DROP TABLE IF EXISTS state_zones CASCADE;"
    ]
    
    for stmt in drop_statements:
        try:
            db.execute_sql(stmt)
            table_name = stmt.split()[4].replace("IF", "").replace("EXISTS", "").replace("CASCADE;", "").strip()
            print(f"✅ Dropped: {table_name}")
        except Exception as e:
            print(f"❌ Error dropping table: {e}")
    
    print("✅ All tables dropped successfully!")

def confirm_action(action_name):
    """Ask user to confirm destructive action"""
    response = input(f"\n⚠️  Are you sure you want to {action_name}? (yes/no): ").lower().strip()
    return response in ['yes', 'y']

def main():
    print("🧹 Database Cleanup Utility")
    print("=" * 35)
    
    # Show current status
    has_data = show_current_data()
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == "status":
            # Just show status and exit
            return
            
        elif action == "truncate":
            if has_data and confirm_action("truncate all tables (remove data, keep schema)"):
                truncate_all_tables()
                print("\n🎉 Database cleaned! Schema preserved, ready for fresh data.")
            elif not has_data:
                print("\n✅ No data to truncate.")
                
        elif action == "drop":
            if confirm_action("drop all tables (remove schema and data)"):
                drop_all_tables()
                print("\n🎉 All tables dropped! Run create_tables.py to recreate schema.")
                
        elif action == "force-truncate":
            # Force truncate without confirmation (for scripts)
            if has_data:
                truncate_all_tables()
                print("\n🎉 Database cleaned! Ready for fresh data.")
            else:
                print("\n✅ No data to truncate.")
                
        else:
            print(f"\n❌ Unknown action: {action}")
            print_usage()
            
    else:
        # Interactive mode
        if not has_data:
            print("\n✅ Database is already clean!")
            return
            
        print("\nChoose an action:")
        print("1. Truncate tables (remove data, keep schema)")
        print("2. Drop tables (remove everything)")
        print("3. Show status only")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            if confirm_action("truncate all tables"):
                truncate_all_tables()
                print("\n🎉 Database cleaned! Ready for fresh data.")
        elif choice == "2":
            if confirm_action("drop all tables"):
                drop_all_tables()
                print("\n🎉 All tables dropped! Run create_tables.py to recreate.")
        elif choice == "3":
            pass  # Status already shown
        elif choice == "4":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice!")

def print_usage():
    print("\nUsage: python cleanup_database.py [action]")
    print("Actions:")
    print("  status         - Show current database status")
    print("  truncate       - Remove all data but keep schema")
    print("  drop           - Remove all tables and schema")
    print("  force-truncate - Truncate without confirmation (for scripts)")
    print("  (no action)    - Interactive mode")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)