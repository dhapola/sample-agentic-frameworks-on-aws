# Project Structure Documentation

This document provides a detailed overview of the Gen AI Evaluation Platform project structure.

## Directory Tree

```
gen-ai-eval-platform/
├── backend/                          # Python FastAPI Backend
│   ├── app/                         # Application source code
│   │   ├── __init__.py             # Package initialization
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Configuration settings (env vars)
│   │   ├── api/                    # REST API endpoints (to be implemented)
│   │   │   └── __init__.py
│   │   ├── models/                 # Pydantic data models (to be implemented)
│   │   │   └── __init__.py
│   │   ├── database/               # Database layer
│   │   │   ├── __init__.py
│   │   │   └── connection.py      # MongoDB connection manager
│   │   ├── services/               # Business logic services (to be implemented)
│   │   │   └── __init__.py
│   │   ├── connectors/             # Application connector plugins (to be implemented)
│   │   │   └── __init__.py
│   │   └── engine/                 # Evaluation engine (to be implemented)
│   │       └── __init__.py
│   ├── tests/                      # Test suite
│   │   ├── __init__.py
│   │   ├── unit/                   # Unit tests
│   │   │   └── __init__.py
│   │   ├── properties/             # Property-based tests (Hypothesis)
│   │   │   └── __init__.py
│   │   └── integration/            # Integration tests
│   │       └── __init__.py
│   ├── requirements.txt            # Python dependencies
│   ├── pyproject.toml             # Python project configuration
│   ├── .env.example               # Environment variables template
│   └── README.md                  # Backend documentation
│
├── frontend/                        # React TypeScript Frontend
│   ├── src/                        # Application source code
│   │   ├── main.tsx               # Application entry point
│   │   ├── App.tsx                # Root component
│   │   ├── index.css              # Global styles
│   │   ├── vite-env.d.ts          # Vite type definitions
│   │   ├── components/            # Reusable UI components (to be implemented)
│   │   ├── views/                 # Page-level components (to be implemented)
│   │   ├── services/              # API client services (to be implemented)
│   │   ├── types/                 # TypeScript type definitions (to be implemented)
│   │   ├── contexts/              # React contexts (to be implemented)
│   │   └── utils/                 # Utility functions (to be implemented)
│   ├── tests/                     # Test suite
│   │   ├── setup.ts              # Test setup and configuration
│   │   ├── unit/                 # Unit tests (Jest + React Testing Library)
│   │   └── properties/           # Property-based tests (fast-check)
│   ├── public/                    # Static assets
│   ├── index.html                # HTML entry point
│   ├── package.json              # Node dependencies and scripts
│   ├── tsconfig.json             # TypeScript configuration
│   ├── tsconfig.node.json        # TypeScript config for Node
│   ├── vite.config.ts            # Vite build configuration
│   ├── jest.config.ts            # Jest test configuration
│   ├── .eslintrc.cjs             # ESLint configuration
│   ├── .env.example              # Environment variables template
│   └── README.md                 # Frontend documentation
│
├── scripts/                        # Development scripts
│   ├── setup.sh                  # Automated setup script
│   ├── start-dev.sh              # Start development servers
│   └── run-tests.sh              # Run all tests
│
├── .kiro/                         # Kiro specification files
│   └── specs/
│       └── gen-ai-eval-platform/
│           ├── requirements.md   # Requirements specification
│           ├── design.md         # Design document
│           └── tasks.md          # Implementation tasks
│
├── docker-compose.yml            # Docker Compose for MongoDB
├── Makefile                      # Development commands
├── .gitignore                    # Git ignore rules
├── README.md                     # Main project documentation
├── QUICKSTART.md                 # Quick start guide
└── PROJECT_STRUCTURE.md          # This file
```

## Key Files and Their Purpose

### Backend Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application entry point, defines lifespan events, CORS, and health endpoint |
| `app/config.py` | Configuration management using Pydantic Settings, loads from environment variables |
| `app/database/connection.py` | MongoDB connection manager with async Motor driver, handles connection lifecycle |
| `requirements.txt` | Python dependencies including FastAPI, Motor, Pydantic, pytest, Hypothesis |
| `pyproject.toml` | Python project configuration for pytest, black, mypy, and Hypothesis |

### Frontend Files

| File | Purpose |
|------|---------|
| `src/main.tsx` | React application entry point, renders root component |
| `src/App.tsx` | Root component with Material-UI theme and React Router |
| `package.json` | Node dependencies and npm scripts for dev, build, test |
| `vite.config.ts` | Vite configuration with React plugin and API proxy |
| `jest.config.ts` | Jest configuration for TypeScript and React Testing Library |
| `tsconfig.json` | TypeScript compiler configuration |

### Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | MongoDB service definition for local development |
| `Makefile` | Convenient commands for setup, start, test, and clean |
| `.gitignore` | Excludes venv, node_modules, .env, and build artifacts |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation with architecture and setup |
| `QUICKSTART.md` | Quick start guide for getting up and running |
| `PROJECT_STRUCTURE.md` | This file - detailed structure documentation |
| `backend/README.md` | Backend-specific documentation |
| `frontend/README.md` | Frontend-specific documentation |

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.6
- **Database Driver**: Motor 3.7.0 (async MongoDB)
- **Validation**: Pydantic 2.10.6
- **Testing**: pytest 8.3.4, Hypothesis 6.122.3
- **Code Quality**: black, flake8, mypy

### Frontend
- **Framework**: React 18.3.1
- **Language**: TypeScript 5.7.3
- **UI Library**: Material-UI 6.3.1
- **Build Tool**: Vite 6.0.7
- **Testing**: Jest 29.7.0, fast-check 3.24.2
- **HTTP Client**: Axios 1.7.9

### Database
- **Database**: MongoDB Community Edition 7.0
- **Driver**: Motor (async Python driver)

## Environment Variables

### Backend (.env)
```
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=gen_ai_eval_platform
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=INFO
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
```

## Development Workflow

### 1. Initial Setup
```bash
./scripts/setup.sh
# or
make setup
```

### 2. Start Services
```bash
# Start MongoDB
make start-db

# Start backend (terminal 1)
make start-backend

# Start frontend (terminal 2)
make start-frontend
```

### 3. Development
- Backend auto-reloads on file changes (FastAPI reload mode)
- Frontend has hot module replacement (Vite HMR)
- MongoDB data persists in Docker volume

### 4. Testing
```bash
# Run all tests
make test

# Run specific test suites
make test-backend
make test-frontend
```

## API Endpoints

### Current Endpoints
- `GET /api/health` - Health check endpoint

### Planned Endpoints (Future Tasks)
- Customer management: `/api/customers/*`
- Application profiles: `/api/application-profiles/*`
- Datasets: `/api/datasets/*`
- Evaluations: `/api/evaluations/*`

## Database Collections

### Planned Collections (Future Tasks)
- `customers` - Customer organizations (tenants)
- `applicationProfiles` - Gen AI application configurations
- `datasets` - Test datasets with test cases
- `evaluationRuns` - Evaluation execution records

All collections will include `customerId` for multi-tenant isolation.

## Testing Strategy

### Backend Testing
- **Unit Tests**: pytest for specific examples and edge cases
- **Property Tests**: Hypothesis for universal correctness properties
- **Integration Tests**: End-to-end workflow testing

### Frontend Testing
- **Unit Tests**: Jest + React Testing Library for components
- **Property Tests**: fast-check for UI properties
- **Coverage Goal**: >70% for interactive components

## Next Implementation Steps

Based on the tasks.md file, the next steps are:

1. **Task 2**: Implement data models and database layer
   - Create Pydantic models for all entities
   - Implement DataRepository with CRUD operations
   - Add tenant isolation at database level
   - Write property tests for data persistence

2. **Task 3**: Implement customer and application profile management
   - Create service layer for customer operations
   - Create service layer for application profiles
   - Write tests for management operations

3. **Task 4**: Implement Application Connector component
   - Create plugin interface and base classes
   - Implement HTTP/REST and WebSocket plugins
   - Write tests for connector functionality

4. **Task 5**: Implement Evaluation Engine
   - Create evaluation execution logic
   - Implement metrics calculator
   - Write tests for evaluation properties

5. **Task 6**: Implement REST API endpoints
   - Create FastAPI routers for all resources
   - Add input validation and error handling
   - Write API endpoint tests

6. **Task 7**: Implement Web UI components
   - Create React components for all views
   - Implement API client service
   - Write UI component tests

## Multi-Tenancy Architecture

The platform implements complete data isolation:

1. **Database Level**: All collections have `customerId` field with indexes
2. **Service Level**: All operations filter by customer context
3. **API Level**: Endpoints enforce tenant-scoped access
4. **UI Level**: Users only see their customer's data

## Build and Deployment

### Backend Build
```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### Frontend Build
```bash
cd frontend
npm install
npm run build
# Output in dist/ directory
```

### Production Deployment
- Backend: Deploy with uvicorn/gunicorn
- Frontend: Serve static files from dist/
- Database: MongoDB Atlas or self-hosted MongoDB cluster

## Maintenance Commands

```bash
# Clean all generated files
make clean

# Stop all services
make stop-db

# View all available commands
make help
```

## Contributing

When adding new features:
1. Follow the task list in `.kiro/specs/gen-ai-eval-platform/tasks.md`
2. Write tests before implementation (TDD)
3. Ensure property tests validate correctness properties
4. Update documentation as needed
5. Run full test suite before committing

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Material-UI Documentation](https://mui.com/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [fast-check Documentation](https://fast-check.dev/)
