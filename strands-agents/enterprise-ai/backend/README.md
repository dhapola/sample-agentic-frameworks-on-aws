# Enterprise AI Backend

A Flask-based backend service that powers an enterprise AI assistant application with specialized agents for fintech analytics, personal task management, and AWS resource analysis. Built with Amazon Bedrock integration and Model Context Protocol (MCP) for extensible tool connectivity.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│                     Port: 8081                                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/REST API
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Flask Backend                                │
│                     Port: 8080                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   API       │  │   Agents    │  │ Providers   │             │
│  │ Resources   │  │             │  │             │             │
│  │             │  │ • Fintech   │  │ • Bedrock   │             │
│  │ • Models    │  │ • Personal  │  │ • MCP       │             │
│  │ • Charts    │  │ • WAF Logs  │  │             │             │
│  │ • Streaming │  │ • AWS Res.  │  │             │             │
│  │ • Threads   │  │             │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Repositories│  │   Utils     │  │   Config    │             │
│  │             │  │             │  │             │             │
│  │ • Base      │  │ • Database  │  │ • Env       │             │
│  │ • Chat      │  │ • Logging   │  │ • Settings  │             │
│  │ • History   │  │ • Tools     │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   AWS       │ │ PostgreSQL  │ │ MCP Servers │
│  Bedrock    │ │  Database   │ │             │
│             │ │             │ │ • Postgres  │
│ • Claude    │ │ • Sales     │ │ • AWS API   │
│ • Nova      │ │ • Chat      │ │ • Quip      │
│ • Haiku     │ │ • Users     │ │ • CloudWatch│
└─────────────┘ └─────────────┘ └─────────────┘
```

## 🚀 Tech Stack

### Core Framework
- **Flask 2.3.3+** - Web framework
- **Flask-RESTful 0.3.10+** - REST API extensions
- **Flask-CORS 4.0.0+** - Cross-origin resource sharing

### AI & Machine Learning
- **Strands Agents** - AI agent framework
- **Strands Agents Tools** - Agent tooling extensions
- **LangChain MCP Adapters** - Model Context Protocol integration
- **Amazon Bedrock** - Cloud AI service
  - Claude 3 Haiku
  - Claude 3.5 Sonnet
  - Nova Lite models

### Database & ORM
- **PostgreSQL 12+** - Primary database
- **SQLAlchemy 2.0+** - ORM and database toolkit
- **psycopg2-binary 2.9.9+** - PostgreSQL adapter

### Cloud & Integration
- **Boto3 1.34.0+** - AWS SDK
- **Model Context Protocol (MCP) 1.0.0+** - Tool integration framework

### Configuration & Environment
- **python-dotenv 1.0.0** - Environment variable management

## 📁 Project Structure

```
backend/
├── agents/                    # AI Agent Implementations
│   ├── fintech_sales_postgresql.py    # Sales analytics agent
│   ├── personal_tasks.py              # Task management agent
│   ├── waf_logs.py                   # Security log analysis
│   ├── aws_resource_assistant.py     # AWS resource management
│   ├── mcp_servers.py                # MCP server management
│   └── agent_callback_handler.py     # Agent event handling
│
├── providers/                 # Service Providers
│   ├── bedrock_provider.py           # AWS Bedrock integration
│   └── mcp_provider.py               # MCP server management
│
├── resources/                 # REST API Endpoints
│   ├── streaming_api.py              # Real-time streaming responses
│   ├── models_api.py                 # AI model management
│   ├── chart_api.py                  # Data visualization
│   ├── wizard_api.py                 # Guided workflows
│   └── chat_thread_api.py            # Chat session management
│
├── repositories/              # Data Access Layer
│   ├── base_repository.py            # Base repository pattern
│   └── chat_history_repository.py    # Chat persistence
│
├── utils/                     # Utilities & Helpers
│   ├── database.py                   # Database connection management
│   ├── db_init.py                    # Database initialization
│   ├── utility.py                    # Common utilities
│   ├── chat_thread.py                # Chat thread management
│   └── tool_message_schema.py        # Message formatting
│
├── config/                    # Configuration
│   └── database_config.py            # Database configuration
│
├── app.py                     # Main Flask application
├── config.py                  # Application configuration
├── mcp.json                   # MCP server configuration
└── requirements.txt           # Python dependencies
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Flask Configuration
DEBUG=True
PORT=8080
FLASK_ENV=development

# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=paymentsdb
DB_USERNAME=paymentsappuser
DB_PASSWORD=your_password

