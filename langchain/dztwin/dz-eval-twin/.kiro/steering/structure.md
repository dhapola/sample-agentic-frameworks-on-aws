# Project Structure and Conventions

## Directory Layout

```
gen-ai-eval-platform/
├── backend/              # Python FastAPI backend
│   ├── app/             # Application source code
│   │   ├── main.py      # FastAPI entry point with lifespan management
│   │   ├── config.py    # Settings loaded from environment variables
│   │   ├── api/         # REST API endpoint routers
│   │   ├── models/      # Pydantic data models
│   │   ├── database/    # Database connection and repository layer
│   │   ├── services/    # Business logic services
│   │   ├── connectors/  # Application connector plugins (HTTP, WebSocket)
│   │   ├── engine/      # Evaluation engine and metrics calculator
│   │   ├── middleware/  # Request middleware (auth, logging, error handling)
│   │   └── utils/       # Utility functions
│   └── tests/           # Test suite
│       ├── unit/        # Unit tests (pytest)
│       ├── properties/  # Property-based tests (Hypothesis)
│       └── integration/ # Integration tests
├── frontend/            # React TypeScript frontend
│   ├── src/            # Application source code
│   │   ├── main.tsx    # React entry point
│   │   ├── App.tsx     # Root component with routing
│   │   ├── components/ # Reusable UI components
│   │   ├── views/      # Page-level components
│   │   ├── services/   # API client services
│   │   ├── types/      # TypeScript type definitions
│   │   ├── contexts/   # React contexts
│   │   └── utils/      # Utility functions
│   └── tests/          # Test suite
│       ├── unit/       # Unit tests (Jest + React Testing Library)
│       └── properties/ # Property-based tests (fast-check)
├── scripts/            # Development automation scripts
├── .kiro/              # Kiro specification files
│   ├── specs/         # Feature specifications
│   └── steering/      # Project steering documents (this file)
└── docs/              # Additional documentation
```

## Backend Architecture Patterns

### API Router Organization
```python
# main.py - Router registration
app.include_router(customers.router)           # /api/customers
app.include_router(application_profiles.router) # /api/customers/{id}/application-profiles
                                                # /api/application-profiles/{id}
app.include_router(datasets.router)             # /api/datasets
app.include_router(evaluations.router)          # /api/evaluations
```

### Layered Architecture
1. **API Layer** (`app/api/`): FastAPI routers, request/response handling
2. **Service Layer** (`app/services/`): Business logic, orchestration
3. **Database Layer** (`app/database/`): Data access, repository pattern
4. **Models** (`app/models/`): Pydantic models for validation and serialization

### Key Patterns

**Async/Await**: All I/O operations use async/await with Motor (async MongoDB driver)
```python
async def get_customer(customer_id: str) -> Optional[Customer]:
    result = await database_manager.database.customers.find_one({"id": customer_id})
    return Customer(**result) if result else None
```

**Dependency Injection**: FastAPI dependencies for services and customer context
```python
from fastapi import Depends, Request

def get_customer_id(request: Request) -> str:
    """Get customer_id from request state set by middleware."""
    customer_id = getattr(request.state, "customer_id", None)
    if not customer_id:
        raise UnauthorizedError("Customer context required. Please provide X-Customer-ID header.")
    return customer_id

@router.get("/datasets")
async def list_datasets(
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
):
    # customer_id and service injected automatically
```

**Pydantic Models**: Type-safe data validation and serialization
```python
class Customer(BaseModel):
    id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: EmailStr
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
```

**Middleware**: Request processing pipeline (order matters)
- `CORSMiddleware`: CORS handling (added first for preflight requests)
- `LoggingMiddleware`: Request/response logging with timing
- `CustomerContextMiddleware`: Tenant isolation via X-Customer-ID header
- `error_handler_middleware`: Centralized error handling with standardized responses
- `validation_exception_handler`: Pydantic validation error formatting

**Database Manager**: Singleton pattern with retry logic and health checks
```python
from app.database.connection import database_manager

# In lifespan (main.py)
await database_manager.connect()  # Retries up to 3 times with exponential backoff
# Use database
db = database_manager.database
# Health check
is_healthy = await database_manager.health_check()
# Disconnect
await database_manager.disconnect()
```

## Frontend Architecture Patterns

### Routing Structure
```typescript
// App.tsx with React Router
<Routes>
  <Route path="/" element={<Layout />}>
    <Route index element={<DashboardView />} />
    <Route path="admin" element={<AdminView />} />
    <Route path="datasets" element={<DatasetsView />} />
    <Route path="evaluations" element={<EvaluationsView />} />
    <Route path="results" element={<ResultsView />} />
  </Route>
</Routes>
```

