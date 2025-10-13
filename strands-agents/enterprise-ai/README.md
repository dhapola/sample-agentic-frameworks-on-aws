# Enterprise AI Assistant

A comprehensive enterprise-grade AI assistant application built with React frontend, Flask backend, and PostgreSQL database. The system leverages AI agents powered by Amazon Bedrock and Model Context Protocol (MCP) servers to provide intelligent data analysis and insights.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  Flask Backend  │    │   PostgreSQL    │
│     (Port 8081)  │◄──►│   (Port 8080)   │◄──►│    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  MCP Servers    │
                    │  - AWS API      │
                    │  - PostgreSQL   │
                    │  - Quip         │
                    │  - CloudWatch   │
                    └─────────────────┘
```

## 🚀 Features

### Frontend (React)
- **Modern UI**: Built with Material-UI (MUI) components
- **Real-time Chat**: Interactive chat interface with streaming responses
- **Data Visualization**: Charts and graphs using ApexCharts
- **Document Export**: PDF generation with jsPDF
- **Responsive Design**: Mobile-friendly interface
- **Markdown Support**: Rich text rendering with syntax highlighting

### Backend (Flask)
- **RESTful API**: Clean API endpoints for all operations
- **AI Agents**: Specialized agents for different domains:
  - Fintech Sales Analysis
  - Personal Task Management
  - WAF Log Analysis
  - MCP Server Integration
- **Streaming Responses**: Real-time AI response streaming
- **Database Integration**: SQLAlchemy ORM with PostgreSQL
- **Model Context Protocol**: Integration with multiple MCP servers

### Database & Data Generation
- **PostgreSQL Database**: Robust data storage
- **Synthetic Data Generation**: Realistic fintech transaction data
- **Data Models**: Comprehensive schema for:
  - Merchants and Payment Gateways
  - POS Terminals and Transactions
  - Sales Reports and Analytics
  - Chat History and User Sessions

## 📁 Project Structure

```
enterprise-ai/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── utils/          # Utility functions
│   │   └── App.js          # Main application component
│   ├── public/             # Static assets
│   └── package.json        # Frontend dependencies
│
├── backend/                 # Flask backend application
│   ├── agents/             # AI agent implementations
│   ├── providers/          # Service providers (Bedrock, MCP)
│   ├── resources/          # API endpoints
│   ├── repositories/       # Data access layer
│   ├── utils/             # Backend utilities
│   ├── config/            # Configuration files
│   ├── app.py             # Main Flask application
│   ├── requirements.txt   # Backend dependencies
│   └── mcp.json          # MCP server configuration
│
├── app-db/                 # Database models and utilities
│   ├── models.py          # SQLAlchemy models
│   ├── database_config.py # Database configuration
│   ├── build_database.py  # Database setup script
│   └── migrations.py      # Database migrations
│
├── sales-data-prep/        # Data generation scripts
│   ├── generate_merchants.py
│   ├── transactions.py
│   ├── sales_report_table.py
│   ├── query_sales_report.py
│   └── generate_all_data.sh
│
└── README.md              # This file
```

## 🛠️ Installation & Setup

### Prerequisites
- Node.js (v16 or higher)
- Python 3.8+
- PostgreSQL 12+
- AWS CLI configured (for Bedrock access)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd enterprise-ai
```

### 2. Database Setup
```bash
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE your_database_name;
CREATE USER your_db_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE your_database_name TO your_db_user;
\q
```

### 3. Backend Setup
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -c "from utils.db_init import init_database; init_database()"
```

### 4. Generate Sample Data
```bash
cd ../sales-data-prep

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with database credentials

# Generate all sample data
chmod +x generate_all_data.sh
./generate_all_data.sh
```

### 5. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Create environment file (if needed)
# Edit src/env.js for API endpoints
```

## 🚀 Running the Application

### Start Backend Server
```bash
cd backend
source venv/bin/activate
python app.py
```
Backend will be available at `http://localhost:8080`

### Start Frontend Development Server
```bash
cd frontend
npm start
```
Frontend will be available at `http://localhost:8081`

### Verify Installation
1. Visit `http://localhost:8081` in your browser
2. Check backend health: `http://localhost:8080/health`
3. Check database status: `http://localhost:8080/db/status`

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
# Database Configuration
DB_HOST=localhost
DB_NAME=your_database_name
DB_PORT=5432
DB_USERNAME=your_db_user
DB_PASSWORD=your_secure_password

