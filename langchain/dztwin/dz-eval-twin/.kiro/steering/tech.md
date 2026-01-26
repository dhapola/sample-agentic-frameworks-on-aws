# Technology Stack

## Backend

- **Framework**: FastAPI (async Python web framework)
- **Language**: Python 3.11+
- **Database**: MongoDB 8.0 (NoSQL document database)
- **Database Driver**: Motor (async MongoDB driver for Python)
- **Validation**: Pydantic 2.x with pydantic-settings (data validation using type annotations)
- **Testing**: pytest, pytest-asyncio, Hypothesis (property-based testing), httpx (async HTTP testing), websockets
- **Code Quality**: black (formatter), flake8 (linter), mypy (type checker)

## Frontend

- **Framework**: React 18.3.1
- **Language**: TypeScript 5.7.3
- **Build Tool**: Vite 6.0.7 (fast dev server and bundler)
- **UI Library**: Material-UI 6.3.1 (@mui/material, @mui/icons-material, @emotion/react, @emotion/styled)
- **Routing**: React Router DOM 7.1.3
- **HTTP Client**: Axios 1.7.9
- **Charts**: Recharts 2.15.0
- **Testing**: Jest 29.7.0, React Testing Library (@testing-library/react, @testing-library/jest-dom, @testing-library/user-event), fast-check 4.5.3 (property-based testing), ts-jest

## Development Tools

- **Container Runtime**: Docker Compose with MongoDB 8.0 (can also use Finch as Docker alternative for macOS)
- **Make**: Development task automation
- **Scripts**: Bash scripts for setup and testing
- **Server**: Uvicorn with standard extras (ASGI server for FastAPI)

## Common Commands

### Setup
```bash
make setup              # Complete project setup
make install-backend    # Install Python dependencies
make install-frontend   # Install Node dependencies
```

### Database
```bash
make start-db          # Start MongoDB (Docker Compose)
make stop-db           # Stop MongoDB (Docker Compose down)
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
make test-frontend     # Run frontend tests (Jest with --passWithNoTests)

# Backend specific
cd backend
pytest                 # All tests
pytest tests/unit/     # Unit tests only
pytest tests/properties/  # Property-based tests only
pytest tests/integration/ # Integration tests only
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
- `backend/requirements.txt`: Python dependencies (no version pinning)
- `frontend/package.json`: Node dependencies and scripts
- `frontend/vite.config.ts`: Vite build configuration with path aliases and proxy
- `frontend/jest.config.ts`: Jest test configuration
- `frontend/tsconfig.json`: TypeScript compiler options with path aliases
- `frontend/tsconfig.node.json`: TypeScript config for Node.js files
- `docker-compose.yml`: MongoDB 8.0 service definition with healthcheck
- `Makefile`: Development task automation
- `.env` files: Environment configuration (use .env.example as template)

## Containers
**Container Runtime**: Docker Compose is the primary method. MongoDB 8.0 runs in a container with:
- Port mapping: 27017:27017
- Volume: mongodb_data for persistence
- Healthcheck: mongosh ping command
- Auto-restart: unless-stopped

Alternative: Finch can be used as a Docker alternative for macOS (https://runfinch.com/)