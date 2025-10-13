from db_connection import db
from tabulate import tabulate
import pandas as pd
from datetime import datetime, timedelta

def execute_query(sql):
    try:
        result = db.fetch_all(sql)
        return result
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

def format_records(records, column_names):
    """Format records into a list of dictionaries"""
    result = []
    for record in records:
        row = {}
        for i, value in enumerate(record):
            row[column_names[i]] = value
        result.append(row)
    return result

def print_table(data, headers):
    """Print data in a formatted table"""
    if data:
        print(tabulate(data, headers=headers, tablefmt="grid", floatfmt=".2f"))
    else:
        print("No data found.")
    print()

def get_zone_summary():
    """Get sales summary by zone"""
    print("📊 Sales Summary by Zone")
    print("-" * 30)
    
    sql = """
    SELECT 
        zone,
        SUM(total_transactions) as total_transactions,
        SUM(total_sales) as total_sales,
        AVG(avg_transaction_value) as avg_transaction_value,
        SUM(completed_transactions) as completed_transactions,
        SUM(failed_transactions) as failed_transactions
    FROM daily_sales_report 
    GROUP BY zone 
    ORDER BY total_sales DESC
    """
    
    records = execute_query(sql)
    if records:
        columns = ["Zone", "Total Transactions", "Total Sales (₹)", "Avg Transaction Value (₹)", "Completed", "Failed"]
        data = []
        for record in records:
            data.append([
                record[0],  # zone
                record[1],  # total_transactions
                record[2],  # total_sales
                record[3],  # avg_transaction_value
                record[4],  # completed_transactions
                record[5]   # failed_transactions
            ])
        print_table(data, columns)

def get_monthly_trend():
    """Get monthly sales trend"""
    print("📈 Monthly Sales Trend")
    print("-" * 25)
    
    sql = """
    SELECT 
        year,
        month,
        month_name,
        SUM(total_transactions) as total_transactions,
        SUM(total_sales) as total_sales,
        AVG(avg_transaction_value) as avg_transaction_value
    FROM daily_sales_report 
    GROUP BY year, month, month_name
    ORDER BY year, month
    """
    
    records = execute_query(sql)
    if records:
        columns = ["Year", "Month", "Month Name", "Total Transactions", "Total Sales (₹)", "Avg Transaction Value (₹)"]
        data = []
        for record in records:
            data.append([
                record[0],  # year
                record[1],  # month
                record[2].strip(),  # month_name (strip whitespace)
                record[3],  # total_transactions
                record[4],  # total_sales
                record[5]   # avg_transaction_value
            ])
        print_table(data, columns)

def get_top_states():
    """Get top 5 performing states"""
    print("🏆 Top 5 Performing States")
    print("-" * 30)
    
    sql = """
    SELECT 
        state,
        zone,
        SUM(total_transactions) as total_transactions,
        SUM(total_sales) as total_sales,
        AVG(avg_transaction_value) as avg_transaction_value
    FROM daily_sales_report 
    GROUP BY state, zone
    ORDER BY total_sales DESC 
    LIMIT 5
    """
    
    records = execute_query(sql)
    if records:
        columns = ["State", "Zone", "Total Transactions", "Total Sales (₹)", "Avg Transaction Value (₹)"]
        data = []
        for record in records:
            data.append([
                record[0],  # state
                record[1],  # zone
                record[2],  # total_transactions
                record[3],  # total_sales
                record[4]   # avg_transaction_value
            ])
        print_table(data, columns)

def get_transaction_status_summary():
    """Get transaction status summary"""
    print("📋 Transaction Status Summary")
    print("-" * 35)
    
    sql = """
    SELECT 
        SUM(total_transactions) as total_transactions,
        SUM(completed_transactions) as completed_transactions,
        SUM(failed_transactions) as failed_transactions,
        SUM(pending_transactions) as pending_transactions,
        SUM(refunded_transactions) as refunded_transactions,
        SUM(cancelled_transactions) as cancelled_transactions
    FROM daily_sales_report
    """
    
    records = execute_query(sql)
    if records and records[0][0] is not None:
        record = records[0]
        total = record[0] or 0
        completed = record[1] or 0
        failed = record[2] or 0
        pending = record[3] or 0
        refunded = record[4] or 0
        cancelled = record[5] or 0
        
        # Calculate percentages
        data = [
            ["Completed", completed, f"{(completed/total*100):.1f}%" if total > 0 else "0%"],
            ["Failed", failed, f"{(failed/total*100):.1f}%" if total > 0 else "0%"],
            ["Pending", pending, f"{(pending/total*100):.1f}%" if total > 0 else "0%"],
            ["Refunded", refunded, f"{(refunded/total*100):.1f}%" if total > 0 else "0%"],
            ["Cancelled", cancelled, f"{(cancelled/total*100):.1f}%" if total > 0 else "0%"],
            ["Total", total, "100.0%" if total > 0 else "0%"]
        ]
        
        columns = ["Status", "Count", "Percentage"]
        print_table(data, columns)
    else:
        print("No transaction data found. Please ensure the sales report table has been populated.")
        print()

def get_quarterly_performance():
    """Get quarterly performance analysis"""
    print("📅 Quarterly Performance Analysis")
    print("-" * 40)
    
    sql = """
    SELECT 
        year,
        quarter,
        SUM(total_transactions) as total_transactions,
        SUM(total_sales) as total_sales,
        AVG(avg_transaction_value) as avg_transaction_value,
        COUNT(DISTINCT state) as states_covered
    FROM daily_sales_report 
    GROUP BY year, quarter
    ORDER BY year, quarter
    """
    
    records = execute_query(sql)
    if records:
        columns = ["Year", "Quarter", "Total Transactions", "Total Sales (₹)", "Avg Transaction Value (₹)", "States Covered"]
        data = []
        for record in records:
            data.append([
                record[0],  # year
                f"Q{record[1]}",  # quarter
                record[2],  # total_transactions
                record[3],  # total_sales
                record[4],  # avg_transaction_value
                record[5]   # states_covered
            ])
        print_table(data, columns)

if __name__ == "__main__":
    print("🔍 Sales Report Analysis")
    print("=" * 50)
    
    # Get total number of records
    records = execute_query("SELECT COUNT(*) FROM daily_sales_report")
    if records:
        count = records[0][0]
        print(f"Total daily report records: {count}")
        print()
    
    # Run various reports
    get_zone_summary()
    get_monthly_trend()
    get_top_states()
    get_transaction_status_summary()
    get_quarterly_performance()
    
    print("✅ Report analysis complete!")
