import ast
import json
import re
from datetime import date
from utils.utility import Utility
from utils.utility import Utility, GREEN_COLOR, RESET_COLOR, WHITE_COLOR, BLUE_COLOR
from providers.mcp_provider import MCPProvider
from agents.agent_callback_handler import common_agent_callback_handler
from strands import Agent, tool
from strands.models import BedrockModel
from utils.tool_message_schema import MessageSchema
from decimal import Decimal
from config import Config
from agents.agent_base import AgentBase

# model_id = 'us.anthropic.claude-3-5-sonnet-20240620-v1:0'

SYSTEM_PROMPT = f"""
        You are a business analyst. you have been provided a postgresql database of payments. you need to answer questions from the data in db. Your workflow is as follows:
        1. Understand the question
        2. Table Schema Retrieval -> get the tables from the database and identify appropriate table having data for answering the question
        - Sample query to retrieve table schema: SELECT column_name, data_type, character_maximum_length FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = '<table_name>';
        3. Generate PostgreSQL compatible SQL query to fetch data from the tables
        4. Execute the generated SQL query


        Rules:
        - If multiple tables or joins are needed, construct valid PostgreSQL compatible SQL statement
        - Always prioritize data privacy and query efficiency.
        - Always return data from the table(s). Do not return instructions to use queries
        - Use ₹ currency symbol when needed.
        - Format numbers with commas as per Indian standards

        Available Tables:
        - daily_sales_report - use this table for daily, monthly, quarterly and yearly sales data
        - transactions - use this table for real time transaction information
        - payment_methods - use this table to find payment methods
        - payment_gateways - use this table to find payment gateways
        - merchants - use this table to find merchant details
        - pos_terminals - use this for POS terminals
    

        Today's date is {date.today().strftime('%Y-%m-%d')}

        """
        
        
model_list = [
    'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    'us.anthropic.claude-3-5-haiku-20241022-v1:0',
    'us.anthropic.claude-3-5-sonnet-20240620-v1:0',
    
    'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    'us.anthropic.claude-sonnet-4-20250514-v1:0',
    'us.anthropic.claude-3-sonnet-20240229-v1:0',
    'us.anthropic.claude-3-opus-20240229-v1:0',
    'us.anthropic.claude-3-haiku-20240307-v1:0'
]


class FintechSalesAgent(AgentBase):

    def __init__(self, thought_queue):
        super().__init__(thought_queue=thought_queue)
        self.util = Utility()
        self.thought_queue = thought_queue
        self.config = Config()

    
    def sales_analytics_assistant_tool(self):
        @tool 
        def sales_analytics_assistant(user_input: str) -> dict:
            """
            Use this tool for searching payment transactions and sales data
            
            Args:
                user_input (str): user's question
                
            Returns:
                dict: a dictionary containing natural language response & query results
            """
            

            mcp_tools = MCPProvider().get_tools_for_mcp_server('postgres-mcp-server')

            response, agent = super(FintechSalesAgent, self).invoke_agent(
                                          system_prompt=SYSTEM_PROMPT,
                                          user_input=user_input,
                                          models=model_list,
                                          tools=mcp_tools)

            query_results = agent.messages[-2]
            
            query_results = query_results['content'][-1]['toolResult']['content'][0]['text']
            
            query_results = re.sub(r"Decimal\('([0-9.]+)'\)", r"\1", query_results)
            query_results = ast.literal_eval(query_results)
            query_results = json.dumps(query_results)
            
            show_graph = len(query_results)>1
            
            return json.dumps(MessageSchema.create(response=str(response), query_results=query_results, show_graph=show_graph))
        return sales_analytics_assistant

