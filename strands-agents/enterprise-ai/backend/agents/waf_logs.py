
import sys
import json
from utils.utility import Utility
from utils.utility import Utility
from providers.mcp_provider import MCPProvider

from strands import Agent, tool
from strands.models import BedrockModel
from utils.tool_message_schema import MessageSchema
from agents.agent_callback_handler import common_agent_callback_handler
from config import Config
from agents.agent_base import AgentBase


task_manager_model_id = 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
sql_generator_model_id  = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
response_generator_model_id = 'us.amazon.nova-lite-v1:0'

model_list = [
    'us.amazon.nova-lite-v1:0',
    'us.anthropic.claude-3-haiku-20240307-v1:0',
    'us.anthropic.claude-3-sonnet-20240229-v1:0',
    'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    'us.anthropic.claude-3-5-haiku-20241022-v1:0',
    'us.anthropic.claude-3-5-sonnet-20240620-v1:0',
    
    'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    'us.anthropic.claude-sonnet-4-20250514-v1:0',
]

class WAFLogsAgent(AgentBase):
    def __init__(self, thought_queue):
        self.util = Utility()
        self.thought_queue = thought_queue
        self.config = Config()

    def agent_callback_handler(self, **kwargs):
        common_agent_callback_handler(thought_queue=self.thought_queue, **kwargs)

    def was_tool(self):
        @tool 
        def waf_logs_assistant(user_input: str) -> dict:
            """
            Use this function to search for WAF logs
            
            Args:
                user_input (str): question asked by user
                
            Returns:
                dict: a dictionary containing answer to user's question 
                
            """
            
            SYSTEM_PROMPT =f"""
                    You are an agent designed to answer natural language questions by interacting with a ClickHouse database. Your workflow is as follows:
                    1. Understand the User Query:
                    - Carefully read and interpret the user's question, which will always be provided in natural language.
                    2. Schema Retrieval -> Retrieve the waf_logs table schema from the database using DESCRIBE TABLE statement, No need for follow ups
                    3. SQL Query Generation -> Use generate_sql_statement tool
                    4. Query Execution:
                    - Execute the generated SQL query against the ClickHouse database.
                    - Retrieve the results, handling any errors or ambiguities gracefully.

                    Key Responsibilities:
                    - Accurately interpret diverse natural language questions.
                    - Reliably map questions to the correct database tables and fields.
                    - Generate and execute ClickHouse SQL queries with high precision.
                    - Summarize and explain results in user-friendly language.

                    Decision Protocol:
                    - If the question is unclear, ask the user for clarification before proceeding.
                    - If multiple tables or joins are needed, construct the appropriate SQL statements.
                    - Always prioritize data privacy and query efficiency.

                    Table Schema below: 
                    Table name: default.waf_logs
                    Columns:
                    - timestamp (DateTime)
                    - format_version (UInt32)
                    - webacl_id (String)
                    - terminating_rule_id (String)
                    - terminating_rule_type (String)
                    - action (String)
                    - http_source_name (String)
                    - http_source_id (String)
                    - response_code_sent (Nullable(UInt16))
                    - http_client_ip (String)
                    - http_country (String)
                    - http_uri (String)
                    - http_args (String)
                    - http_http_version (String)
                    - http_http_method (String)
                    - http_request_id (String)
                    - http_fragment (String)
                    - http_scheme (String)
                    - http_host (String)
                    - header_host (String)
                    - header_connection (String)
                    - header_cache_control (String)
                    - header_upgrade_insecure_requests (String)
                    - header_user_agent (String)
                    - header_accept (String)
                    - header_accept_encoding (String)
                    - header_accept_language (String)
                    - header_if_none_match (String)
                    - header_if_modified_since (String)

                    """
            mcp_tools = MCPProvider().get_tools_for_mcp_server('clickhouse-mcp-server')
            
            # Get the tools from the MCP server
            tools = [self.generate_sql_statement]
            tools += mcp_tools
            
            response, agent = super(WAFLogsAgent, self).invoke_agent(
                                                    system_prompt=SYSTEM_PROMPT,
                                                    user_input=user_input,
                                                    models=model_list,
                                                    tools=tools)

            query_results = agent.messages[-2]
            query_results = query_results['content'][-1]['toolResult']['content']
            rows = []
            for row in query_results:
                row_text = row['text'].strip()
                json_data = json.loads(row_text )

                rows.append(json_data)

            return response

        return waf_logs_assistant

    @tool
    def generate_sql_statement(self, user_input: str, table_schema: str) -> str:
        """
        Generates a ClickHouse-compatible SQL statement based on a natural language user query and database schema.
        
        Args:
            user_input (str): The natural language query from the user describing what data they want to retrieve
            table_schema (str): A string representation of the database schema including tables, columns and their types
            
        Returns:
            str: A properly formatted SQL statement compatible with ClickHouse that addresses the user's query
        """
        
        self.util.log_header(function_name=sys._getframe().f_code.co_name)
        self.util.log_data('I need to generate SQL statement...')
        SYSTEM_PROMPT = f"""
                You are an expert SQL developer. 
                
                SQL Generation rules:
                - Output only SQL Statement, with no additional text or formatting
                - Do not add any decorators around the query
                - When generating SQL SELECT queries involving date filtering, follow these rules: 
                    - if year is not given then consider 2025
                    - Always use the >= (greater than or equal to) and <= (less than or equal to) operators in the WHERE clause to specify date ranges 
                    - Ensure that the date format matches the database schema
                    - do not use toString for datetime columns in where condition
                - Always convert DateTime column type (including DateTime64) to string using the toString() function
                - Always convert any column of type DateTime (including DateTime64) to a string using the toString() function. For example, if a table has a column named timestamp of type 
                - Do not select all columns using SELECT *. select all columns by names
                - SQL MUST be compatible with ClickHouse database. When using functions, Use only native ClickHouse native functions
                - String comparisons in the WHERE clause must be case-insensitive by converting both the column and the string literal to lowercase using the LOWER() function. 


                Example:
                    task: Find all blocked hosts on 10th May
                    Output: 
                        SELECT toString(timestamp), format_version, webacl_id, terminating_rule_id, terminating_rule_type, action, http_source_name, http_source_id, response_code_sent, http_client_ip, http_country, http_uri, http_args, http_http_version, http_http_method, http_request_id, http_fragment, http_scheme, http_host, header_host, header_connection, header_cache_control, header_upgrade_insecure_requests, header_user_agent, header_accept, header_accept_encoding, header_accept_language, header_if_none_match, header_if_modified_since
                        FROM <table_name> 
                        WHERE LOWER(action) = LOWER('BLOCK') AND
                        (timestamp >= '2025-05-10 00:00:00'
                        AND timestamp <= '2025-05-10 23:59:59')
            """
        formatted_query = f"""task: {user_input}

        Table Schema: {table_schema}

        """
        self.util.log_data(f"Formatted query: {formatted_query}")
        
        sql_gen_model = BedrockModel(model_id=sql_generator_model_id, 
                                # verbose=True, 
                                temperature=0.3,
                                region_name = self.config.aws_region)
        
        sql_agent = Agent(system_prompt=SYSTEM_PROMPT,model=sql_gen_model, tools=[], callback_handler=None) # no extra tools required
        agent_response = sql_agent(formatted_query)

        sql = str(agent_response)
        sql = self.util.clean_sql_string(sql)

        if len(sql) > 0:
            return sql
        else:
            return "I'm sorry I could not generate SQL statement for the provided inputs"

    ## This function is redundant
    @tool
    def generate_response(self, user_input: str, sql_query_results: str) -> str:
        """
        Generates a natural language response based on SQL query results and the original user question.

        Args:
            user_input (str): The original natural language question asked by the user
            sql_query_results (str): JSON string containing the results from executing the SQL query
            
        Returns:
            str: A natural language response that answers the user's question based on the SQL results
        """

        self.util.log_header(function_name=sys._getframe().f_code.co_name)
        self.util.log_data(f'SQL Query Results: {sql_query_results}')
        self.util.log_data('Preparing answer...')

        system_message = '''
        You are a professional and courteous log analysis agent. Your goal is to answer user's questions using provided context. You must NOT make any assumptions.
        '''

        try:

            prompt = f"""
                        question: {user_input}
                        context: {sql_query_results}
                        """
            
            response_gen_model = BedrockModel(model_id=response_generator_model_id, 
                                                verbose=True,
                                                region_name = self.config.aws_region)
                                                
            user_query_agent = Agent(system_prompt=system_message, model=response_gen_model, tools=[], callback_handler=None)
            agent_response = user_query_agent(prompt)
            response = str(agent_response)
            

            if len(response) > 0:
                return response
            
            return "I apologize, but I couldn't properly analyze your English language question. Could you please rephrase or provide more context?"
            
        except Exception as e:
            error = f"Exception occurred. Details: {e}"
            self.util.log_error(error)