# AWS Configuration
AWS_REGION=your-aws-region
AWS_PROFILE=default

# Application Configuration
FLASK_ENV=development
DEBUG=True
PORT=8080
```

#### Sales Data Prep (.env)
```env
DB_HOST=localhost
DB_NAME=your_database_name
DB_PORT=5432
DB_USERNAME=your_db_user
DB_PASSWORD=your_secure_password
REGION=your-aws-region
```

### MCP Server Configuration
The `backend/mcp.json` file configures available MCP servers:
- **AWS API MCP Server**: AWS service interactions
- **PostgreSQL MCP Server**: Database operations
- **Quip MCP Server**: Document management
- **CloudWatch Logs MCP Server**: Log analysis

## 🤖 AI Agents

### Fintech Sales Agent
- Analyzes payment transaction data
- Generates sales reports and insights
- Supports natural language queries
- Integrates with PostgreSQL database

### Personal Tasks Agent
- Manages personal task lists
- Integrates with Quip for document management
- Supports task creation and tracking

### WAF Logs Agent
- Analyzes web application firewall logs
- Identifies security patterns and threats
- Integrates with CloudWatch Logs

### MCP Servers Agent
- Orchestrates multiple MCP servers
- Provides unified interface for various tools
- Supports dynamic tool discovery

## 📊 Database Schema

### Core Tables
- **merchants**: Merchant information and details
- **payment_gateways**: Payment processing providers
- **payment_methods**: Available payment options
- **pos_terminals**: Point-of-sale terminal data
- **transactions**: Transaction records and status
- **daily_sales_report**: Aggregated sales analytics
- **chat_history**: User conversation history

### Sample Queries
```sql
-- Top performing merchants
SELECT merchant_name, SUM(amount) as total_sales
FROM transactions t
JOIN merchants m ON t.merchant_id = m.merchant_id
WHERE t.status = 'completed'
GROUP BY merchant_name
ORDER BY total_sales DESC
LIMIT 10;

-- Monthly sales trend
SELECT DATE_TRUNC('month', transaction_date) as month,
       SUM(amount) as monthly_sales
FROM transactions
WHERE status = 'completed'
GROUP BY month
ORDER BY month;
```

## 🔌 API Endpoints

### Core APIs
- `GET /health` - Health check
- `GET /db/status` - Database status
- `GET /api/models` - Available AI models
- `POST /api/answer` - Stream AI responses
- `POST /api/insights` - Generate insights
- `POST /api/chart` - Create visualizations

### Chat Management
- `GET /api/threads` - List chat threads
- `GET /api/thread/<id>` - Get specific thread
- `POST /api/thread` - Create new thread
- `PUT /api/thread/<id>` - Update thread
- `DELETE /api/thread/<id>` - Delete thread

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Test database connection
cd sales-data-prep
python test_connection.py

# Test API endpoints
curl http://localhost:8080/health
curl http://localhost:8080/db/status
```

## 📈 Performance Optimization

### Database
- Indexed columns for faster queries
- Connection pooling with SQLAlchemy
- Batch operations for data generation
- Query optimization for large datasets

### Frontend
- Code splitting and lazy loading
- Memoized components
- Optimized bundle size
- Service worker for caching

### Backend
- Async processing for AI responses
- Connection pooling
- Response caching
- Error handling and retry logic

## 🔒 Security Considerations

- Environment variables for sensitive data
- Database connection encryption
- API rate limiting (recommended)
- Input validation and sanitization
- CORS configuration for frontend access

## 🚀 Deployment

### Docker Deployment (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Manual Deployment
1. Set up production database
2. Configure environment variables
3. Build frontend: `npm run build`
4. Deploy backend with WSGI server (Gunicorn)
5. Serve frontend with Nginx

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **[Your Name]** - Initial work and development

## 🙏 Acknowledgments

- Amazon Bedrock for AI model access
- Strands Agents framework for agent orchestration
- Model Context Protocol for tool integration
- Material-UI for React components
- Flask ecosystem for backend development

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the documentation in each component directory
- Review the API documentation at `/api/docs` (when running)

## 🔄 Version History

- **v0.1.1** - Current version with full feature set
- **v0.1.0** - Initial release with basic functionality

---

**Note**: This application is designed for enterprise use and requires proper AWS credentials and database setup. Ensure all security best practices are followed in production deployments.
