from strands.models import BedrockModel
from strands import Agent
from utils.utility import Utility
from config import Config
from agents.agent_callback_handler import common_agent_callback_handler
from strands.types.exceptions import ModelThrottledException

class AgentBase:
    def __init__(self, thought_queue):
        self.util = Utility()
        self.thought_queue = thought_queue
        self.config = Config()
        

    def agent_callback_handler(self, **kwargs):
        common_agent_callback_handler(thought_queue=self.thought_queue, **kwargs)

    
    def invoke_agent( self, models: list, 
                    tools: list, 
                    system_prompt: str, 
                    user_input: str,
                    temperature=0.3):
        
        for model_id in models:
            try:
                
                bedrock_model = BedrockModel(model_id=model_id, 
                                            # verbose=True, 
                                            temperature=0.3,
                                            region_name = self.config.aws_region)
                agent = Agent(
                    system_prompt=system_prompt,
                    model=bedrock_model,
                    tools=tools,
                    callback_handler=self.agent_callback_handler,
                )
                response = agent(user_input)
                return response, agent
            except ThrottlingException as e:
                self.util.log_error(f'Model {model_id} is throttling: {e}')
                continue
            except Exception as e:
                self.util.log_error(f'Error in invoke_agent: {e}')
                break
