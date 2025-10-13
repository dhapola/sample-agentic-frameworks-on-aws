import random
from datetime import datetime
from faker import Faker
from db_connection import db

fake = Faker('en_IN')

states_cities = [
    # Major commercial centers (higher representation)
    ('Karnataka', 'Bangalore'),
    ('Tamil Nadu', 'Chennai'),
    ('Maharashtra', 'Mumbai'),
    ('West Bengal', 'Kolkata'),
    ('Delhi', 'New Delhi'),
    ('Telangana', 'Hyderabad'),
    ('Gujarat', 'Ahmedabad'),
    ('Rajasthan', 'Jaipur'),
    ('Punjab', 'Ludhiana'),
    ('Kerala', 'Kochi'),
    ('Uttar Pradesh', 'Lucknow'),
    ('Madhya Pradesh', 'Bhopal'),
    ('Odisha', 'Bhubaneswar'),
    ('Assam', 'Guwahati'),
    ('Bihar', 'Patna'),
    # Additional states for better coverage
    ('Andhra Pradesh', 'Visakhapatnam'),
    ('Chhattisgarh', 'Raipur'),
    ('Goa', 'Panaji'),
    ('Haryana', 'Gurugram'),
    ('Himachal Pradesh', 'Shimla'),
    ('Jharkhand', 'Ranchi'),
    ('Uttarakhand', 'Dehradun'),
    ('Jammu and Kashmir', 'Srinagar'),
    ('Manipur', 'Imphal'),
    ('Meghalaya', 'Shillong'),
    ('Mizoram', 'Aizawl'),
    ('Nagaland', 'Kohima'),
    ('Sikkim', 'Gangtok'),
    ('Tripura', 'Agartala'),
    ('Arunachal Pradesh', 'Itanagar'),
    # Union Territories
    ('Chandigarh', 'Chandigarh'),
    ('Puducherry', 'Puducherry'),
    ('Ladakh', 'Leh'),
    ('Dadra and Nagar Haveli and Daman and Diu', 'Daman'),
    ('Lakshadweep', 'Kavaratti'),
    ('Andaman and Nicobar Islands', 'Port Blair')
]

merchant_names = [
    'Shree Ganesh Traders', 'Lakshmi Stores', 'Mumbai Electronics', 'Kolkata Books', 'Delhi Fashion Hub',
    'Hyderabad Spices', 'Ahmedabad Mart', 'Jaipur Jewels', 'Ludhiana Textiles', 'Kochi Supermarket',
    'Lucknow Crafts', 'Bhopal Hardware', 'Bhubaneswar Electronics', 'Guwahati Handlooms', 'Patna Grocery'
]

def random_gst(state_code):
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return f"{state_code:02d}{''.join(random.choices(letters, k=5))}{random.randint(1000,9999)}{random.choice(letters)}1Z{random.randint(1,9)}"

def insert_merchants():
    try:
        merchants_data = []
        for _ in range(100):
            state, city = random.choice(states_cities)
            merchant_data = {
                'name': random.choice(merchant_names) + f" {fake.company_suffix()}",
                'address': fake.street_address(),
                'city': city,
                'state': state,
                'pin_code': fake.postcode(),
                'contact_number': f"+91-{random.randint(7000000000, 9999999999)}",
                'email': fake.email(),
                'gst_number': random_gst(random.randint(1, 36))
            }
            merchants_data.append(merchant_data)

        sql = """
            INSERT INTO merchants (name, address, city, state, pin_code, contact_number, email, gst_number, created_at, updated_at) 
            VALUES (:name, :address, :city, :state, :pin_code, :contact_number, :email, :gst_number, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """

        db.execute_many(sql, merchants_data)
        print("Successfully inserted 100 merchants using SQLAlchemy.")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    insert_merchants()
