from flask_restful import Resource
from flask import request, jsonify
from repositories.chat_history_repository import ChatHistoryRepository
from utils.chat_thread import ChatThreadHelper, ChatThread
import time
from utils.utility import Utility


class ChatThreadListResource(Resource):
    """Resource for listing all chat threads for a user"""
    
    def __init__(self):
        self.chat_history_repo = ChatHistoryRepository()
        self.util = Utility()
    
    def get(self):
        """Get all threads for a user"""
        try:
            
            # Get user from request parameters
            user = request.args.get('user', 'Deepesh')
            
            # Optional pagination parameters
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))
            
            # Get threads from repository
            threads = self.chat_history_repo.get_threads_by_user(user, page, page_size)
            
            # Format the response
            thread_list = []
            for thread in threads:
                thread_list.append({
                    'thread_id': thread.get('thread_id', ''),
                    'thread_title': thread.get('thread_title', 'Untitled Chat'),
                    'user_id': thread.get('user_id', ''),
                    'created_at': thread.get('created_at', ''),
                    'updated_at': thread.get('updated_at', ''),
                    'message_count': len(thread.get('ui_msgs', [])) if thread.get('ui_msgs') else 0
                })
            
            return {
                'status': 'success',
                'threads': thread_list,
                'page': page,
                'page_size': page_size,
                'total': len(thread_list)  # In a real implementation, this would be the total count from DB
            }
            
        except Exception as e:
            self.util.log_error(f"Error getting threads: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}, 500

    
    

class ChatThreadResource(Resource):
    """Resource for managing a specific chat thread"""
    
    def __init__(self):
        self.chat_history_repo = ChatHistoryRepository()

    def get(self, thread_id):
        """Get a specific thread by ID"""
        try:
            # Get user from request parameters
            user = request.args.get('user', 'Deepesh')
            
            # Get thread from repository
            thread = self.chat_history_repo.get_thread_by_id(thread_id, user)
            
            if not thread:
                return {'status': 'error', 'message': 'Thread not found'}, 404
            
            # Format the response to match the expected structure
            response = {
                'thread_id': thread.get('thread_id', ''),
                'thread_title': thread.get('thread_title', ''),
                'type': 'final',
                'ui_msgs': thread.get('ui_msgs', []),
                'status': 'success'
            }
            
            return response
            
        except Exception as e:
            self.util.log_error(f"Error getting thread {thread_id}: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}, 500
    
    def delete(self, thread_id):
        """Delete a specific thread by ID"""
        try:
            # Get user from request parameters
            user = request.args.get('user', 'Deepesh')
            
            # Delete thread from repository
            success = self.chat_history_repo.delete_thread(thread_id, user)
            
            if not success:
                return {'status': 'error', 'message': 'Thread not found or could not be deleted'}, 404
            
            return {'status': 'success', 'message': f'Thread {thread_id} deleted successfully'}
            
        except Exception as e:
            self.util.log_error(f"Error deleting thread {thread_id}: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}, 500


    def post(self):
        """Create a new thread"""
        try:
            # Get user from request parameters
            user = request.args.get('user', 'Deepesh')
            chat_thread = ChatThread.create_new(human_msg='New Chat 1', user_id=user)

            # Get thread from repository
            self.chat_history_repo.save_thread(chat_thread, is_new=True)
            
            # Format the response to match the expected structure
            response = {
                'thread_id': chat_thread['thread_id'],
                'thread_title': chat_thread['thread_title'],
                'type': 'final',
                'ui_msgs': [],
                'status': 'success'
            }
            
            return response
            
        except Exception as e:
            self.util.log_error(f"Error saving thread {chat_thread['thread_id']}: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}, 500
    
    