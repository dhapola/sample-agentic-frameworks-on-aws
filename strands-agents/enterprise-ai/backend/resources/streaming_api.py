from flask_restful import Resource
from botocore.exceptions import ClientError, NoCredentialsError
from providers.bedrock_provider import get_bedrock_client
from utils.utility import Utility
from flask import Response, stream_with_context, request
import queue
import threading
import json
from strands.models import BedrockModel
from strands import Agent, tool
from strands.agent import AgentResult
from agents.fintech_sales_postgresql import FintechSalesAgent
from agents.personal_tasks import PersonalTasksAgent
from agents.waf_logs import WAFLogsAgent
from agents.mcp_servers import MCPServersAgent
from flask import session
import time
from utils.chat_thread import ChatThread, ChatThreadHelper
from repositories.chat_history_repository import ChatHistoryRepository
import re
from agents.aws_resource_assistant import AWSResourcesAgent
from config import Config

class StreamAnswerResource(Resource):

    def __init__(self):
        self.thought_queue = queue.Queue()
        self.util = Utility()
        self.start_time = None
        self.fintech_sales_agent = FintechSalesAgent(self.thought_queue)
        self.personal_tasks_manager = PersonalTasksAgent(self.thought_queue)
        self.mcp_servers_agent = MCPServersAgent(self.thought_queue)
        self.waf_logs_agent = WAFLogsAgent(self.thought_queue)
        self.aws_resource_assistant = AWSResourcesAgent(self.thought_queue)
        self.chat_history_repo = ChatHistoryRepository()
        self.config = Config()
        

    def _answer_stream_response(self, **kwargs):
        self.start_time = time.time()

        # Handle preflight OPTIONS request for CORS
        if request.method == 'OPTIONS':
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
            
        # Get data from either POST body or GET query parameters
        if request.method == 'POST':
            data = request.json
        else:  # GET
            data = request.args
            
        # Use the new payload structure (human, thread_id, user)
        user_input = data.get('human', '')  # Changed from 'query' to 'human'
        thread_id = data.get('thread_id', '')
        user = data.get('user', 'Deepesh')
        model_id = data.get('model_id', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Log the received data
        
        self.util.log_data(f"Received request: human={user_input}, thread_id={thread_id}, user={user}, model_id={model_id}")
        
        # Start the processing thread
        threading.Thread(target=self.process_agent_response, args=(user_input, model_id, thread_id, user)).start()
        
        response = Response(stream_with_context(self.generate()), 
                      mimetype='text/event-stream',
                      headers={
                          'Cache-Control': 'no-cache',
                          'Connection': 'keep-alive',
                          'X-Accel-Buffering': 'no',
                          'Access-Control-Allow-Origin': '*',
                          'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                          'Access-Control-Allow-Headers': 'Content-Type'
                      })
        
        return response
    
    def generate(self):
        # First, yield a heartbeat to establish the connection
        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        
        # Process thoughts from the queue
        while True:
            try:
                thought = self.thought_queue.get(timeout=1.0)
                
                if thought == "DONE":
                    break

                yield f"data: {thought}\n\n"
            except queue.Empty:
                # Send a heartbeat to keep the connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                continue

    def get(self, **kwargs):
        """
        Handle GET requests (legacy support)
        """
        return self._answer_stream_response(**kwargs)

    def post(self, **kwargs):
        """
        Handle POST requests with the new payload structure
        """
        return self._answer_stream_response(**kwargs)

    def options(self, **kwargs):
        """
        Handle OPTIONS requests for CORS
        """
        return self._answer_stream_response(**kwargs)


    # Override the callback handler in sales_analytics_assistant to forward thoughts to our queue
    def global_callback_handler(self, **kwargs):

        if "data" in kwargs:
            # Stream the model's thinking process
            thought_data = {
                "type": "thinking",
                "content": kwargs['data']
            }
            self.thought_queue.put(json.dumps(thought_data))
            
        elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
            # Stream tool usage information
            tool_data = {
                "type": "tool_use",
                "tool": kwargs['current_tool_use']['name']
            }
            self.thought_queue.put(json.dumps(tool_data))
            
        #return None
        
    # Start a thread to process the agent's response
    def process_agent_response(self, user_input, model_id, thread_id, user="Deepesh"):
        #try:
        # Handle thread management
        chat_thread = None
        
        # Define the orchestrator system prompt
        MAIN_SYSTEM_PROMPT = f"""
        You are an assistant that routes queries to specialized agents:
            - For WAF questions ->  Use the waf_logs_assistant tool
            - For my personal task management ->  Use the personal_assistant tool
            - For Payment and Sales analytics ->  Use the sales_analytics_assistant tool
            - For aws resources like ec2, rds, lambda and others ->  Use the aws_resource_assistant tool
            - For specialized tasks -> Use mcp_servers_assistant tool
            - For simple questions, creative tasks, general knowledge that do not require specialized knowledge ->  Answer directly

        Rules:
        - Always select the most appropriate tool based on the user's query
        - In your final response, DO NOT include commentry           
            
        """
        chat_thread = self.chat_history_repo.get_thread_by_id(thread_id, user)
        print(chat_thread)
        
        if (len(chat_thread['ui_msgs']) < 1):
            chat_thread['thread_title'] = user_input
        
        
        chat_thread_helper = ChatThreadHelper(chat_thread)
        model = BedrockModel(model_id=model_id, 
                                # verbose=True, 
                                temperature=0.3,
                                region_name = self.config.aws_region)
        
        # Set up the orchestrator with the enhanced callback
        orchestrator = Agent(
            system_prompt=MAIN_SYSTEM_PROMPT,
            model=model,
            
            tools=[
                self.fintech_sales_agent.sales_analytics_assistant_tool(),
                    self.personal_tasks_manager.personal_task_manager_tool(),
                    self.aws_resource_assistant.aws_resources_tool(),
                    self.mcp_servers_agent.mcp_servers_tool(),
                    self.waf_logs_agent.was_tool()],

            callback_handler=self.global_callback_handler,
            messages = chat_thread['agent_msgs']
        )
        
        # Process the user input
        response = orchestrator(user_input)
        
        # Get the final response and any query results
        last_message = orchestrator.messages[-2]['content']
        
        final_response = ""
        query_results = []
        show_graph = False
        
        try:        
            if (type(response) == AgentResult):
                messages = orchestrator.messages
                final_response = messages[-1]['content'][0]['text'] # final response
                last_message = messages[-2]['content'] # last message from the agent
                for item in last_message:
                    if 'toolResult' in item:
                        tool_result  = item['toolResult']['content'][0]['text']
                        
                        self.util.log_data(f"""📊 Tool Result --> {tool_result}
                                    """)

                        response_json   = json.loads(tool_result)
                        query_results   = response_json['query_results']
                        show_graph      = response_json['show_graph']

                
                self.util.log_data(f"""📊 Metrics -->
                                    Tool Meetrics: {response.metrics.tool_metrics}
                                    cycle_durations: {response.metrics.cycle_durations}
                                    Traces: {response.metrics.traces}
                                    Accumulated usage: {response.metrics.accumulated_usage}
                                    Accumulated metrics: {response.metrics.accumulated_metrics}
                                    """)
                
            self.util.log_data(f"✅ Final Response: {final_response}")
            
        except json.JSONDecodeError as ex:
            # If not valid JSON or not a dict, use the response as is
            self.util.log_error(f'Error in process_agent_response. Details: {str(ex)}')
            pass
        except TypeError as ex:
             # If not valid JSON or not a dict, use the response as is
            self.util.log_error(f'Error in process_agent_response. Details: {str(ex)}')
            pass
        
        
    
        # Save the updated thread to the database
        # try:
        # attach tool messages from the agent
        chat_thread_helper.update_agent_messages(orchestrator.messages)
        
        chat_thread_helper.update_ui_messages(response=final_response,
                                                user_input=user_input,
                                                query_results=query_results,
                                                show_graph=show_graph)
        

        self.chat_history_repo.save_thread(chat_thread_helper.get_chat_thread(), is_new=False)
        

        self.util.log_data(f"Saved chat thread {chat_thread['thread_id']} to database")
        # except Exception as e:
        #     self.util.log_error(f"Failed to save chat thread to database: {str(e)}")
        
        chat_thread = chat_thread_helper.get_chat_thread()
        final_data = {
            "thread_id": chat_thread['thread_id'],
            "type": "final",
            "ui_msgs": chat_thread['ui_msgs'],
            "status": "success"
        }
        
        #This may not be required
        self.thought_queue.put(json.dumps(final_data))
         # Signal that we're done
        #self.util.log_data('DONE')
        self.thought_queue.put("DONE")
        

        # Calculate and log execution time
        end_time = time.time()
        execution_time = end_time - self.start_time
        self.util.log_data(f"Total execution time: {execution_time:.2f} seconds")
            
        # except Exception as e:
        #     # Handle any exceptions
        #     error_data = {
        #         'type': 'error',
        #         'content': f"Error processing request: {str(e)}"
        #     }
        #     self.thought_queue.put(json.dumps(error_data))
        #     self.thought_queue.put("DONE")
        #     self.util.log_error(f"Error in process_agent_response: {str(e)}", exc_info=True)
        #     raise e

    