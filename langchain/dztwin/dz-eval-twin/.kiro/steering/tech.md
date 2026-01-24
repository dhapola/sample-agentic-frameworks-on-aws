# Technology Stack

## Backend

- **Framework**: FastAPI 0.115.6 (async Python web framework)
- **Language**: Python 3.11+
- **Database**: MongoDB Community Edition 7.0 (NoSQL document database)
- **Database Driver**: Motor 3.7.0 (async MongoDB driver for Python)
- **Validation**: Pydantic 2.10.6 (data validation using type annotations)
- **Testing**: pytest 8.3.4, pytest-asyncio, Hypothesis 6.122.3 (property-based testing)
- **Code Quality**: black (formatter), flake8 (linter), mypy (type checker)

## Frontend

- **Framework**: React 18.3.1
- **Language**: TypeScript 5.7.3
- **Build Tool**: Vite 6.0.7 (fast dev server and bundler)
- **UI Library**: Material-UI 6.3.1 (@mui/material)
- **Routing**: React Router 7.1.3
- **HTTP Client**: Axios 1.7.9
- **Charts**: Recharts 2.15.0
- **Testing**: Jest 29.7.0, React Testing Library, fast-check 3.24.2 (property-based testing)

## Development Tools

- **Docker**: MongoDB containerization via docker-compose
- **Make**: Development task automation
- **Scripts**: Bash scripts for setup and testing

## Common Commands

### Setup
```bash
make setup              # Complete project setup
make install-backend    # Install Python dependencies
make install-frontend   # Install Node dependencies
```

### Database
```bash
make start-db          # Start MongoDB (Docker)
make stop-db           # Stop MongoDB
```

### Development
```bash
make start-backend     # Start FastAPI server (http://localhost:8000)
make start-frontend    # Start Vite dev server (http://localhost:3000)
```

### Testing
```bash
make test              # Run all tests
make test-backend      # Run backend tests (pytest)
make test-frontend     # Run frontend tests (Jest)

# Backend specific
cd backend
pytest                 # All tests
pytest tests/unit/     # Unit tests only
pytest tests/properties/  # Property-based tests only
pytest --cov=app       # With coverage

# Frontend specific
cd frontend
npm test               # All tests
npm run test:watch     # Watch mode
npm run test:coverage  # With coverage
```

### Build
```bash
# Backend
cd backend
python -m app.main     # Run server directly

# Frontend
cd frontend
npm run build          # Production build
npm run preview        # Preview production build
```

### Code Quality
```bash
# Backend
cd backend
black .                # Format code
flake8 .              # Lint code
mypy app/             # Type check

# Frontend
cd frontend
npm run lint          # ESLint
```

## Environment Configuration

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

## API Documentation

- **Swagger UI**: http://localhost:8000/docs (interactive API docs)
- **Health Check**: http://localhost:8000/api/health

## Testing Strategy

### Backend
- **Unit Tests**: pytest for specific examples and edge cases
- **Property Tests**: Hypothesis for universal correctness properties across many inputs
- **Integration Tests**: End-to-end workflow testing
- **Async Testing**: pytest-asyncio for async code

### Frontend
- **Unit Tests**: Jest + React Testing Library for components
- **Property Tests**: fast-check for UI properties
- **Coverage Goal**: >70% for interactive components

## Key Configuration Files

- `backend/pyproject.toml`: pytest, black, mypy, Hypothesis configuration
- `backend/requirements.txt`: Python dependencies
- `frontend/package.json`: Node dependencies and scripts
- `frontend/vite.config.ts`: Vite build configuration
- `frontend/jest.config.ts`: Jest test configuration
- `frontend/tsconfig.json`: TypeScript compiler options
- `docker-compose.yml`: MongoDB service definition
- `Makefile`: Development task automation
