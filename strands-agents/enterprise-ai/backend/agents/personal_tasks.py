
import sys
from utils.utility import Utility
from utils.utility import Utility
from providers.mcp_provider import MCPProvider
from strands import Agent, tool
from strands.models import BedrockModel
from agents.agent_callback_handler import common_agent_callback_handler
from config import Config
from agents.agent_base import AgentBase

model_id = ''

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


class PersonalTasksAgent(AgentBase):

    def __init__(self, thought_queue):
        self.util = Utility()
        self.thought_queue = thought_queue
        self.config = Config()

    def agent_callback_handler(self, **kwargs):
        common_agent_callback_handler(thought_queue=self.thought_queue, **kwargs)


    def personal_task_manager_tool(self):

        @tool 
        def quip_tasks_assistant(user_input: str):
            '''
            This tool performs personal task management actions like retrieving outstanding tasks, all tasks, marking tasks complete.

            Args:
                user_input (str): action requested by user
                
            Returns:
                dict: a dictionary containing answer
            '''

            SYSTEM_PROMPT ="""
                    You are personal task assistant. Use tools to manage tasks. Provide your response in markdown format. Task list should be numbered.
                    """
            
            mcp_tools = MCPProvider().get_tools_for_mcp_server('d2-quip-mcp-server')

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

            # #self.util.log_data('calling quip task agent')
            # response = agent(user_input)
            # content = str(response)
            #self.util.log_data(f'\n\nquip task response  ==> {content}\n\n')
            
            response, agent = super(PersonalTasksAgent, self).invoke_agent(
                                                    system_prompt=SYSTEM_PROMPT,
                                                    user_input=user_input,
                                                    models=model_list,
                                                    tools=mcp_tools)
            return response
            
        
        return quip_tasks_assistant