import random
from datetime import datetime, timedelta
from db_connection import db

# Transaction statuses
transaction_statuses = ['COMPLETED', 'PENDING', 'FAILED', 'REFUNDED', 'CANCELLED']

# Transaction status weights (for realistic distribution)
status_weights = [0.75, 0.1, 0.08, 0.05, 0.02]  # 75% completed, 10% pending, etc.

# Zone definitions with states (complete coverage of all Indian states and UTs)
ZONES = {
    'SOUTH': ['Karnataka', 'Tamil Nadu', 'Telangana', 'Kerala', 'Andhra Pradesh', 'Puducherry', 'Lakshadweep'],
    'WEST': ['Maharashtra', 'Gujarat', 'Rajasthan', 'Goa', 'Dadra and Nagar Haveli and Daman and Diu'],
    'NORTH': ['Delhi', 'Punjab', 'Haryana', 'Uttar Pradesh', 'Himachal Pradesh', 'Uttarakhand', 'Jammu and Kashmir', 'Ladakh', 'Chandigarh'],
    'EAST': ['West Bengal', 'Odisha', 'Assam', 'Bihar', 'Jharkhand', 'Tripura', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Arunachal Pradesh', 'Sikkim', 'Andaman and Nicobar Islands'],
    'CENTRAL': ['Madhya Pradesh', 'Chhattisgarh']
}

# Zone transaction weights (South highest, then West, then North)
ZONE_WEIGHTS = {
    'SOUTH': 0.40,   # 40% of transactions
    'WEST': 0.25,    # 25% of transactions  
    'NORTH': 0.20,   # 20% of transactions
    'EAST': 0.10,    # 10% of transactions
    'CENTRAL': 0.05  # 5% of transactions
}

def get_pos_terminal_ids_by_zone():
    """Fetch existing POS terminal IDs grouped by zone based on merchant state"""
    try:
        # Join pos_terminals with merchants to get state information
        result = db.fetch_all("""
            SELECT pt.pos_terminal_id, m.state 
            FROM pos_terminals pt 
            JOIN merchants m ON pt.merchant_id = m.merchant_id 
            WHERE pt.status = 'ACTIVE'
        """)
        
        # Group terminals by zone
        terminals_by_zone = {zone: [] for zone in ZONES.keys()}
        
        for terminal_id, state in result:
            # Find which zone this state belongs to
            for zone, states in ZONES.items():
                if state in states:
                    terminals_by_zone[zone].append(terminal_id)
                    break
        
        return terminals_by_zone
    except Exception as e:
        print(f"Error fetching POS terminal IDs by zone: {e}")
        return {zone: [] for zone in ZONES.keys()}

def get_pos_terminal_ids():
    """Fetch existing POS terminal IDs from the database (legacy function for compatibility)"""
    try:
        result = db.fetch_all("SELECT pos_terminal_id FROM pos_terminals WHERE status = 'ACTIVE'")
        terminal_ids = [row[0] for row in result]
        return terminal_ids
    except Exception as e:
        print(f"Error fetching POS terminal IDs: {e}")
        return []

def get_payment_method_ids():
    """Fetch existing payment method IDs from the database"""
    try:
        result = db.fetch_all("SELECT payment_method_id FROM payment_methods")
        method_ids = [row[0] for row in result]
        return method_ids
    except Exception as e:
        print(f"Error fetching payment method IDs: {e}")
        return []

def get_payment_gateway_ids():
    """Fetch existing payment gateway IDs from the database"""
    try:
        result = db.fetch_all("SELECT payment_gateway_id FROM payment_gateways")
        gateway_ids = [row[0] for row in result]
        return gateway_ids
    except Exception as e:
        print(f"Error fetching payment gateway IDs: {e}")
        return []

def generate_transaction_date():
    """Generate a random transaction date within the specified range (April 1, 2024 to July 31, 2025)"""
    start_date = datetime(2024, 4, 1)
    end_date = datetime(2025, 7, 31)
    
    # Calculate the difference in days
    delta_days = (end_date - start_date).days
    
    # Generate a random number of days to add to the start date
    random_days = random.randint(0, delta_days)
    
    # Generate random hours, minutes, and seconds
    random_hours = random.randint(0, 23)
    random_minutes = random.randint(0, 59)
    random_seconds = random.randint(0, 59)
    
    # Calculate the transaction date
    transaction_date = start_date + timedelta(
        days=random_days,
        hours=random_hours,
        minutes=random_minutes,
        seconds=random_seconds
    )
    
    return transaction_date.strftime('%Y-%m-%d %H:%M:%S')

def generate_card_last4():
    """Generate last 4 digits of a card number"""
    return ''.join(random.choices('0123456789', k=4))

def generate_upi_transaction_id():
    """Generate a UPI transaction ID"""
    prefix = random.choice(['UPI', 'BHIM', 'GPay', 'PhonePe', 'Paytm'])
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8))
    return f"{prefix}-{timestamp}-{suffix}"

