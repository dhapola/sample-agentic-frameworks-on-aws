"""
SQLAlchemy models for the application database.
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatHistory(Base):
    """Model for chat_history table."""
    __tablename__ = 'chat_history'
    
    thread_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    thread_title = Column(Text)
    ui_msgs = Column(JSON, nullable=False)
    agent_msgs = Column(JSON, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    deleted = Column(Boolean, nullable=False, default=False, index=True)

    def __repr__(self):
        return f"<ChatHistory(thread_id='{self.thread_id}', user_id='{self.user_id}', title='{self.thread_title}')>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'thread_id': self.thread_id,
            'user_id': self.user_id,
            'thread_title': self.thread_title,
            'ui_msgs': self.ui_msgs,
            'agent_msgs': self.agent_msgs,
            'date': self.date.isoformat() if self.date else None,
            'deleted': self.deleted
        }


# Add more models here as needed
class User(Base):
    """Model for users table (example)."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', username='{self.username}')>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
