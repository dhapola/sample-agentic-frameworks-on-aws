# Gen AI Evaluation Platform

A multi-tenant web-based platform for evaluating generative AI applications through systematic testing with managed datasets, automated evaluation execution, and comprehensive performance metrics.

## Features

- **Multi-Tenancy**: Complete data isolation between customer organizations
- **Dataset Management**: Create and manage test datasets with input/output pairs
- **Application Profiles**: Configure and manage gen AI application connections
- **Evaluation Execution**: Run automated evaluations against application profiles
- **Metrics & Analytics**: Calculate accuracy, relevance, and latency metrics
- **Results Dashboard**: Interactive web interface for viewing and comparing results

## Architecture

- **Backend**: Python FastAPI with async MongoDB driver (Motor)
- **Frontend**: React with TypeScript and Material-UI
- **Database**: MongoDB 8 Community Edition (NoSQL database with multi-tenancy support)
- **Container Runtime**: Finch (for running MongoDB)
- **Testing**: pytest + Hypothesis (backend), Jest + fast-check (frontend)

## Project Structure

```
gen-ai-eval-platform/
├── backend/                 # Python FastAPI backend
│   ├── app/                # Application code
│   │   ├── api/           # REST API endpoints
│   │   ├── models/        # Pydantic data models
│   │   ├── database/      # Database layer
│   │   ├── services/      # Business logic
│   │   ├── connectors/    # Application connector plugins
│   │   └── engine/        # Evaluation engine
│   ├── tests/             # Test suite
│   │   ├── unit/          # Unit tests
│   │   ├── properties/    # Property-based tests
│   │   └── integration/   # Integration tests
│   └── requirements.txt   # Python dependencies
├── frontend/               # React TypeScript frontend
│   ├── src/               # Application code
│   │   ├── components/    # Reusable UI components
│   │   ├── views/         # Page-level components
│   │   ├── services/      # API client
│   │   ├── types/         # TypeScript types
│   │   └── contexts/      # React contexts
│   ├── tests/             # Test suite
│   │   ├── unit/          # Unit tests
│   │   └── properties/    # Property-based tests
│   └── package.json       # Node dependencies
└── README.md              # This file
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Finch (container runtime) - [Installation Guide](https://runfinch.com/)

### Database Setup

**Start MongoDB 8 using Finch:**

```bash
# Start MongoDB 8 container
finch compose up -d

# Initialize database with indexes
./scripts/init-mongodb.sh

# Verify connection
python scripts/test-mongodb-connection.py
```

MongoDB will be available at `mongodb://localhost:27017`

For detailed MongoDB setup instructions, see [MONGODB_SETUP.md](MONGODB_SETUP.md)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# MongoDB is already configured to use localhost:27017
```

5. Run the backend server:
```bash
python -m app.main
```

The API will be available at http://localhost:8000
API documentation at http://localhost:8000/docs

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
```bash
cp .env.example .env
```

4. Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run property-based tests only
pytest tests/properties/

# Run with coverage
pytest --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

## Development

### Backend Development

The backend uses:
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation using Python type annotations
- **Motor**: Async MongoDB driver for Python
- **pytest**: Testing framework
- **Hypothesis**: Property-based testing library

### Frontend Development

The frontend uses:
- **React 18**: UI library with hooks
- **TypeScript**: Type-safe JavaScript
- **Material-UI**: Component library
- **Vite**: Fast build tool and dev server
- **Jest**: Testing framework
- **fast-check**: Property-based testing library

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation powered by Swagger UI.

## Multi-Tenancy

The platform implements complete data isolation between customers:
- All data entities include a `customer_id` field
- Database queries automatically filter by customer context
- API endpoints enforce tenant-scoped access
- Users can only access data belonging to their customer organization

## License

This project is part of the Gen AI Evaluation Platform specification.

## Next Steps

This is the initial project structure. Subsequent tasks will implement:
1. Data models and database layer
2. Customer and application profile management
3. Application connector plugins
4. Evaluation engine
5. REST API endpoints
6. Web UI components
7. Integration and end-to-end testing
