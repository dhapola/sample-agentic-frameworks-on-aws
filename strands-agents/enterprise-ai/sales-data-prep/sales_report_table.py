from db_connection import db

# Define SQL statements as separate statements (RDS Data API doesn't support multi-statements)
CREATE_STATE_ZONES_TABLE = """
CREATE TABLE IF NOT EXISTS state_zones (
    state_name VARCHAR(100) PRIMARY KEY,
    zone VARCHAR(20) NOT NULL
);
"""

# Insert statements for state zones - we'll do these one by one
STATE_ZONE_MAPPINGS = [
    # South Zone
    ("Karnataka", "South"),
    ("Tamil Nadu", "South"),
    ("Kerala", "South"),
    ("Andhra Pradesh", "South"),
    ("Telangana", "South"),
    ("Puducherry", "South"),
    ("Lakshadweep", "South"),
    # West Zone
    ("Maharashtra", "West"),
    ("Gujarat", "West"),
    ("Rajasthan", "West"),
    ("Goa", "West"),
    ("Dadra and Nagar Haveli and Daman and Diu", "West"),
    # Central Zone
    ("Madhya Pradesh", "Central"),
    ("Chhattisgarh", "Central"),
    # North Zone
    ("Uttar Pradesh", "North"),
    ("Delhi", "North"),
    ("Haryana", "North"),
    ("Punjab", "North"),
    ("Himachal Pradesh", "North"),
    ("Uttarakhand", "North"),
    ("Jammu and Kashmir", "North"),
    ("Ladakh", "North"),
    ("Chandigarh", "North"),
    # East Zone (including Northeast states)
    ("West Bengal", "East"),
    ("Bihar", "East"),
    ("Jharkhand", "East"),
    ("Odisha", "East"),
    ("Assam", "East"),
    ("Meghalaya", "East"),
    ("Manipur", "East"),
    ("Mizoram", "East"),
    ("Nagaland", "East"),
    ("Tripura", "East"),
    ("Sikkim", "East"),
    ("Arunachal Pradesh", "East"),
    ("Andaman and Nicobar Islands", "East")
]

# Create daily sales report table
CREATE_SALES_REPORT_TABLE = """
CREATE TABLE IF NOT EXISTS daily_sales_report (
    report_id SERIAL PRIMARY KEY,
    transaction_date DATE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    state VARCHAR(100) NOT NULL,
    zone VARCHAR(20) NOT NULL,
    total_transactions INT NOT NULL,
    total_sales NUMERIC(12, 2) NOT NULL,
    avg_transaction_value NUMERIC(10, 2) NOT NULL,
    completed_transactions INT NOT NULL,
    failed_transactions INT NOT NULL,
    pending_transactions INT NOT NULL,
    refunded_transactions INT NOT NULL,
    cancelled_transactions INT NOT NULL,
    UNIQUE (transaction_date, state)
);
"""

# Create indexes separately
CREATE_INDEX_DATE = """
CREATE INDEX IF NOT EXISTS idx_daily_sales_date ON daily_sales_report(transaction_date);
"""

CREATE_INDEX_STATE = """
CREATE INDEX IF NOT EXISTS idx_daily_sales_state ON daily_sales_report(state);
"""

CREATE_INDEX_ZONE = """
CREATE INDEX IF NOT EXISTS idx_daily_sales_zone ON daily_sales_report(zone);
"""

CREATE_INDEX_YEAR_QUARTER = """
CREATE INDEX IF NOT EXISTS idx_daily_sales_year_quarter ON daily_sales_report(year, quarter);
"""

