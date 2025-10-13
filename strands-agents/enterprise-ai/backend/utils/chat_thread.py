"""
Chat thread management utilities for AIUI application.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, TypedDict, NotRequired
from utils.utility import Utility


DEFAULT_USER = 'Deepesh'

class MessageSchema(TypedDict):
    response: str
    show_graph: NotRequired[bool]  # Default will be False
    messages: list
    query_results: list
    status: NotRequired[str]  # Status field for API responses
    
    @staticmethod
    def create(response="", messages=[], query_results=[], show_graph=False, status="success"):
        """Factory method to create a MessageSchema with default values."""
        return MessageSchema(
            response=response,
            messages=messages,
            query_results=query_results,
            show_graph=show_graph,
            status=status
        )

class Usage(TypedDict):
    input: int
    output: int
    total_tokens: int
    latency: int

class ChatItem(TypedDict):
    human: str
    ai: str
    query_results: list
    show_graph: bool
    graph_code: str
    usage: Usage

class ChatThread(TypedDict):
    """
    TypedDict to manage chat threads for display and model context.
    Handles serialization and deserialization of chat history.
    """
    thread_id: str
    user_id: str
    thread_title: str
    ui_msgs: List[ChatItem]
    agent_msgs: list
    date: datetime
    
    @staticmethod
    def create_new(human_msg: str, user_id: str = DEFAULT_USER) -> 'ChatThread':
        """
        Create a new chat thread with an initial human message.
        
        Args:
            human_msg: Initial human message
            user_id: ID of the user creating the thread (defaults to DEFAULT_USER)
            
        Returns:
            New ChatThread instance
        """
        thread_id = str(uuid.uuid4())
        

        msg_list = [{
            "role":"user",
            "content": human_msg
        }]
        
        return ChatThread(
            thread_id=thread_id,
            thread_title=human_msg,
            user_id=user_id,
            ui_msgs=[],
            agent_msgs=[],
            date=datetime.utcnow()
        )
    
    @staticmethod
    def create_from_string(thread_data: Dict[str, Any]) -> 'ChatThread':
        """
        Create a chat thread from database record.
        
        Args:
            thread_data: Dictionary containing thread data from database
            
        Returns:
            ChatThread instance
        """
        try:
            thread_id = thread_data.get('thread_id')
            user_id = thread_data.get('user_id')
            thread_title = thread_data.get('thread_title')
            
            # Parse JSON strings if needed
            if isinstance(thread_data.get('ui_msgs'), str):
                ui_msgs = json.loads(thread_data.get('ui_msgs'))
            else:
                ui_msgs = thread_data.get('ui_msgs')
                
            if isinstance(thread_data.get('agent_msgs'), str):
                agent_msgs = json.loads(thread_data.get('agent_msgs'))
            else:
                agent_msgs = thread_data.get('agent_msgs')
            
            # Parse date if it's a string
            date_str = thread_data.get('date')
            if isinstance(date_str, str):
                try:
                    date = datetime.fromisoformat(date_str)
                except ValueError:
                    date = datetime.utcnow()
            else:
                date = thread_data.get('date', datetime.utcnow())
            
            return ChatThread(
                thread_id=thread_id,
                user_id=user_id,
                thread_title = thread_title,
                ui_msgs=ui_msgs,
                agent_msgs=agent_msgs,
                date=date
            )
        except Exception as e:
            Utility().log_error(f"Error creating chat thread from string: {str(e)}")
            raise ValueError(f"Invalid thread data format: {str(e)}")


class ChatThreadHelper:
    def __init__(self, chat_thread: ChatThread):
        self.chat_thread = chat_thread

    def get_chat_thread(self) -> ChatThread:
        return self.chat_thread

    def update_agent_messages(self, messages: list):
        self.chat_thread['agent_msgs'] = messages

    def update_ui_messages(self, 
                           response: str, 
                           query_results: list, 
                           user_input: str, 
                           show_graph: bool):
        
        usage = Usage()
        usage['input'] = 0
        usage['output'] = 0
        usage['total_tokens'] = 0
        usage['latency'] = 0

        chat_item = ChatItem()
        chat_item['human'] = user_input
        chat_item['ai'] = response
        chat_item['query_results'] = query_results

        chat_item['show_graph'] = show_graph
        chat_item['graph_code'] = ''
        chat_item['usage'] = usage

        self.chat_thread['ui_msgs'].append(chat_item)

    def update_thread_title(self, title: str):
        """
        Update the thread title.
        
        Args:
            title: New title for the thread
        """
        self.chat_thread['thread_title'] = title

         
    

# Helper functions to maintain compatibility with class-based implementation
def add_human_message(thread: ChatThread, message: str) -> ChatThread:
    """
    Add a human message to the thread.
    
    Args:
        thread: ChatThread instance
        message: Human message content
        
    Returns:
        Updated ChatThread instance
    """
    # Add message for display
    display_msg = {
        "role": "human",
        "content": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    thread['ui_msgs'].append(display_msg)
    
    # Add message for model
    model_msg = {
        "role": "user",
        "content": message
    }
    thread['agent_msgs'].append(model_msg)
    
    return thread



def to_dict(thread: ChatThread) -> Dict[str, Any]:
    """
    Convert the thread to a dictionary for database storage.
    
    Args:
        thread: ChatThread instance
        
    Returns:
        Dictionary representation of the thread
    """
    return {
        "thread_id": thread['thread_id'],
        "user_id": thread['user_id'],
        "ui_msgs": json.dumps(thread['ui_msgs']),
        "agent_msgs": json.dumps(thread['agent_msgs']),
        "date": datetime.utcnow().isoformat()
    }

def get_model_messages(thread: ChatThread) -> List[Dict[str, str]]:
    """
    Get messages formatted for the AI model.
    
    Args:
        thread: ChatThread instance
        
    Returns:
        List of messages in model format
    """
    return thread['agent_msgs']

def get_display_messages(thread: ChatThread) -> List[Dict[str, Any]]:
    """
    Get messages formatted for UI display.
    
    Args:
        thread: ChatThread instance
        
    Returns:
        List of messages in display format
    """
    return thread['ui_msgs']

# Add method-like functions to ChatThread TypedDict
# ChatThread.add_human_message = lambda self, message: add_human_message(self, message)
# ChatThread.add_ai_message = lambda self, message: add_ai_message(self, message)
# ChatThread.to_dict = lambda self: to_dict(self)
# ChatThread.get_model_messages = lambda self: get_model_messages(self)
# ChatThread.get_display_messages = lambda self: get_display_messages(self)
