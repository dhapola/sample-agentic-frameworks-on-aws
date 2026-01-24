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

**Dependency Injection**: FastAPI dependencies for database, authentication, etc.
```python
from fastapi import Depends

async def get_current_customer(customer_id: str = Header(...)) -> str:
    return customer_id

@router.get("/datasets")
async def list_datasets(customer_id: str = Depends(get_current_customer)):
    # customer_id injected automatically
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

**Middleware**: Request processing pipeline
- `LoggingMiddleware`: Request/response logging
- `CustomerContextMiddleware`: Tenant isolation
- `error_handler_middleware`: Centralized error handling

**Database Manager**: Singleton pattern for connection lifecycle
```python
from app.database.connection import database_manager

# In lifespan
await database_manager.connect()
# Use database
db = database_manager.database
```

## Frontend Architecture Patterns

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
}
```

**API Client**: Axios-based service layer
```typescript
// src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

export const customerService = {
  list: () => api.get<Customer[]>('/api/customers'),
  get: (id: string) => api.get<Customer>(`/api/customers/${id}`),
};
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

**Error Handling**: Use FastAPI HTTPException
```python
from fastapi import HTTPException, status

if not customer:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Customer {customer_id} not found"
    )
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
- All collections have `customerId` field
- Indexes on `customerId` for efficient queries
- Repository methods filter by customer context

### Service Level
- All operations accept `customer_id` parameter
- Automatic filtering in repository layer
```python
async def list_datasets(customer_id: str) -> list[Dataset]:
    cursor = database_manager.database.datasets.find({"customerId": customer_id})
    return [Dataset(**doc) async for doc in cursor]
```

### API Level
- Customer context extracted from headers/auth
- Middleware enforces tenant isolation
- Endpoints automatically scoped to customer

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
- Composite: `[("customerId", 1), ("status", 1)]` for common queries
- Created automatically in `database_manager._create_indexes()`

## API Conventions

### Endpoint Structure
- Base path: `/api/`
- Resource-based: `/api/customers`, `/api/datasets`
- RESTful verbs: GET, POST, PUT, DELETE

### Response Format
```json
{
  "id": "123",
  "name": "Resource Name",
  "customerId": "cust_456",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### Error Format
```json
{
  "detail": "Error message",
  "status_code": 404
}
```

## Configuration Management

### Backend
- Use `pydantic-settings` for environment variables
- Define in `app/config.py`
- Access via `settings` singleton

### Frontend
- Use Vite environment variables (`VITE_*`)
- Access via `import.meta.env.VITE_API_BASE_URL`

## Logging

### Backend
- Use Python `logging` module
- Configure in `main.py`
- Log levels: DEBUG, INFO, WARNING, ERROR

### Frontend
- Use `console.log`, `console.error` for development
- Consider structured logging for production
