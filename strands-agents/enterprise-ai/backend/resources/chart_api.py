import json
from flask_restful import Resource, request
from strands import Agent
from utils.utility import Utility
from strands.models import BedrockModel
from repositories.chat_history_repository import ChatHistoryRepository
from config import Config



class ChartResource(Resource):
    """
    API resource for generating chart configurations based on query results
    """

    def __init__(self):
        self.util = Utility()
        self.chat_history_repo = ChatHistoryRepository()
        self.config = Config()
        

    def post(self):
        data = request.get_json()
        
        model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        # Extract required fields
        text = data.get('text')
        query_results = data.get('queryResults')
        user_id = data.get('user_id', 'Deepesh')  # Default to 'Deepesh' if not provided
        thread_id = data.get('thread_id')
        thread = self.chat_history_repo.get_thread_by_id(thread_id, user_id)
        
        prompt = f"""
            You are a data visualization expert. Based on the following data and analysis, suggest the most appropriate chart type and configuration.
            
            User Query: {text}
            
            Data Results:
            {query_results}
            
            Please provide a JSON response with the following structure:
            {{
                "chart_type": "line|bar|pie|scatter|area|etc",
                "caption": "Brief description of what the chart shows",
                "rationale": "Brief explanation of why this chart type is appropriate",
                "chart_configuration": {{
                "options": {{
                    // ApexCharts options
                }},
                "series": [
                    // ApexCharts series data
                ]
                }}
            }}
            
            Focus on creating a visualization that best represents the data and answers the user's query.
            do not generate formatter functions as these are not parsable by JavaScript
        """

        model = BedrockModel(model_id=model_id, 
                    # verbose=True, 
                    temperature=0.3, 
                    region_name=self.config.aws_region)

        # Strands Agents SDK allows easy integration of agent tools
        agent = Agent(model=model, tools=[])

        response = agent(prompt)

        response = str(response)
        json_response = self.util.clean_json_string(response)

        try:
            ui_msgs = thread['ui_msgs']
            for msg in ui_msgs:
                if msg['human'] == text:
                    msg['graph_code'] = json_response
                    break
            
            
            self.chat_history_repo.save_thread(thread, False)
        except Exception as e:
            self.util.log_error(f"Error updating thread {thread_id} with chart data: {str(e)}")

        self.util.log_data(f'\nFinal Response: {json_response}')
        #chart_dict = json.loads(json_response)

        json_response =  {
            "chart": json_response,
            "status": "success"
        }

        return json_response


                       
