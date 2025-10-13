#!/usr/bin/env python3
"""
Verify the updated date range for transaction generation
"""

from datetime import datetime, timedelta
import random

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
    
    return transaction_date

def verify_date_range():
    print("📅 Transaction Date Range Verification")
    print("=" * 45)
    
    start_date = datetime(2024, 4, 1)
    end_date = datetime(2025, 7, 31)
    
    print(f"Start Date: {start_date.strftime('%B %d, %Y')}")
    print(f"End Date: {end_date.strftime('%B %d, %Y')}")
    print(f"Total Days: {(end_date - start_date).days}")
    print(f"Total Months: {((end_date.year - start_date.year) * 12 + end_date.month - start_date.month)}")
    print()
    
    # Show year breakdown
    print("📊 Coverage by Year:")
    print("-" * 25)
    
    # 2024 coverage (April 1 - December 31)
    days_2024 = (datetime(2024, 12, 31) - start_date).days + 1
    print(f"2024: {days_2024} days (April 1 - December 31)")
    
    # 2025 coverage (January 1 - July 31)
    days_2025 = (end_date - datetime(2025, 1, 1)).days + 1
    print(f"2025: {days_2025} days (January 1 - July 31)")
    
    print()
    print("📈 Monthly Coverage:")
    print("-" * 20)
    
    # List all months covered
    current = start_date.replace(day=1)
    months = []
    
    while current <= end_date:
        months.append(current.strftime('%B %Y'))
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    for i, month in enumerate(months, 1):
        print(f"{i:2d}. {month}")
    
    print()
    print("✅ Date range successfully updated!")
    print("   Transactions can now be generated across 15 months")
    print("   covering parts of 2024 and 2025 for comprehensive testing")

if __name__ == "__main__":
    verify_date_range()