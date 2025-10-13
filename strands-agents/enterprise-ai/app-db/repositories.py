"""
Repository classes for database operations.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc

from models import ChatHistory, User
from database_config import get_db_session


class BaseRepository:
    """Base repository class with common operations."""
    
    def __init__(self):
        pass
    
    def get_session(self) -> Optional[Session]:
        """Get database session."""
        return get_db_session()


class ChatHistoryRepository(BaseRepository):
    """Repository for chat_history operations."""
    
    def create(self, thread_id: str, user_id: str, thread_title: str,
               ui_msgs: Dict[str, Any], agent_msgs: Dict[str, Any]) -> Optional[ChatHistory]:
        """Create a new chat history record."""
        session = self.get_session()
        if not session:
            return None
        
        try:
            chat_history = ChatHistory(
                thread_id=thread_id,
                user_id=user_id,
                thread_title=thread_title,
                ui_msgs=ui_msgs,
                agent_msgs=agent_msgs
            )
            
            session.add(chat_history)
            session.commit()
            session.refresh(chat_history)
            print(f"Chat history created for thread_id: {thread_id}")
            return chat_history
            
        except SQLAlchemyError as e:
            print(f"Error creating chat history: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_by_thread_id(self, thread_id: str, include_deleted: bool = False) -> Optional[ChatHistory]:
        """Get chat history by thread_id."""
        session = self.get_session()
        if not session:
            return None
        
        try:
            query = session.query(ChatHistory).filter(ChatHistory.thread_id == thread_id)
            
            if not include_deleted:
                query = query.filter(ChatHistory.deleted == False)
            
            chat_history = query.first()
            return chat_history
            
        except SQLAlchemyError as e:
            print(f"Error getting chat history: {e}")
            return None
        finally:
            session.close()
    
    def get_by_user_id(self, user_id: str, include_deleted: bool = False, 
                       limit: Optional[int] = None) -> List[ChatHistory]:
        """Get all chat histories for a user."""
        session = self.get_session()
        if not session:
            return []
        
        try:
            query = session.query(ChatHistory).filter(ChatHistory.user_id == user_id)
            
            if not include_deleted:
                query = query.filter(ChatHistory.deleted == False)
            
            query = query.order_by(desc(ChatHistory.date))
            
            if limit:
                query = query.limit(limit)
            
            chat_histories = query.all()
            return chat_histories
            
        except SQLAlchemyError as e:
            print(f"Error getting user chat histories: {e}")
            return []
        finally:
            session.close()
    
    def update(self, thread_id: str, **kwargs) -> Optional[ChatHistory]:
        """Update chat history record."""
        session = self.get_session()
        if not session:
            return None
        
        try:
            chat_history = session.query(ChatHistory).filter(
                ChatHistory.thread_id == thread_id
            ).first()
            
            if not chat_history:
                print(f"Chat history not found for thread_id: {thread_id}")
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(chat_history, key):
                    setattr(chat_history, key, value)
            
            session.commit()
            session.refresh(chat_history)
            print(f"Chat history updated for thread_id: {thread_id}")
            return chat_history
            
        except SQLAlchemyError as e:
            print(f"Error updating chat history: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def delete(self, thread_id: str, soft_delete: bool = True) -> bool:
        """Delete chat history (soft delete by default)."""
        session = self.get_session()
        if not session:
            return False
        
        try:
            if soft_delete:
                # Soft delete - mark as deleted
                chat_history = session.query(ChatHistory).filter(
                    ChatHistory.thread_id == thread_id
                ).first()
                
                if chat_history:
                    chat_history.deleted = True
                    session.commit()
                    print(f"Chat history soft deleted for thread_id: {thread_id}")
                    return True
                else:
                    print(f"Chat history not found for thread_id: {thread_id}")
                    return False
            else:
                # Hard delete - remove from database
                deleted_count = session.query(ChatHistory).filter(
                    ChatHistory.thread_id == thread_id
                ).delete()
                
                session.commit()
                if deleted_count > 0:
                    print(f"Chat history hard deleted for thread_id: {thread_id}")
                    return True
                else:
                    print(f"Chat history not found for thread_id: {thread_id}")
                    return False
                    
        except SQLAlchemyError as e:
            print(f"Error deleting chat history: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def search(self, user_id: Optional[str] = None, thread_title_contains: Optional[str] = None,
               date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
               include_deleted: bool = False, limit: Optional[int] = None) -> List[ChatHistory]:
        """Search chat histories with various filters."""
        session = self.get_session()
        if not session:
            return []
        
        try:
            query = session.query(ChatHistory)
            
            # Apply filters
            if user_id:
                query = query.filter(ChatHistory.user_id == user_id)
            
            if thread_title_contains:
                query = query.filter(ChatHistory.thread_title.ilike(f"%{thread_title_contains}%"))
            
            if date_from:
                query = query.filter(ChatHistory.date >= date_from)
            
            if date_to:
                query = query.filter(ChatHistory.date <= date_to)
            
            if not include_deleted:
                query = query.filter(ChatHistory.deleted == False)
            
            query = query.order_by(desc(ChatHistory.date))
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            return results
            
        except SQLAlchemyError as e:
            print(f"Error searching chat histories: {e}")
            return []
        finally:
            session.close()
    
    def get_all(self, include_deleted: bool = False, limit: Optional[int] = None) -> List[ChatHistory]:
        """Get all chat histories."""
        session = self.get_session()
        if not session:
            return []
        
        try:
            query = session.query(ChatHistory)
            
            if not include_deleted:
                query = query.filter(ChatHistory.deleted == False)
            
            query = query.order_by(desc(ChatHistory.date))
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            return results
            
        except SQLAlchemyError as e:
            print(f"Error getting all chat histories: {e}")
            return []
        finally:
            session.close()


class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    def create(self, user_id: str, username: str, email: str) -> Optional[User]:
        """Create a new user."""
        session = self.get_session()
        if not session:
            return None
        
        try:
            user = User(
                user_id=user_id,
                username=username,
                email=email
            )
            
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"User created: {username}")
            return user
            
        except SQLAlchemyError as e:
            print(f"Error creating user: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_by_user_id(self, user_id: str) -> Optional[User]:
        """Get user by user_id."""
        session = self.get_session()
        if not session:
            return None
        
        try:
            user = session.query(User).filter(
                User.user_id == user_id,
                User.is_active == True
            ).first()
            return user
            
        except SQLAlchemyError as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            session.close()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        session = self.get_session()
        if not session:
            return None
        
        try:
            user = session.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            return user
            
        except SQLAlchemyError as e:
            print(f"Error getting user by username: {e}")
            return None
        finally:
            session.close()
    
    def update(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user record."""
        session = self.get_session()
        if not session:
            return None
        
        try:
            user = session.query(User).filter(User.user_id == user_id).first()
            
            if not user:
                print(f"User not found for user_id: {user_id}")
                return None
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            print(f"User updated for user_id: {user_id}")
            return user
            
        except SQLAlchemyError as e:
            print(f"Error updating user: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def deactivate(self, user_id: str) -> bool:
        """Deactivate user (soft delete)."""
        session = self.get_session()
        if not session:
            return False
        
        try:
            user = session.query(User).filter(User.user_id == user_id).first()
            
            if user:
                user.is_active = False
                user.updated_at = datetime.utcnow()
                session.commit()
                print(f"User deactivated for user_id: {user_id}")
                return True
            else:
                print(f"User not found for user_id: {user_id}")
                return False
                
        except SQLAlchemyError as e:
            print(f"Error deactivating user: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_all_active(self, limit: Optional[int] = None) -> List[User]:
        """Get all active users."""
        session = self.get_session()
        if not session:
            return []
        
        try:
            query = session.query(User).filter(User.is_active == True)
            query = query.order_by(asc(User.username))
            
            if limit:
                query = query.limit(limit)
            
            users = query.all()
            return users
            
        except SQLAlchemyError as e:
            print(f"Error getting all active users: {e}")
            return []
        finally:
            session.close()