# Database Pool Configuration
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=0
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
DB_QUERY_LOG_LEVEL=INFO
```

### MCP Server Configuration

The `mcp.json` file configures Model Context Protocol servers:

```json
{
  "mcpServers": {
    "postgres-mcp-server": {
      "command": "postgres-mcp",
      "args": ["--access-mode=restricted"],
      "env": {
        "DATABASE_URI": "postgresql://user:pass@localhost:5432/db"
      }
    },
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-api-mcp-server@latest"],
      "env": {
        "AWS_REGION": "ap-south-1"
      }
    }
  }
}
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- AWS Account with Bedrock access
- UV package manager (for MCP servers)

### Installation

1. **Clone and navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database:**
   ```bash
   python -c "from utils.db_init import init_database; init_database()"
   ```

6. **Start the server:**
   ```bash
   python app.py
   ```

The server will start on `http://localhost:8080`

## 🔌 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/db/status` | GET | Database connectivity status |
| `/api/models` | GET | Available AI models |
| `/api/insights` | POST | Generate insights |
| `/api/chart` | POST | Generate chart data |
| `/api/answer` | POST | Streaming AI responses |

### Chat Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/threads` | GET | List chat threads |
| `/api/thread` | POST | Create new thread |
| `/api/thread/<id>` | GET | Get thread details |
| `/api/thread/<id>` | PUT | Update thread |
| `/api/thread/<id>` | DELETE | Delete thread |

## 🤖 AI Agents

### Fintech Sales Agent
- **Purpose**: Analyzes payment transactions and sales data
- **Database**: PostgreSQL with sales, transactions, merchants tables
- **Capabilities**: 
  - Daily/monthly/quarterly sales reports
  - Transaction analysis
  - Payment method insights
  - Merchant performance metrics

### Personal Tasks Agent
- **Purpose**: Manages personal tasks and documents
- **Integration**: Quip MCP server
- **Capabilities**:
  - Task creation and management
  - Document analysis
  - Workflow automation

### WAF Logs Agent
- **Purpose**: Security log analysis and monitoring
- **Integration**: CloudWatch MCP server
- **Capabilities**:
  - Log pattern analysis
  - Security threat detection
  - Performance monitoring

### AWS Resource Assistant
- **Purpose**: AWS infrastructure management
- **Integration**: AWS API MCP server
- **Capabilities**:
  - Resource inventory
  - Cost analysis
  - Configuration management

## 🗄️ Database Architecture

### Connection Management
- **Pool Size**: Configurable connection pooling
- **Connection Timeout**: 10 seconds
- **Pool Recycle**: 30 minutes
- **Singleton Pattern**: Single DatabaseManager instance

### Tables
- `chat_history` - Chat session persistence
- `daily_sales_report` - Aggregated sales data
- `transactions` - Real-time transaction records
- `merchants` - Merchant information
- `payment_methods` - Payment method catalog
- `payment_gateways` - Gateway configurations
- `pos_terminals` - POS terminal registry

## 🔒 Security Features

- **CORS Configuration**: Configurable cross-origin policies
- **Environment Variables**: Sensitive data protection
- **Connection Pooling**: Resource management and DoS protection
- **SQL Injection Prevention**: Parameterized queries
- **AWS IAM Integration**: Role-based access control

## 📊 Monitoring & Logging

### Application Logging
- **Utility Class**: Centralized logging with color coding
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Database Logging**: Query performance tracking
- **Agent Logging**: AI agent execution tracking

### Health Checks
- **Application Health**: `/health` endpoint
- **Database Health**: `/db/status` endpoint
- **Connection Pool Status**: Real-time pool metrics

## 🧪 Testing

### Database Testing
```bash
python -c "from utils.database import DatabaseManager; print(DatabaseManager().test_connection())"
```

### API Testing
```bash
curl http://localhost:8080/health
curl http://localhost:8080/db/status
```

### Agent Testing
```bash
curl -X POST http://localhost:8080/api/insights \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me daily sales for this month"}'
```

## 🚀 Deployment

### Production Configuration
```bash
export FLASK_ENV=production
export DEBUG=False
export PORT=8080
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "app.py"]
```

## 🤝 Contributing

1. Follow PEP 8 style guidelines
2. Add type hints for new functions
3. Include docstrings for public methods
4. Write tests for new features
5. Update this README for significant changes

## 📝 License

This project is proprietary software for enterprise use.

---

**Built with ❤️ using Flask, AWS Bedrock, and Model Context Protocol**