### Component Organization
- **Components** (`src/components/`): Reusable, presentational components
- **Views** (`src/views/`): Page-level components with business logic
- **Services** (`src/services/`): API client, data fetching
- **Contexts** (`src/contexts/`): Global state management

### Key Patterns

**TypeScript Types**: Shared type definitions in `src/types/`
```typescript
export interface Customer {
  id: string;
  name: string;
  contactEmail: string;
  contactPhone?: string;
  configuration?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface ConnectionConfig {
  endpoint: string;
  authentication?: Record<string, any>;
  timeout?: number;
  retries?: number;
  customHeaders?: Record<string, string>;
}

export interface ApplicationProfile {
  id: string;
  customerId: string;
  name: string;
  type: string; // "chatbot" | "rag" | "agent" | "workflow" | "custom"
  connectionConfig: ConnectionConfig;
  createdAt: string;
  updatedAt: string;
}
```

**API Client**: Axios-based service layer with interceptors
```typescript
// src/services/api.ts
import axios from 'axios';

const apiClient = new APIClient();

// Set customer context for tenant-scoped requests
apiClient.setCustomerContext(customerId);

// Make requests
const customers = await apiClient.getCustomers();
const datasets = await apiClient.getDatasets(); // Uses X-Customer-ID header

// Clear customer context
apiClient.clearCustomerContext();
```

**Material-UI**: Consistent component styling
```typescript
import { Button, Card, Typography } from '@mui/material';
```

## Coding Conventions

### Backend (Python)

**Style**: Follow PEP 8, enforced by black (100 char line length)

**Type Hints**: Required on all function signatures
```python
def calculate_metrics(responses: list[Response]) -> dict[str, float]:
    ...
```

**Docstrings**: Use for public functions and classes
```python
def validate_input(data: dict[str, Any]) -> bool:
    """
    Validate input data against schema.
    
    Args:
        data: Input data dictionary
        
    Returns:
        True if valid, False otherwise
    """
```

**Imports**: Organized in groups (stdlib, third-party, local)
```python
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.database.connection import database_manager
```

**Error Handling**: Custom exception classes with standardized responses
```python
from app.middleware.error_handler import (
    NotFoundError, ValidationError, UnauthorizedError,
    DatabaseError, ConnectionError, ForbiddenError
)

# Raise custom exceptions
if not customer:
    raise NotFoundError(f"Customer {customer_id} not found")

if not customer_id:
    raise UnauthorizedError("Customer context required. Please provide X-Customer-ID header.")

# Errors are caught by error_handler_middleware and converted to:
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Customer cust_123 not found",
    "details": null,
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Frontend (TypeScript)

**Style**: Follow ESLint rules, 2-space indentation

**Type Safety**: Avoid `any`, use explicit types
```typescript
interface Props {
  customerId: string;
  onSelect: (id: string) => void;
}
```

**Component Structure**: Functional components with hooks
```typescript
export const CustomerList: React.FC<Props> = ({ customerId, onSelect }) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  
  useEffect(() => {
    // Fetch data
  }, [customerId]);
  
  return <div>...</div>;
};
```

**File Naming**: 
- Components: PascalCase (`CustomerList.tsx`)
- Utilities: camelCase (`formatDate.ts`)
- Types: camelCase (`customer.ts`)

## Multi-Tenancy Implementation

### Database Level
- All collections have `customerId` field (camelCase)
- Indexes on `customerId` for efficient queries
- Repository methods filter by customer context
- Automatic index creation in `database_manager._create_indexes()`

### Service Level
- All tenant-scoped operations accept `customer_id` parameter
- Automatic filtering in repository layer
```python
async def list_datasets(customer_id: str) -> list[Dataset]:
    cursor = database_manager.database.datasets.find({"customerId": customer_id})
    return [Dataset(**doc) async for doc in cursor]
```

### API Level
- Customer context extracted from `X-Customer-ID` header by `CustomerContextMiddleware`
- Stored in `request.state.customer_id`
- Admin endpoints (customers, application profiles) exempt from customer context requirement
- Tenant-scoped endpoints (datasets, evaluations) require customer context via dependency injection
- Middleware enforces tenant isolation at the request level

## Testing Conventions

### Backend Tests

**File Naming**: `test_*.py` in `tests/unit/` or `tests/properties/`

**Unit Tests**: Specific examples and edge cases
```python
def test_customer_validation():
    """Test customer name validation."""
    with pytest.raises(ValueError):
        Customer(id="123", name="", contact_email="test@example.com")
