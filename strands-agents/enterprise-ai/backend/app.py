from flask import Flask, jsonify
from flask_restful import Api
from flask_cors import CORS
import os
from sqlalchemy import text

# Import API resources
from resources.models_api import ModelsResource
from resources.wizard_api import ApiInsightsResource
from resources.chart_api import ChartResource
from resources.streaming_api import StreamAnswerResource
from resources.chat_thread_api import ChatThreadListResource, ChatThreadResource

from providers.mcp_provider import MCPProvider
from utils.db_init import init_database
from utils.database import DatabaseManager
from config import get_config
from utils.utility import Utility


def create_app(config_object=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    util = Utility()
    
    # Load configuration
    if config_object is None:
        config_object = get_config()
    app.config.from_object(config_object)
    
    # Enable CORS
    CORS(app, origins='*', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # Initialize API
    api = Api(app)
    
    # Register API resources
    api.add_resource(ModelsResource, '/api/models')
    api.add_resource(ApiInsightsResource, '/api/insights')
    api.add_resource(ChartResource, '/api/chart')
    api.add_resource(StreamAnswerResource, '/api/answer')
    
    # Register thread management APIs
    api.add_resource(ChatThreadListResource, '/api/threads')
    api.add_resource(ChatThreadResource, '/api/thread/<string:thread_id>', '/api/thread')
    

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy"})
    
    # Database status endpoint
    @app.route('/db/status', methods=['GET'])
    def db_status():
        db = DatabaseManager()
        return jsonify(db.test_connection())
    
    # Initialize database
    try:
        util.log_data("Initializing database connection...")
        init_database()
        util.log_data("Database initialization completed successfully")
    except Exception as e:
        util.log_error(f"Database initialization failed: {str(e)}")
        
    
    # Initialize MCP servers
    mcp_provider = MCPProvider()
    mcp_provider.load_mcp_servers()
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    port = app.config.get('PORT', 8080)
    debug = app.config.get('DEBUG', Flask)
    Utility().log_data(f"Starting server on port {port} with debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=True)
