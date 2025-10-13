#!/bin/bash
echo "🚀 Starting fresh data generation..."
echo "=================================="

echo "Testing database connection..."
python test_connection.py

echo "Cleaning existing data..."
python cleanup_database.py force-truncate

echo "Recreating tables with fresh schema..."
python create_tables.py recreate

echo "Generating synthetic data for all tables..."
echo "1. Generating merchants data..."
python generate_merchants.py

echo "2. Generating payment gateways data..."
python payment_gateways.py

echo "3. Generating payment methods data..."
python payment_methods.py

echo "4. Generating POS terminals data..."
python pos_terminals.py

echo "5. Generating transactions data (20,000 rows)..."
python transactions.py

echo "6. Creating sales report aggregation table..."
python sales_report_table.py

echo "Data generation complete!"