```

**Property Tests**: Universal properties with Hypothesis
```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=200))
def test_customer_name_roundtrip(name: str):
    """Property: Customer name should survive serialization."""
    customer = Customer(id="123", name=name, contact_email="test@example.com")
    assert customer.name == name.strip()
```

**Async Tests**: Use pytest-asyncio
```python
@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection."""
    await database_manager.connect()
    assert database_manager.is_connected()
```

### Frontend Tests

**File Naming**: `*.test.tsx` co-located with components

**Component Tests**: React Testing Library
```typescript
import { render, screen } from '@testing-library/react';

test('renders customer name', () => {
  render(<CustomerCard customer={mockCustomer} />);
  expect(screen.getByText('Acme Corp')).toBeInTheDocument();
});
```

**Property Tests**: fast-check for UI properties
```typescript
import fc from 'fast-check';

test('customer name always displays', () => {
  fc.assert(
    fc.property(fc.string(), (name) => {
      const { container } = render(<CustomerCard customer={{ name }} />);
      return container.textContent?.includes(name) ?? false;
    })
  );
});
```

## Database Conventions

### Collection Naming
- camelCase: `customers`, `applicationProfiles`, `datasets`, `evaluationRuns`

### Document Structure
- Always include `customerId` for tenant isolation
- Use ISO 8601 timestamps: `createdAt`, `updatedAt`
- Use descriptive field names in camelCase

### Indexes
- Primary: `customerId` on all collections
- Composite indexes for common queries:
  - `evaluationRuns`: `[("customerId", 1), ("status", 1)]`
  - `evaluationRuns`: `[("customerId", 1), ("startTime", -1)]`
- Created automatically in `database_manager._create_indexes()`
- Collections: `customers`, `applicationProfiles`, `datasets`, `evaluationRuns`

## Validation Patterns

### Backend Validation
- **Pydantic Models**: Field-level validation with `Field()` constraints
- **Custom Validators**: Use `@field_validator` for complex validation logic
- **ID Validation**: Utility functions in `app/utils/validation.py`:
  - `validate_customer_id()`
  - `validate_application_profile_id()`
  - `validate_dataset_id()`
  - `validate_test_case_id()`
- **Request Validation**: Separate request models (e.g., `CreateCustomerRequest`, `UpdateCustomerRequest`)
- **Response Models**: Separate response models with `from_model()` class methods

### Frontend Validation
- TypeScript interfaces for type safety
- API client validates responses match expected types
- Form validation in UI components (Material-UI integration)

## API Conventions

### Endpoint Structure
- Base path: `/api/`
- Admin endpoints: `/api/customers`, `/api/customers/{customer_id}/application-profiles`, `/api/application-profiles/{profile_id}`
- Tenant-scoped endpoints: `/api/datasets`, `/api/evaluations`
- RESTful verbs: GET, POST, PUT, DELETE
- Nested resources: `/api/datasets/{dataset_id}/test-cases`

### Request Headers
- `X-Customer-ID`: Required for tenant-scoped endpoints (datasets, evaluations)
- `X-Request-Time`: Added automatically by API client
- `Content-Type: application/json`

### Response Format
```json
{
  "id": "123",
  "customerId": "cust_456",
  "name": "Resource Name",
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

### Error Format
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": null,
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Status Codes
- 200: Success (GET, PUT)
- 201: Created (POST)
- 204: No Content (DELETE)
- 400: Validation Error
- 401: Unauthorized (missing customer context)
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error
- 503: Service Unavailable (connection errors)

## Configuration Management

### Backend
- Use `pydantic-settings` for environment variables
- Define in `app/config.py` as `Settings` class
- Access via `settings` singleton
- Supports `.env` file loading with `SettingsConfigDict`
- Properties: `cors_origins_list` parses comma-separated CORS origins

### Frontend
- Use Vite environment variables (`VITE_*`)
- Access via `import.meta.env.VITE_API_BASE_URL` or `process.env.VITE_API_BASE_URL`
- Path aliases configured: `@/*` maps to `src/*`
- Proxy configuration in `vite.config.ts` for `/api` requests

## Logging

### Backend
- Use Python `logging` module
- Configure in `main.py` with `logging.basicConfig()`
- Log level from `settings.log_level` (default: INFO)
- Format: `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
- Middleware adds request/response logging with timing
- Error handler logs exceptions with `exc_info=True`

### Frontend
- Use `console.log`, `console.error` for development
- API client logs requests/responses in development mode
- Error interceptor logs API errors with status codes
- Consider structured logging for production
