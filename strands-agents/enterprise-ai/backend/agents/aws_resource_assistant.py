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



model_list = [
    'us.amazon.nova-pro-v1:0',
    'us.amazon.nova-lite-v1:0',
    'us.anthropic.claude-3-haiku-20240307-v1:0',
    'us.anthropic.claude-3-sonnet-20240229-v1:0',
    'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    'us.anthropic.claude-3-5-haiku-20241022-v1:0',
    'us.anthropic.claude-3-5-sonnet-20240620-v1:0',
    
    'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    'us.anthropic.claude-sonnet-4-20250514-v1:0',
]


class AWSResourcesAgent(AgentBase):
    def __init__(self, thought_queue):
        self.util = Utility()
        self.thought_queue = thought_queue
        self.config = Config()

    def agent_callback_handler(self, **kwargs):
        common_agent_callback_handler(thought_queue=self.thought_queue, **kwargs)

    def aws_resources_tool(self):
        @tool 
        def aws_resource_assistant(user_input: str) -> dict:
            """
            Use this tool to search for resources in AWS account
            
            Args:
                user_input (str): question asked by user
                
            Returns:
                dict: a dictionary containing answer to user's question 
                
            """
            
            SYSTEM_PROMPT =f"""
                    Use available tools to answer user's question.
                    follow step by step process to perform the actions

                    """
            mcp_tools = MCPProvider().get_tools_for_mcp_server('awslabs.aws-api-mcp-server')
            
            
            response, agent = super(AWSResourcesAgent, self).invoke_agent(
                                          system_prompt=SYSTEM_PROMPT,
                                          user_input=user_input,
                                          models=model_list,
                                          tools=mcp_tools)
            
            
            self.thought_queue.put('DONE')

            return str(response)

        return aws_resource_assistant


