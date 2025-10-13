import random
from datetime import datetime, timedelta
from db_connection import db

# Terminal types
terminal_types = ['MOBILE', 'DESKTOP', 'KIOSK', 'HANDHELD', 'INTEGRATED']

# Terminal status options
terminal_statuses = ['ACTIVE', 'INACTIVE', 'MAINTENANCE', 'DECOMMISSIONED']

# Terminal name prefixes
terminal_prefixes = ['POS', 'Terminal', 'Checkout', 'Register', 'Station']

# Location descriptions
locations = [
    'Main Counter', 'Checkout Area', 'Customer Service Desk', 
    'Entrance', 'Exit', 'Floor 1', 'Floor 2', 'Billing Section',
    'Electronics Department', 'Grocery Section', 'Apparel Section'
]

def get_merchant_ids():
    """Fetch existing merchant IDs from the database"""
    try:
        result = db.fetch_all("SELECT merchant_id FROM merchants")
        merchant_ids = [row[0] for row in result]
        return merchant_ids
    except Exception as e:
        print(f"Error fetching merchant IDs: {e}")
        return []

def generate_serial_number():
    """Generate a unique serial number for POS terminals"""
    prefix = random.choice(['PT', 'ST', 'MT', 'KT'])
    middle = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    number = ''.join(random.choices('0123456789', k=6))
    return f"{prefix}-{middle}{number}"

def generate_maintenance_date():
    """Generate a random maintenance date within the last year"""
    days_ago = random.randint(0, 365)
    maintenance_date = datetime.now() - timedelta(days=days_ago)
    return maintenance_date.strftime('%Y-%m-%d %H:%M:%S')

def insert_pos_terminals():
    try:
        # Get existing merchant IDs
        merchant_ids = get_merchant_ids()
        
        if not merchant_ids:
            print("No merchants found in the database. Please run generate_merchants.py first.")
            return
        
        # Number of terminals to create (2-5 per merchant)
        num_terminals = 0
        terminals_data = []
        
        # Create terminals for each merchant
        for merchant_id in merchant_ids:
            # Create 2-5 terminals per merchant
            terminals_for_merchant = random.randint(2, 5)
            
            for _ in range(terminals_for_merchant):
                terminal_name = f"{random.choice(terminal_prefixes)} {random.randint(1, 99)}"
                serial_number = generate_serial_number()
                terminal_type = random.choice(terminal_types)
                location = random.choice(locations)
                status = random.choice(terminal_statuses)
                
                # 70% chance of having a maintenance date
                last_maintenance = None
                if random.random() < 0.7:
                    last_maintenance = generate_maintenance_date()
                
                terminal_data = {
                    'merchant_id': merchant_id,
                    'terminal_name': terminal_name,
                    'serial_number': serial_number,
                    'terminal_type': terminal_type,
                    'location': location,
                    'status': status,
                    'last_maintenance': last_maintenance
                }
                terminals_data.append(terminal_data)
                num_terminals += 1

        sql = """
            INSERT INTO pos_terminals (merchant_id, terminal_name, serial_number, terminal_type, 
                                     location, status, last_maintenance, created_at, updated_at) 
            VALUES (:merchant_id, :terminal_name, :serial_number, :terminal_type, 
                    :location, :status, :last_maintenance, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """

        db.execute_many(sql, terminals_data)
        print(f"Successfully inserted {num_terminals} POS terminals for {len(merchant_ids)} merchants using SQLAlchemy.")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    insert_pos_terminals()