# SQL to populate the daily sales report table
POPULATE_SALES_REPORT = """
INSERT INTO daily_sales_report (
    transaction_date,
    year,
    quarter,
    month,
    month_name,
    state,
    zone,
    total_transactions,
    total_sales,
    avg_transaction_value,
    completed_transactions,
    failed_transactions,
    pending_transactions,
    refunded_transactions,
    cancelled_transactions
)
SELECT 
    DATE(t.transaction_date) AS transaction_date,
    EXTRACT(YEAR FROM t.transaction_date) AS year,
    EXTRACT(QUARTER FROM t.transaction_date) AS quarter,
    EXTRACT(MONTH FROM t.transaction_date) AS month,
    TO_CHAR(t.transaction_date, 'Month') AS month_name,
    m.state,
    sz.zone,
    COUNT(t.transaction_id) AS total_transactions,
    SUM(t.amount) AS total_sales,
    CASE 
        WHEN COUNT(t.transaction_id) > 0 THEN ROUND(SUM(t.amount) / COUNT(t.transaction_id), 2)
        ELSE 0
    END AS avg_transaction_value,
    COUNT(CASE WHEN t.transaction_status = 'COMPLETED' THEN 1 END) AS completed_transactions,
    COUNT(CASE WHEN t.transaction_status = 'FAILED' THEN 1 END) AS failed_transactions,
    COUNT(CASE WHEN t.transaction_status = 'PENDING' THEN 1 END) AS pending_transactions,
    COUNT(CASE WHEN t.transaction_status = 'REFUNDED' THEN 1 END) AS refunded_transactions,
    COUNT(CASE WHEN t.transaction_status = 'CANCELLED' THEN 1 END) AS cancelled_transactions
FROM 
    transactions t
JOIN 
    pos_terminals pt ON t.pos_terminal_id = pt.pos_terminal_id
JOIN 
    merchants m ON pt.merchant_id = m.merchant_id
JOIN 
    state_zones sz ON m.state = sz.state_name
GROUP BY 
    DATE(t.transaction_date),
    EXTRACT(YEAR FROM t.transaction_date),
    EXTRACT(QUARTER FROM t.transaction_date),
    EXTRACT(MONTH FROM t.transaction_date),
    TO_CHAR(t.transaction_date, 'Month'),
    m.state,
    sz.zone
ORDER BY 
    transaction_date, state;
"""

def execute_sql(sql, description):
    try:
        db.execute_sql(sql)
        print(f"✅ {description} - Success")
        return True
    except Exception as e:
        print(f"❌ {description} - Failed: {e}")
        return False

def insert_state_zone(state, zone):
    sql = """
    INSERT INTO state_zones (state_name, zone) 
    VALUES (:state_name, :zone)
    ON CONFLICT (state_name) DO UPDATE SET zone = :zone
    """
    try:
        db.execute_sql(sql, {'state_name': state, 'zone': zone})
        return True
    except Exception as e:
        print(f"❌ Error inserting state zone mapping for {state}: {e}")
        return False

def create_sales_report_table():
    print("Creating sales report tables and data...")
    
    # Create state zones mapping table
    if execute_sql(CREATE_STATE_ZONES_TABLE, "Creating state zones mapping table"):
        # Insert state zone mappings
        print("Inserting state zone mappings...")
        success_count = 0
        for state, zone in STATE_ZONE_MAPPINGS:
            if insert_state_zone(state, zone):
                success_count += 1
        
        print(f"✅ Inserted {success_count}/{len(STATE_ZONE_MAPPINGS)} state zone mappings")
    
    # Create daily sales report table
    if execute_sql(CREATE_SALES_REPORT_TABLE, "Creating daily sales report table"):
        # Create indexes
        execute_sql(CREATE_INDEX_DATE, "Creating date index")
        execute_sql(CREATE_INDEX_STATE, "Creating state index")
        execute_sql(CREATE_INDEX_ZONE, "Creating zone index")
        execute_sql(CREATE_INDEX_YEAR_QUARTER, "Creating year-quarter index")
        
        # Populate daily sales report table
        execute_sql(POPULATE_SALES_REPORT, "Populating daily sales report table")
    
    # Get count of records in the report table
    try:
        result = db.fetch_one("SELECT COUNT(*) FROM daily_sales_report")
        count = result[0]
        print(f"📊 Generated {count} daily sales report records")
        
        # Import and run the ensure_complete_data function
        print("Ensuring complete data for all states and months...")
        print("Running query_sales_report.py to fill in any missing data...")
        
        # Execute the script as a separate process
        import subprocess
        result = subprocess.run(['python', 'query_sales_report.py'], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Errors: {result.stderr}")
    except Exception as e:
        print(f"❌ Error counting report records: {e}")

if __name__ == "__main__":
    create_sales_report_table()
