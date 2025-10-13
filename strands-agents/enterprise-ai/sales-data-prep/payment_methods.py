from db_connection import db

# Define payment methods with descriptions
payment_methods = [
    {
        'method_name': 'Credit Card',
        'description': 'Payment using credit cards from various banks and card networks'
    },
    {
        'method_name': 'Debit Card',
        'description': 'Payment using debit cards linked directly to bank accounts'
    },
    {
        'method_name': 'UPI',
        'description': 'Unified Payments Interface for instant real-time bank-to-bank payments'
    },
    {
        'method_name': 'Net Banking',
        'description': 'Direct payment through customer\'s bank portal'
    },
    {
        'method_name': 'Mobile Wallet',
        'description': 'Payment through digital wallets like Paytm, PhonePe, etc.'
    },
    {
        'method_name': 'QR Code Payment',
        'description': 'Scan and pay using QR codes linked to various payment methods'
    },
    {
        'method_name': 'Cash on Delivery',
        'description': 'Payment made in cash at the time of delivery'
    },
    {
        'method_name': 'EMI',
        'description': 'Equated Monthly Installments through credit cards or bank loans'
    },
    {
        'method_name': 'BNPL',
        'description': 'Buy Now Pay Later services'
    },
    {
        'method_name': 'Gift Card',
        'description': 'Payment using pre-loaded gift cards'
    }
]

def insert_payment_methods():
    try:
        sql = """
            INSERT INTO payment_methods (method_name, description) 
            VALUES (:method_name, :description)
        """

        db.execute_many(sql, payment_methods)
        print(f"Successfully inserted {len(payment_methods)} payment methods using SQLAlchemy.")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    insert_payment_methods()
