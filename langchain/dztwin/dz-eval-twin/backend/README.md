# Gen AI Evaluation Platform - Backend

Python FastAPI backend for the Gen AI Evaluation Platform.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your MongoDB connection details
```

4. Start MongoDB (if running locally):
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or install MongoDB Community Edition locally
```

5. Run the development server:
```bash
python -m app.main
```

The API will be available at http://localhost:8000
API documentation at http://localhost:8000/docs

## Testing

Run all tests:
```bash
pytest
```

Run unit tests only:
```bash
pytest tests/unit/
```

Run property-based tests only:
```bash
pytest tests/properties/
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── models/              # Pydantic data models
│   ├── database/            # Database layer
│   ├── services/            # Business logic services
│   ├── api/                 # API endpoints
│   ├── connectors/          # Application connector plugins
│   └── engine/              # Evaluation engine
├── tests/
│   ├── unit/                # Unit tests
│   ├── properties/          # Property-based tests
│   └── integration/         # Integration tests
├── requirements.txt
├── pyproject.toml
└── README.md
```
