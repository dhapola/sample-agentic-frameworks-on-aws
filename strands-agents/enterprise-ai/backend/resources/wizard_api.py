import time
import json
from flask_restful import Resource, request
from botocore.exceptions import ClientError, NoCredentialsError
from providers.bedrock_provider import get_bedrock_client
from utils.utility import Utility, GREEN_COLOR, RESET_COLOR, WHITE_COLOR, BLUE_COLOR
from providers.mcp_provider import MCPProvider


class ApiInsightsResource(Resource):
    
    def __init__(self):
        self.util = Utility()
    
    def get(self):
        """
        GET request handler for agent information
        Returns list of available tools from cache
        """
        try:
        # Get tools from cache
            tools = MCPProvider().get_tools()
            
            self.util.log_data("Returning list of available tools from cache")
            
            return tools
            
        except Exception as e:
            self.util.log_error(f"Unexpected error: {str(e)}")
            return {
                "error": "An unexpected error occurred",
                "details": str(e),
                "status": "error"
            }, 500

    # def post(self):
    #     """
    #     Invokes model with HTTP POST request
    #     Accepts:
    #         - modelid: string - The ID of the model to use
    #         - input: string - The input text to process
    #         - messages: list - List of messages for conversation context
    #     """
        
    #     start_time = time.time()
        
    #     # try:
    #     # Get data from POST request
    #     data = request.get_json()
        
    #     # Extract required fields
    #     modelid = data.get('modelid')
    #     input_text = data.get('input')
    #     messages = data.get('messages', [])
        
    #     # Validate required fields
    #     if not modelid:
    #         return {"error": "modelid is required", "status": "error"}, 400
    #     if not input_text:
    #         return {"error": "input is required", "status": "error"}, 400
        
    #     self.util.log_data(f"User input: {input_text}")
    #     self.util.log_data(f"Model: {modelid}")

    #     response = orchestrator_tool(user_input=input_text, model_id=modelid, messages=None) # todo - add messages
        
    #     execution_time = time.time() - start_time
    #     self.util.log_data(f"Total execution time: {execution_time:.2f} seconds")
        
    #     return json.loads(str(response))
        
        # except NoCredentialsError:
        #     self.util.log_error("No AWS credentials found")
        #     return {
        #         "error": "AWS credentials not found",
        #         "details": "Please configure your AWS credentials",
        #         "status": "error"
        #     }, 500
            
        # except ClientError as e:
        #     error_code = e.response.get('Error', {}).get('Code')
        #     error_message = e.response.get('Error', {}).get('Message')
            
        #     self.util.log_error(f"AWS Bedrock API error: {error_code} - {error_message}")
            
        #     return {
        #         "error": "Failed to invoke model",
        #         "details": f"{error_code}: {error_message}",
        #         "status": "error"
        #     }, 500
            
        # except Exception as e:
        #     self.util.log_error(f"Unexpected error: {str(e)}")
            
        #     return {
        #         "error": "An unexpected error occurred",
        #         "details": str(e),
        #         "status": "error"
        #     }, 500
