import random
from datetime import datetime
from db_connection import db

# Define sample payment gateway data
gateway_names = [
    'Stripe', 'PayPal', 'Razorpay', 'Paytm', 'PhonePe', 
    'GooglePay', 'AmazonPay', 'CCAvenue', 'Instamojo', 'PayU',
    'BillDesk', 'Cashfree', 'EBS', 'JusPay', 'MobiKwik',
    'FreeCharge', 'Citrus Pay', 'Atom Technologies', 'Worldline', 'Pine Labs'
]

gateway_types = ['CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'WALLET', 'NET_BANKING', 'QR_CODE']

# API endpoint patterns for different gateways
api_endpoint_patterns = {
    'Stripe': 'https://api.stripe.com/v1/',
    'PayPal': 'https://api.paypal.com/v2/',
    'Razorpay': 'https://api.razorpay.com/v1/',
    'Paytm': 'https://securegw.paytm.in/v3/',
    'PhonePe': 'https://api.phonepe.com/apis/hermes/',
    'GooglePay': 'https://pay.google.com/gp/p/api/',
    'AmazonPay': 'https://api.amazon.com/pay/v2/',
    'CCAvenue': 'https://secure.ccavenue.com/transaction/v1/',
    'Instamojo': 'https://api.instamojo.com/v2/',
    'PayU': 'https://secure.payu.in/api/',
    'BillDesk': 'https://www.billdesk.com/pgidsk/PGIMerchantPayment',
    'Cashfree': 'https://api.cashfree.com/api/v2/',
    'EBS': 'https://secure.ebs.in/pg/ma/payment/request/',
    'JusPay': 'https://api.juspay.in/v1/',
    'MobiKwik': 'https://api.mobikwik.com/v1/',
    'FreeCharge': 'https://api.freecharge.in/v1/',
    'Citrus Pay': 'https://api.citruspay.com/v2/',
    'Atom Technologies': 'https://payment.atomtech.in/api/v1/',
    'Worldline': 'https://api.worldline.com/v1/',
    'Pine Labs': 'https://api.pinelabs.com/v2/'
}

def insert_payment_gateways():
    try:
        # Ensure we don't have more gateways than names
        num_gateways = min(20, len(gateway_names))
        
        gateways_data = []
        for i in range(num_gateways):
            gateway_name = gateway_names[i]
            gateway_type = random.choice(gateway_types)
            
            # Get the corresponding API endpoint or use a generic one
            api_endpoint = api_endpoint_patterns.get(gateway_name, f"https://api.{gateway_name.lower().replace(' ', '')}.com/v1/")
            
            gateway_data = {
                'gateway_name': gateway_name,
                'gateway_type': gateway_type,
                'api_endpoint': api_endpoint
            }
            gateways_data.append(gateway_data)

        sql = """
            INSERT INTO payment_gateways (gateway_name, gateway_type, api_endpoint, created_at, updated_at) 
            VALUES (:gateway_name, :gateway_type, :api_endpoint, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """

        db.execute_many(sql, gateways_data)
        print(f"Successfully inserted {num_gateways} payment gateways using SQLAlchemy.")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    insert_payment_gateways()
