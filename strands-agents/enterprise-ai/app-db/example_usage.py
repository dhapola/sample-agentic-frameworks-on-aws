"""
Example usage of the SQLAlchemy-based database system.
"""
import json
from datetime import datetime
from database_config import init_database, db_connection
from models import Base
from repositories import ChatHistoryRepository, UserRepository


def main():
    """Example usage of the database system."""
    print("=== SQLAlchemy Database Example ===\n")
    
    # Initialize database
    if not init_database():
        print("Failed to initialize database.")
        return
    
    # Create tables
    engine = db_connection.get_engine()
    if engine:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.\n")
    else:
        print("Failed to get database engine.")
        return
    
    # Initialize repositories
    chat_repo = ChatHistoryRepository()
    user_repo = UserRepository()
    
    try:
        # Example 1: Create a user
        print("1. Creating a user...")
        user = user_repo.create(
            user_id="user_001",
            username="john_doe",
            email="john.doe@example.com"
        )
        if user:
            print(f"   Created user: {user.username} ({user.email})")
        
        # Example 2: Create chat history
        print("\n2. Creating chat history...")
        chat_history = chat_repo.create(
            thread_id="thread_001",
            user_id="user_001",
            thread_title="Getting Started with AI",
            ui_msgs={
                "messages": [
                    {"role": "user", "content": "Hello, how can I get started with AI?"},
                    {"role": "user", "content": "What are the basic concepts I should know?"}
                ]
            },
            agent_msgs={
                "responses": [
                    {"role": "assistant", "content": "Hello! I'd be happy to help you get started with AI."},
                    {"role": "assistant", "content": "The basic concepts include machine learning, neural networks, and data preprocessing."}
                ]
            }
        )
        if chat_history:
            print(f"   Created chat history: {chat_history.thread_title}")
        
        # Example 3: Retrieve chat history
        print("\n3. Retrieving chat history...")
        retrieved_chat = chat_repo.get_by_thread_id("thread_001")
        if retrieved_chat:
            print(f"   Retrieved: {retrieved_chat.thread_title}")
            print(f"   User ID: {retrieved_chat.user_id}")
            print(f"   Date: {retrieved_chat.date}")
            print(f"   UI Messages: {len(retrieved_chat.ui_msgs.get('messages', []))} messages")
            print(f"   Agent Messages: {len(retrieved_chat.agent_msgs.get('responses', []))} responses")
        
        # Example 4: Get user's chat histories
        print("\n4. Getting user's chat histories...")
        user_chats = chat_repo.get_by_user_id("user_001")
        print(f"   Found {len(user_chats)} chat histories for user_001")
        for chat in user_chats:
            print(f"   - {chat.thread_title} ({chat.date.strftime('%Y-%m-%d %H:%M:%S')})")
        
        # Example 5: Update chat history
        print("\n5. Updating chat history...")
        updated_chat = chat_repo.update(
            "thread_001",
            thread_title="Getting Started with AI - Updated",
            ui_msgs={
                "messages": [
                    {"role": "user", "content": "Hello, how can I get started with AI?"},
                    {"role": "user", "content": "What are the basic concepts I should know?"},
                    {"role": "user", "content": "Can you recommend some resources?"}
                ]
            }
        )
        if updated_chat:
            print(f"   Updated chat title: {updated_chat.thread_title}")
        
        # Example 6: Search chat histories
        print("\n6. Searching chat histories...")
        search_results = chat_repo.search(
            user_id="user_001",
            thread_title_contains="AI",
            limit=10
        )
        print(f"   Found {len(search_results)} chat histories containing 'AI'")
        
        # Example 7: Create another chat history
        print("\n7. Creating another chat history...")
        chat_repo.create(
            thread_id="thread_002",
            user_id="user_001",
            thread_title="Python Programming Help",
            ui_msgs={"messages": [{"role": "user", "content": "How do I use SQLAlchemy?"}]},
            agent_msgs={"responses": [{"role": "assistant", "content": "SQLAlchemy is a powerful ORM for Python..."}]}
        )
        
        # Example 8: Get all chat histories for user
        print("\n8. Getting all user chat histories...")
        all_user_chats = chat_repo.get_by_user_id("user_001")
        print(f"   User now has {len(all_user_chats)} total chat histories:")
        for i, chat in enumerate(all_user_chats, 1):
            print(f"   {i}. {chat.thread_title}")
        
        # Example 9: Soft delete a chat history
        print("\n9. Soft deleting a chat history...")
        if chat_repo.delete("thread_002", soft_delete=True):
            print("   Chat history soft deleted successfully")
        
        # Example 10: Verify soft delete
        print("\n10. Verifying soft delete...")
        active_chats = chat_repo.get_by_user_id("user_001", include_deleted=False)
        all_chats = chat_repo.get_by_user_id("user_001", include_deleted=True)
        print(f"   Active chat histories: {len(active_chats)}")
        print(f"   Total chat histories (including deleted): {len(all_chats)}")
        
        # Example 11: Get user information
        print("\n11. Getting user information...")
        user_info = user_repo.get_by_user_id("user_001")
        if user_info:
            print(f"   User: {user_info.username}")
            print(f"   Email: {user_info.email}")
            print(f"   Created: {user_info.created_at}")
            print(f"   Active: {user_info.is_active}")
        
        print("\n=== Example completed successfully! ===")
        
    except Exception as e:
        print(f"Error during example execution: {e}")
    
    finally:
        # Clean up
        db_connection.close()


if __name__ == "__main__":
    main()
