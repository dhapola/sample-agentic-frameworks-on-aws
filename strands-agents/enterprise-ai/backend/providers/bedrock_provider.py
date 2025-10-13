import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError
from utils.utility import Utility
from config import Config


def get_bedrock_client():
    """
    Creates and returns a boto3 client for Amazon Bedrock
    
    Returns:
        boto3.client: Configured Bedrock client
        
    Raises:
        NoCredentialsError: If AWS credentials are not found
        Exception: For other unexpected errors
    """

    config = Config()
    util = Utility()
    try:

        util.log_data(f'Selected AWS Region: {config.aws_region}')
        
        # Create a Bedrock client
        bedrock_client = boto3.client(
            service_name='bedrock',
            region_name=config.aws_region
        )
        
        return bedrock_client
        
    except NoCredentialsError:
        util.log_error("No AWS credentials found")
        raise
    except Exception as e:
        util.log_error(f"Error creating Bedrock client: {str(e)}")
        raise
