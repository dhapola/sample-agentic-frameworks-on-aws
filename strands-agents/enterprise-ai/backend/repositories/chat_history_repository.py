"""
Repository for chat history data.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from utils.utility import Utility
from repositories.base_repository import BaseRepository
from utils.chat_thread import ChatThread
from utils.utility import Utility

class ChatHistoryRepository(BaseRepository):
    """
    Repository for managing chat history data in the database.
    """
    
    def __init__(self):
        """Initialize the repository with the chat_history table."""
        super().__init__("chat_history")
        self.utils = Utility()
    
    def get_thread_by_id(self, thread_id: str, user_id: str) -> Optional[ChatThread]:
        """
        Get a chat thread by its ID and user ID.
        
        Args:
            thread_id: ID of the thread
            user_id: ID of the user
            
        Returns:
            ChatThread instance or None if not found
        """
        query = f"""
        SELECT * FROM {self.table_name}
        WHERE thread_id = :thread_id
        AND user_id = :user_id
        AND deleted = FALSE
        """
        
        params = {
            "thread_id": thread_id,
            "user_id": user_id
        }
        
        results = self.db.execute_query(query, params)
        
        if not results:
            return None
            
        try:
            return ChatThread.create_from_string(results[0])
        except Exception as e:
            self.utils.log_error(f"Error creating chat thread from database: {str(e)}")
            return None
    
    def save_thread(self, thread: ChatThread, is_new: bool) -> bool:
        """
        Save a chat thread to the database.
        
        Args:
            thread: ChatThread instance
            
        Returns:
            True if save was successful
        """

        # Convert Python dictionaries to JSON strings
        ui_msgs_json = json.dumps(thread["ui_msgs"])
        agent_msgs_json = json.dumps(thread["agent_msgs"])

        
        if is_new:
            # Insert new thread using named parameters (without text() wrapper)
            query = f"""
            INSERT INTO {self.table_name} (
                thread_id, user_id, thread_title, ui_msgs, agent_msgs, date, deleted
            ) VALUES (
                :thread_id, :user_id, :thread_title, :ui_msgs, :agent_msgs, CURRENT_TIMESTAMP, FALSE
            )
            """

            params = {
                "thread_id": thread["thread_id"],
                "user_id": thread["user_id"],
                "thread_title": thread["thread_title"],
                "ui_msgs": ui_msgs_json,  # JSON string
                "agent_msgs": agent_msgs_json  # JSON string
            }
            
            try:
                self.db.execute_write(query, params)
                return True
            except Exception as e:
                self.utils.log_error(f"Error inserting chat thread: {str(e)}")
                return False
            
        else:
            # Update existing thread using named parameters (without text() wrapper)
            query = f"""
            UPDATE {self.table_name}
            SET ui_msgs = :ui_msgs,
                agent_msgs = :agent_msgs,
                date = CURRENT_TIMESTAMP,
                thread_title = :thread_title
            WHERE thread_id = :thread_id
            AND user_id = :user_id
            """
            
            params = {
                "thread_id": thread["thread_id"],
                "thread_title": thread["thread_title"],
                "user_id": thread["user_id"],
                "ui_msgs": ui_msgs_json,  # JSON string
                "agent_msgs": agent_msgs_json  # JSON string
            }
            
            try:
                self.db.execute_write(query, params)
                return True
            except Exception as e:
                self.utils.log_error(f"Error updating chat thread: {str(e)}")
                return False
            
    
    def delete_thread(self, thread_id: str, user_id: str) -> bool:
        """
        Mark a chat thread as deleted.
        
        Args:
            thread_id: ID of the thread
            user_id: ID of the user
            
        Returns:
            True if deletion was successful
        """
        query = f"""
        UPDATE {self.table_name}
        SET deleted = TRUE
        WHERE thread_id = :thread_id
        AND user_id = :user_id
        """
        
        params = {
            "thread_id": thread_id,
            "user_id": user_id
        }
        
        try:
            rowcount = self.db.execute_write(query, params)
            return rowcount > 0
        except Exception as e:
            self.utils.log_error(f"Error deleting chat thread: {str(e)}")
            return False
    
    def get_threads_by_user(self, user_id: str, page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
        """
        Get all chat threads for a user with pagination.
        
        Args:
            user_id: ID of the user
            page: Page number (starting from 1)
            page_size: Number of items per page
            
        Returns:
            List of thread objects
        """
        offset = (page - 1) * page_size
        
        query = f"""
        SELECT thread_id, user_id, thread_title, date as created_at, date as updated_at
        FROM {self.table_name}
        WHERE user_id = :user_id
        AND deleted = FALSE
        ORDER BY date DESC
        LIMIT :limit OFFSET :offset
        """
        
        params = {
            "user_id": user_id,
            "limit": page_size,
            "offset": offset
        }
        
        try:
            results = self.db.execute_query(query, params)
            threads = []

            
            for row in results:
                # Parse JSON strings back to Python objects
                
                thread = {
                    'thread_id': row.get('thread_id', ''),
                    'user_id': row.get('user_id', ''),
                    'thread_title': row.get('thread_title', 'Untitled Chat'),
                    'created_at': self.utils.to_serializable_date(row.get('created_at', '')),
                    'updated_at': self.utils.to_serializable_date(row.get('updated_at', ''))
                }
                
                threads.append(thread)
                
            return threads
        except Exception as e:
            self.utils.log_error(f"Error getting threads by user: {str(e)}", exc_info=True)
            return []
