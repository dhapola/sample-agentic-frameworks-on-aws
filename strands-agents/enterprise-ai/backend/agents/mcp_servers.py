
import sys
from utils.utility import Utility
from utils.utility import Utility
from providers.mcp_provider import MCPProvider
from strands import Agent, tool
from strands.models import BedrockModel
from agents.agent_callback_handler import common_agent_callback_handler
from config import Config
from agents.agent_base import AgentBase

model_id = 'apac.anthropic.claude-3-haiku-20240307-v1:0' #'apac.anthropic.claude-3-7-sonnet-20250219-v1:0'


class MCPServersAgent(AgentBase):

    def __init__(self, thought_queue):
        self.util = Utility()
        self.thought_queue = thought_queue
        self.config = Config()

    def agent_callback_handler(self, **kwargs):
        common_agent_callback_handler(thought_queue=self.thought_queue, **kwargs)


    def mcp_servers_tool(self):

        @tool 
        def mcp_servers_assistant(user_input: str):
            '''
            This tool loads and calls various MCP servers to answer specialized questions

            Args:
                user_input (str): action requested by user
                
            Returns:
                dict: a dictionary containing answer
            '''

            SYSTEM_PROMPT ="""
                    You have many tools available. Use appropriate tool to answer the question.
                    """
            
            mcp_tools = []
            mcp_servers = MCPProvider().get_mcp_servers()
            for mcp_server in mcp_servers:
                mcp_tools = mcp_tools + MCPProvider().get_tools_for_mcp_server(mcp_server)

            response, agent = super(MCPServersAgent, self).invoke_agent(
                                                    system_prompt=SYSTEM_PROMPT,
                                                    user_input=user_input,
                                                    models=model_list,
                                                    tools=mcp_tools)
            return response


            #self.util.log_data(f'\nmcp_servers_assistant - mcp_tools--> {mcp_tools}')
            # model = BedrockModel(model_id=model_id, 
            #                     verbose=True, 
            #                     temperature=0.3,
            #                     region_name = self.config.aws_region)
            # agent = Agent(
            #     system_prompt=SYSTEM_PROMPT,
            #     model=model,
            #     tools=mcp_tools,
            #     callback_handler=self.agent_callback_handler
            # )

            # response = agent(user_input)
            # content = str(response)

            # return content
        
        return mcp_servers_assistant