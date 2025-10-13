"""
Database configuration settings for AIUI application.
Uses AWS Aurora PostgreSQL with authentication via AWS Secrets Manager.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DATABASE_CONFIG = {
    # AWS Aurora PostgreSQL configuration
    'host': os.environ.get('DB_HOST', ''),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', ''),
    'secret_arn': os.environ.get('DB_SECRET', ''),
    'region': os.environ.get('REGION', 'ap-south-1'),
    
    # Connection pool settings
    'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
    'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 0)),
    'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
    'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 1800)),
    
    # Query execution settings
    'statement_timeout': int(os.environ.get('DB_STATEMENT_TIMEOUT', 60000)),  # milliseconds
    'query_log_level': os.environ.get('DB_QUERY_LOG_LEVEL', 'DEBUG'),
}

# Create directory if it doesn't exist
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
