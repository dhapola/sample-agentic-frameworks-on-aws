# Backend - Gen AI Evaluation Platform

Python FastAPI backend with async MongoDB integration.

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Run server
python -m app.main
```

Server runs at http://localhost:8000  
API docs at http://localhost:8000/docs

## Testing

```bash
# Clear test database
python clear_test_db.py

# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/unit/ -v           # Unit tests
pytest tests/properties/ -v     # Property-based tests
pytest tests/integration/ -v    # Integration tests

# With coverage
pytest --cov=app --cov-report=html
```

## Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── config.py        # Configuration
│   ├── api/             # REST endpoints
│   ├── models/          # Pydantic models
│   ├── database/        # Database layer
│   ├── services/        # Business logic
│   ├── connectors/      # Application plugins
│   ├── engine/          # Evaluation engine
│   ├── middleware/      # Request middleware
│   └── utils/           # Utilities
└── tests/
    ├── unit/            # Unit tests
    ├── properties/      # Property-based tests
    └── integration/     # Integration tests
```

## Environment Variables

```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=gen_ai_eval_platform
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=INFO
```

## Test Status

- **Total Tests**: 581
- **Passing**: 532 (93.5%)
- **Coverage**: Unit, property-based, and integration tests
- **Database**: Tests use real MongoDB for integration validation