def insert_transactions(num_transactions=200000):
    try:
        # Get existing IDs from related tables
        terminals_by_zone = get_pos_terminal_ids_by_zone()
        payment_method_ids = get_payment_method_ids()
        gateway_ids = get_payment_gateway_ids()
        
        # Flatten all terminals for validation
        all_terminals = []
        for zone_terminals in terminals_by_zone.values():
            all_terminals.extend(zone_terminals)
        
        if not all_terminals or not payment_method_ids or not gateway_ids:
            print("Missing required data in related tables. Please run the other scripts first.")
            return
        
        # Print zone distribution
        print("Terminal distribution by zone:")
        for zone, terminals in terminals_by_zone.items():
            print(f"  {zone}: {len(terminals)} terminals")
        
        successful_inserts = 0
        batch_size = 100  # Insert in batches for better performance
        transactions_data = []
        
        print(f"Starting to insert {num_transactions} transactions...")
        print(f"Using {len(all_terminals)} terminals, {len(payment_method_ids)} payment methods, and {len(gateway_ids)} gateways")
        print("Transaction distribution by zone:")
        for zone, weight in ZONE_WEIGHTS.items():
            expected_transactions = int(num_transactions * weight)
            print(f"  {zone}: {expected_transactions} transactions ({weight*100:.1f}%)")
        
        for i in range(num_transactions):
            # Select zone based on weights
            zone = random.choices(list(ZONE_WEIGHTS.keys()), weights=list(ZONE_WEIGHTS.values()), k=1)[0]
            
            # Select random terminal from the chosen zone
            if terminals_by_zone[zone]:
                pos_terminal_id = random.choice(terminals_by_zone[zone])
            else:
                # Fallback to any available terminal if zone has no terminals
                pos_terminal_id = random.choice(all_terminals)
            
            payment_method_id = random.choice(payment_method_ids)
            payment_gateway_id = random.choice(gateway_ids)
            
            # Generate transaction amount (between ₹10 and ₹10,000)
            amount = round(random.uniform(10, 10000), 2)
            
            # Generate transaction status based on weighted distribution
            transaction_status = random.choices(transaction_statuses, weights=status_weights, k=1)[0]
            
            # Generate transaction date
            transaction_date = generate_transaction_date()
            
            # Card number last 4 digits (only for credit/debit card methods)
            card_last4 = None
            if payment_method_id in [1, 2]:  # Assuming 1 and 2 are Credit Card and Debit Card
                card_last4 = generate_card_last4()
            
            # UPI transaction ID (only for UPI method)
            upi_transaction_id = None
            if payment_method_id == 3:  # Assuming 3 is UPI
                upi_transaction_id = generate_upi_transaction_id()
            
            transaction_data = {
                'pos_terminal_id': pos_terminal_id,
                'payment_method_id': payment_method_id,
                'amount': amount,
                'transaction_status': transaction_status,
                'transaction_date': transaction_date,
                'card_number_last4': card_last4,
                'upi_transaction_id': upi_transaction_id,
                'payment_gateway_id': payment_gateway_id
            }
            transactions_data.append(transaction_data)
            
            # Insert in batches
            if len(transactions_data) >= batch_size:
                sql = """
                    INSERT INTO transactions (pos_terminal_id, payment_method_id, amount, 
                                            transaction_status, transaction_date, card_number_last4, 
                                            upi_transaction_id, payment_gateway_id) 
                    VALUES (:pos_terminal_id, :payment_method_id, :amount, 
                            :transaction_status, :transaction_date, :card_number_last4, 
                            :upi_transaction_id, :payment_gateway_id)
                """
                
                db.execute_many(sql, transactions_data)
                successful_inserts += len(transactions_data)
                print(f"Inserted batch of {len(transactions_data)} transactions. Total: {successful_inserts}")
                transactions_data = []
        
        # Insert remaining transactions
        if transactions_data:
            sql = """
                INSERT INTO transactions (pos_terminal_id, payment_method_id, amount, 
                                        transaction_status, transaction_date, card_number_last4, 
                                        upi_transaction_id, payment_gateway_id) 
                VALUES (:pos_terminal_id, :payment_method_id, :amount, 
                        :transaction_status, :transaction_date, :card_number_last4, 
                        :upi_transaction_id, :payment_gateway_id)
            """
            
            db.execute_many(sql, transactions_data)
            successful_inserts += len(transactions_data)
            
        print(f"Successfully inserted {successful_inserts} transactions using SQLAlchemy.")
    except Exception as e:
        print(f"Database error: {e}")

def verify_transaction_distribution():
    """Verify the actual transaction distribution by zone after generation"""
    try:
        print("\n=== Verifying Transaction Distribution by Zone ===")
        
        # Query to get transaction count by zone
        result = db.fetch_all("""
            SELECT m.state, COUNT(t.transaction_id) as transaction_count
            FROM transactions t
            JOIN pos_terminals pt ON t.pos_terminal_id = pt.pos_terminal_id
            JOIN merchants m ON pt.merchant_id = m.merchant_id
            GROUP BY m.state
            ORDER BY transaction_count DESC
        """)
        
        # Group by zone
        zone_counts = {zone: 0 for zone in ZONES.keys()}
        total_transactions = 0
        
        print("Transaction distribution by state:")
        for state, count in result:
            total_transactions += count
            # Find which zone this state belongs to
            for zone, states in ZONES.items():
                if state in states:
                    zone_counts[zone] += count
                    break
            
            # Find zone for display
            zone = "UNKNOWN"
            for z, states in ZONES.items():
                if state in states:
                    zone = z
                    break
            print(f"  {state}: {count:,} transactions (Zone: {zone})")
        
        print(f"\nTotal transactions: {total_transactions:,}")
        print("\nTransaction distribution by zone:")
        for zone, count in zone_counts.items():
            percentage = (count / total_transactions * 100) if total_transactions > 0 else 0
            expected_percentage = ZONE_WEIGHTS[zone] * 100
            print(f"  {zone}: {count:,} transactions ({percentage:.1f}% - Expected: {expected_percentage:.1f}%)")
            
    except Exception as e:
        print(f"Error verifying transaction distribution: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_transaction_distribution()
    else:
        insert_transactions(200000)  # Generate 200000 transactions
