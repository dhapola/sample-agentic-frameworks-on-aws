# Technology Stack

## Frontend
- **Framework**: React 19.1.0
- **UI Library**: Material-UI (MUI) v7.0.1 with Emotion styling
- **Charts**: ApexCharts with react-apexcharts
- **Markdown**: react-markdown with remark-gfm and rehype-raw
- **PDF Export**: jsPDF with jspdf-autotable
- **Build Tool**: Create React App (react-scripts)
- **Port**: 8081 (development)

## Backend
- **Framework**: Flask with Flask-RESTful
- **AI Framework**: Strands Agents with langchain-mcp-adapters
- **Cloud AI**: Amazon Bedrock (Claude models, Nova models)
- **Database ORM**: SQLAlchemy 2.0+
- **Database Driver**: psycopg2-binary
- **CORS**: Flask-CORS
- **Environment**: python-dotenv
- **Port**: 8080

## Database
- **Primary**: PostgreSQL 12+
- **Connection**: SQLAlchemy with connection pooling
- **Migrations**: Custom migration scripts in app-db/

## AI & Integration
- **Model Context Protocol (MCP)**: Tool integration framework
- **AWS Services**: Bedrock, CloudWatch Logs
- **MCP Servers**: PostgreSQL, AWS API, Quip, CloudWatch
- **Agent Models**: Claude 3 Haiku, Claude 3.5 Sonnet, Nova Lite

## Development Tools
- **Package Managers**: npm (frontend), pip (backend)
- **Environment**: Virtual environments for Python
- **Configuration**: .env files for environment variables

## Common Commands

### Frontend Development
```bash
cd frontend
npm install                 # Install dependencies
npm start                   # Start dev server (port 8081)
npm run build              # Build for production
npm test                   # Run tests
```

### Backend Development
```bash
cd backend
python3 -m venv venv       # Create virtual environment
source venv/bin/activate   # Activate virtual environment
pip install -r requirements.txt  # Install dependencies
python app.py              # Start Flask server (port 8080)
```

### Database Setup
```bash
cd app-db
python build_database.py   # Initialize database schema
python -c "from utils.db_init import init_database; init_database()"
```

### Data Generation
```bash
cd sales-data-prep
pip install -r requirements.txt
chmod +x generate_all_data.sh
./generate_all_data.sh     # Generate synthetic data
```

### Health Checks
```bash
curl http://localhost:8080/health     # Backend health
curl http://localhost:8080/db/status  # Database status
```