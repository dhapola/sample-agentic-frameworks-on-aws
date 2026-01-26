# Product Overview

Gen AI Evaluation Platform is a multi-tenant SaaS platform for systematically testing and evaluating generative AI applications.

## Core Capabilities

- **Multi-Tenancy**: Complete data isolation between customer organizations using `customerId` field on all entities
- **Dataset Management**: Create and manage test datasets with input/output pairs for evaluation
- **Application Profiles**: Configure connections to gen AI applications via HTTP/REST or WebSocket
- **Evaluation Engine**: Execute automated evaluations against application profiles using test datasets
- **Metrics & Analytics**: Calculate accuracy, relevance, and latency metrics for AI responses
- **Results Dashboard**: Web interface for viewing, comparing, and analyzing evaluation results

## Key Entities

- **Customer**: Tenant organization (top-level isolation boundary)
  - Fields: `id`, `name`, `contact_email`, `contact_phone`, `configuration`, `created_at`, `updated_at`
  - Validation: Name cannot be empty/whitespace, phone must contain digits
  
- **Application Profile**: Configuration for connecting to a gen AI application
  - Fields: `id`, `customer_id`, `name`, `type`, `connection_config`, `created_at`, `updated_at`
  - Types: `"chatbot"`, `"rag"`, `"agent"`, `"workflow"`, `"custom"`
  - Connection config: `endpoint`, `authentication`, `timeout`, `retries`, `custom_headers`
  
- **Dataset**: Collection of test cases with expected outputs
  - Fields: `id`, `customer_id`, `name`, `description`, `test_cases`, `created_at`, `updated_at`
  - Embedded test cases within dataset document
  
- **Test Case**: Single input/output pair for evaluation
  - Fields: `id`, `input`, `expected_output`, `metadata`
  - Nested within Dataset documents
  
- **Evaluation Run**: Execution of a dataset against an application profile
  - Fields: `id`, `customer_id`, `dataset_id`, `application_profile_id`, `status`, `start_time`, `end_time`, `responses`, `metrics`
  - Status values: `"pending"`, `"running"`, `"completed"`, `"failed"`
  
- **Response**: Individual AI application response with metrics
  - Fields: `test_case_id`, `input`, `output`, `latency`, `timestamp`, `error`, `individual_metrics`
  - Individual metrics: `accuracy`, `relevance`
  
- **Aggregated Metrics**: Summary metrics for an evaluation run
  - Fields: `average_accuracy`, `average_relevance`, `average_latency`, `median_latency`, `p95_latency`, `success_rate`, `total_test_cases`, `failed_test_cases`

## Multi-Tenancy Architecture

All data operations are scoped by `customerId`:
- **Database Level**: All collections have `customerId` field (camelCase) with indexes
- **Middleware Level**: `CustomerContextMiddleware` extracts `X-Customer-ID` header and stores in `request.state.customer_id`
- **API Level**: 
  - Admin endpoints (`/api/customers`, `/api/customers/{id}/application-profiles`) are exempt from customer context
  - Tenant-scoped endpoints (`/api/datasets`, `/api/evaluations`) require `X-Customer-ID` header
  - Dependency injection enforces customer context via `get_customer_id()` dependency
- **Service Level**: All operations filter by `customer_id` parameter
- **Repository Level**: Database queries automatically include `{"customerId": customer_id}` filter
- **Validation**: Custom exceptions (`UnauthorizedError`) raised when customer context is missing

### Exempt Paths (No Customer Context Required)
- `/api/health`
- `/api/customers` (admin endpoints)
- `/docs`, `/redoc`, `/openapi.json` (API documentation)

## API Endpoints

### Admin Endpoints (No Customer Context Required)
- **Customers**
  - `POST /api/customers` - Create customer
  - `GET /api/customers` - List all customers
  - `GET /api/customers/{customer_id}` - Get customer details
  - `PUT /api/customers/{customer_id}` - Update customer
  - `DELETE /api/customers/{customer_id}` - Delete customer

- **Application Profiles**
  - `POST /api/customers/{customer_id}/application-profiles` - Create profile for customer
  - `GET /api/customers/{customer_id}/application-profiles` - List customer's profiles
  - `GET /api/application-profiles/{profile_id}` - Get profile details
  - `PUT /api/application-profiles/{profile_id}` - Update profile
  - `DELETE /api/application-profiles/{profile_id}` - Delete profile

### Tenant-Scoped Endpoints (Require X-Customer-ID Header)
- **Datasets**
  - `POST /api/datasets` - Create dataset
  - `GET /api/datasets` - List customer's datasets
  - `GET /api/datasets/{dataset_id}` - Get dataset details
  - `PUT /api/datasets/{dataset_id}` - Update dataset
  - `DELETE /api/datasets/{dataset_id}` - Delete dataset
  - `POST /api/datasets/{dataset_id}/test-cases` - Add test case
  - `PUT /api/datasets/{dataset_id}/test-cases/{test_case_id}` - Update test case
  - `DELETE /api/datasets/{dataset_id}/test-cases/{test_case_id}` - Delete test case

- **Evaluations**
  - `POST /api/evaluations` - Start evaluation run
  - `GET /api/evaluations` - List customer's evaluation runs (summary)
  - `GET /api/evaluations/{run_id}` - Get evaluation run details (full responses)
  - `POST /api/evaluations/compare` - Compare multiple evaluation runs

### Utility Endpoints
- `GET /api/health` - Health check (returns database connection status)


## Evaluation Workflow

### 1. Setup Phase
1. **Create Customer** (Admin): Register a new tenant organization
2. **Create Application Profile** (Admin): Configure connection to gen AI application
3. **Create Dataset** (Tenant): Define test cases with inputs and expected outputs
4. **Add Test Cases** (Tenant): Populate dataset with test scenarios

### 2. Execution Phase
1. **Start Evaluation Run** (Tenant): Execute dataset against application profile
2. **Engine Execution**: 
   - Validates dataset and profile belong to customer
   - Sends each test case input to the application
   - Captures response, latency, and any errors
   - Stores individual responses with timestamps
3. **Metrics Calculation**:
   - Individual metrics: Accuracy and relevance per response
   - Aggregated metrics: Averages, medians, percentiles, success rate

### 3. Analysis Phase
1. **View Results** (Tenant): Review evaluation run with all responses and metrics
2. **Compare Runs** (Tenant): Side-by-side comparison of multiple evaluation runs
3. **Dashboard** (Tenant): Visualize trends and performance over time

## Error Handling

All errors follow a standardized format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { /* Optional additional context */ },
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Error Codes
- `VALIDATION_ERROR` (400): Request validation failed
- `UNAUTHORIZED` (401): Missing or invalid customer context
- `FORBIDDEN` (403): Access denied
- `NOT_FOUND` (404): Resource not found
- `INTERNAL_ERROR` (500): Unexpected server error
- `DATABASE_ERROR` (500): Database operation failed
- `CONNECTION_ERROR` (503): External service connection failed
