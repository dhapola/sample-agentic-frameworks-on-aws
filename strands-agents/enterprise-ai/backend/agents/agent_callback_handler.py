import json
from utils.utility import Utility


def common_agent_callback_handler(thought_queue, **kwargs):    
    if "data" in kwargs:
        # Stream the model's thinking process
        thought_data = {
            "type": "thinking",
            "content": kwargs['data']
        }
        thought_queue.put(json.dumps(thought_data))

        
    elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
        # Stream tool usage information
        tool_data = {
            "type": "tool_use",
            "tool": kwargs['current_tool_use']['name']
        }
        thought_queue.put(json.dumps(tool_data))
        
    #return None
