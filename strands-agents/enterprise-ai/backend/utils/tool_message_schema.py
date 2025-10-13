from typing import TypedDict, List, NotRequired
import uuid, json, datetime

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


# ChatThread has been moved to utils/chat_thread.py
