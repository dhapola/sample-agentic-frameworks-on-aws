# Project Structure & Organization

## Root Directory Layout
```
enterprise-ai/
├── frontend/           # React application
├── backend/           # Flask API server
├── app-db/           # Database models and utilities
├── sales-data-prep/  # Data generation scripts
└── .kiro/           # Kiro configuration and steering
```

## Frontend Structure (`frontend/`)
```
frontend/
├── src/
│   ├── components/     # React components (Chat, LayoutApp, etc.)
│   ├── utils/         # Utility functions (ApiCalls, Utils, pdfExport)
│   ├── App.js         # Main application component
│   ├── env.js         # Environment configuration
│   └── index.js       # Application entry point
├── public/            # Static assets and images
└── package.json       # Dependencies and scripts
```

## Backend Structure (`backend/`)
```
backend/
├── agents/            # AI agent implementations
│   ├── fintech_sales_postgresql.py
│   ├── personal_tasks.py
│   ├── waf_logs.py
│   └── mcp_servers.py
├── providers/         # Service providers (Bedrock, MCP)
├── resources/         # Flask-RESTful API endpoints
├── repositories/      # Data access layer
├── utils/            # Backend utilities and helpers
├── config/           # Configuration modules
├── app.py            # Main Flask application
├── mcp.json          # MCP server configuration
└── requirements.txt   # Python dependencies
```

## Database Layer (`app-db/`)
```
app-db/
├── models.py          # SQLAlchemy model definitions
├── database_config.py # Database connection configuration
├── build_database.py  # Database initialization script
├── migrations.py      # Database migration utilities
└── repositories.py    # Data repository patterns
```

## Data Generation (`sales-data-prep/`)
```
sales-data-prep/
├── generate_merchants.py    # Merchant data generation
├── transactions.py          # Transaction data generation
├── sales_report_table.py    # Sales reporting data
├── payment_gateways.py      # Payment gateway data
├── payment_methods.py       # Payment method data
├── pos_terminals.py         # POS terminal data
├── generate_all_data.sh     # Master data generation script
└── query_sales_report.py    # Sample queries
```

## Architectural Patterns

### Backend Patterns
- **Repository Pattern**: Data access abstraction in `repositories/`
- **Provider Pattern**: External service integration in `providers/`
- **Resource Pattern**: RESTful API endpoints in `resources/`
- **Agent Pattern**: AI agent implementations in `agents/`

### Frontend Patterns
- **Component-Based Architecture**: Reusable UI components
- **Utility Pattern**: Shared functions in `utils/`
- **API Layer**: Centralized API calls in `utils/ApiCalls.js`

### Database Patterns
- **Model-Repository Pattern**: SQLAlchemy models with repository layer
- **Migration Pattern**: Version-controlled schema changes
- **Configuration Pattern**: Environment-based database configuration

## File Naming Conventions
- **Python**: snake_case for files and functions
- **JavaScript**: camelCase for functions, PascalCase for components
- **Components**: PascalCase (e.g., `Chat.js`, `LayoutApp.js`)
- **Utilities**: camelCase (e.g., `apiCalls.js`, `pdfExport.js`)
- **Configuration**: lowercase with underscores (e.g., `database_config.py`)

## Import Patterns
- **Relative imports** for local modules
- **Absolute imports** from `src/` in frontend
- **Grouped imports**: standard library, third-party, local modules

## Environment Configuration
- **Frontend**: `src/env.js` for configuration constants
- **Backend**: `.env` files with python-dotenv
- **Database**: Separate `.env` files per component
- **MCP**: `mcp.json` for server configuration