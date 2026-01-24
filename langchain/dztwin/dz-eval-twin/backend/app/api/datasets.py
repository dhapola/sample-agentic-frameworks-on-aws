"""Dataset management API endpoints (tenant-scoped)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.middleware.error_handler import NotFoundError, ValidationError, UnauthorizedError
from app.models.dataset import Dataset
from app.models.test_case import TestCase
from app.services.dataset_service import DatasetService
from app.utils.validation import validate_dataset_id, validate_test_case_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


# Request/Response models
class CreateDatasetRequest(BaseModel):
    """Request model for creating a dataset."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Dataset name")
    description: str = Field(default="", max_length=1000, description="Dataset description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Geography Questions",
                "description": "Test cases for geography knowledge"
            }
        }


class UpdateDatasetRequest(BaseModel):
    """Request model for updating a dataset."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Dataset name")
    description: Optional[str] = Field(None, max_length=1000, description="Dataset description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Geography Questions Updated",
                "description": "Updated test cases for geography knowledge"
            }
        }


class CreateTestCaseRequest(BaseModel):
    """Request model for creating a test case."""
    
    input: str = Field(..., min_length=1, description="Test case input text")
    expected_output: Optional[str] = Field(None, description="Expected output for accuracy comparison")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional test case metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "input": "What is the capital of France?",
                "expected_output": "Paris",
                "metadata": {
                    "category": "geography",
                    "difficulty": "easy"
                }
            }
        }


class UpdateTestCaseRequest(BaseModel):
    """Request model for updating a test case."""
    
    input: Optional[str] = Field(None, min_length=1, description="Test case input text")
    expected_output: Optional[str] = Field(None, description="Expected output for accuracy comparison")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional test case metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "input": "What is the capital of France?",
                "expected_output": "The capital of France is Paris"
            }
        }


class TestCaseResponse(BaseModel):
    """Response model for test case data."""
    
    id: str
    input: str
    expected_output: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_test_case(cls, test_case: TestCase) -> "TestCaseResponse":
        """Convert TestCase model to response."""
        return cls(
            id=test_case.id,
            input=test_case.input,
            expected_output=test_case.expected_output,
            metadata=test_case.metadata
        )


class DatasetResponse(BaseModel):
    """Response model for dataset data."""
    
    id: str
    customer_id: str
    name: str
    description: str
    test_cases: List[TestCaseResponse]
    created_at: str
    updated_at: str
    
    @classmethod
    def from_dataset(cls, dataset: Dataset) -> "DatasetResponse":
        """Convert Dataset model to response."""
        return cls(
            id=dataset.id,
            customer_id=dataset.customer_id,
            name=dataset.name,
            description=dataset.description,
            test_cases=[TestCaseResponse.from_test_case(tc) for tc in dataset.test_cases],
            created_at=dataset.created_at.isoformat(),
            updated_at=dataset.updated_at.isoformat()
        )


# Dependency to get dataset service
def get_dataset_service() -> DatasetService:
    """Get dataset service instance."""
    repository = DataRepository(database_manager.database)
    return DatasetService(repository)


# Dependency to get customer_id from request state
def get_customer_id(request: Request) -> str:
    """
    Get customer_id from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Customer ID from request state
        
    Raises:
        UnauthorizedError: If customer_id not found in request state
    """
    customer_id = getattr(request.state, "customer_id", None)
    if not customer_id:
        raise UnauthorizedError("Customer context required. Please provide X-Customer-ID header.")
    return customer_id


@router.post(
    "",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dataset",
    description="Create a new dataset for the authenticated customer"
)
async def create_dataset(
    request_data: CreateDatasetRequest,
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> DatasetResponse:
    """
    Create a new dataset.
    
    Args:
        request_data: Dataset creation request
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Returns:
        Created dataset
        
    Raises:
        ValidationError: If validation fails
        UnauthorizedError: If customer context missing
    """
    try:
        dataset = await service.create_dataset(
            customer_id=customer_id,
            name=request_data.name,
            description=request_data.description
        )
        return DatasetResponse.from_dataset(dataset)
    except ValueError as e:
        raise ValidationError(str(e))


@router.get(
    "",
    response_model=List[DatasetResponse],
    summary="List datasets",
    description="Get all datasets for the authenticated customer"
)
async def list_datasets(
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> List[DatasetResponse]:
    """
    Get all datasets for a customer.
    
    Args:
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Returns:
        List of datasets for the customer
        
    Raises:
        UnauthorizedError: If customer context missing
    """
    try:
        datasets = await service.get_datasets_by_customer(customer_id)
        return [DatasetResponse.from_dataset(d) for d in datasets]
    except ValueError as e:
        raise ValidationError(str(e))


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get dataset details",
    description="Get details of a specific dataset"
)
async def get_dataset(
    dataset_id: str,
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> DatasetResponse:
    """
    Get dataset by ID.
    
    Args:
        dataset_id: Dataset ID
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Returns:
        Dataset details
        
    Raises:
        NotFoundError: If dataset not found
        UnauthorizedError: If customer context missing
        ValidationError: If dataset ID is invalid
    """
    try:
        # Validate dataset_id format
        validated_dataset_id = validate_dataset_id(dataset_id)
        
        dataset = await service.get_dataset(validated_dataset_id, customer_id)
        if dataset is None:
            raise NotFoundError(f"Dataset not found: {validated_dataset_id}")
        return DatasetResponse.from_dataset(dataset)
    except ValueError as e:
        raise ValidationError(str(e))


@router.put(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Update dataset",
    description="Update dataset information"
)
async def update_dataset(
    dataset_id: str,
    request_data: UpdateDatasetRequest,
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> DatasetResponse:
    """
    Update dataset information.
    
    Args:
        dataset_id: Dataset ID
        request_data: Dataset update request
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Returns:
        Updated dataset
        
    Raises:
        NotFoundError: If dataset not found
        ValidationError: If validation fails
        UnauthorizedError: If customer context missing
    """
    try:
        # Validate dataset_id format
        validated_dataset_id = validate_dataset_id(dataset_id)
        
        # Check if at least one field is provided
        if all(v is None for v in [request_data.name, request_data.description]):
            raise ValidationError("At least one field must be provided for update")
        
        dataset = await service.update_dataset(
            dataset_id=validated_dataset_id,
            customer_id=customer_id,
            name=request_data.name,
            description=request_data.description
        )
        return DatasetResponse.from_dataset(dataset)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dataset",
    description="Delete a dataset"
)
async def delete_dataset(
    dataset_id: str,
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> None:
    """
    Delete dataset.
    
    Args:
        dataset_id: Dataset ID
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Raises:
        NotFoundError: If dataset not found
        UnauthorizedError: If customer context missing
        ValidationError: If dataset ID is invalid
    """
    try:
        # Validate dataset_id format
        validated_dataset_id = validate_dataset_id(dataset_id)
        
        await service.delete_dataset(validated_dataset_id, customer_id)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))


@router.post(
    "/{dataset_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add test case",
    description="Add a test case to a dataset"
)
async def add_test_case(
    dataset_id: str,
    request_data: CreateTestCaseRequest,
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> TestCaseResponse:
    """
    Add a test case to a dataset.
    
    Args:
        dataset_id: Dataset ID
        request_data: Test case creation request
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Returns:
        Created test case
        
    Raises:
        NotFoundError: If dataset not found
        ValidationError: If validation fails
        UnauthorizedError: If customer context missing
    """
    try:
        # Validate dataset_id format
        validated_dataset_id = validate_dataset_id(dataset_id)
        
        test_case = await service.add_test_case(
            dataset_id=validated_dataset_id,
            customer_id=customer_id,
            input_text=request_data.input,
            expected_output=request_data.expected_output,
            metadata=request_data.metadata
        )
        return TestCaseResponse.from_test_case(test_case)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))


@router.put(
    "/{dataset_id}/test-cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Update test case",
    description="Update a test case in a dataset"
)
async def update_test_case(
    dataset_id: str,
    test_case_id: str,
    request_data: UpdateTestCaseRequest,
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> TestCaseResponse:
    """
    Update a test case in a dataset.
    
    Args:
        dataset_id: Dataset ID
        test_case_id: Test case ID
        request_data: Test case update request
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Returns:
        Updated test case
        
    Raises:
        NotFoundError: If dataset or test case not found
        ValidationError: If validation fails
        UnauthorizedError: If customer context missing
    """
    try:
        # Validate IDs format
        validated_dataset_id = validate_dataset_id(dataset_id)
        validated_test_case_id = validate_test_case_id(test_case_id)
        
        # Check if at least one field is provided
        if all(v is None for v in [request_data.input, request_data.expected_output, request_data.metadata]):
            raise ValidationError("At least one field must be provided for update")
        
        test_case = await service.update_test_case(
            dataset_id=validated_dataset_id,
            customer_id=customer_id,
            test_case_id=validated_test_case_id,
            input_text=request_data.input,
            expected_output=request_data.expected_output,
            metadata=request_data.metadata
        )
        return TestCaseResponse.from_test_case(test_case)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))


@router.delete(
    "/{dataset_id}/test-cases/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete test case",
    description="Delete a test case from a dataset"
)
async def delete_test_case(
    dataset_id: str,
    test_case_id: str,
    customer_id: str = Depends(get_customer_id),
    service: DatasetService = Depends(get_dataset_service)
) -> None:
    """
    Delete a test case from a dataset.
    
    Args:
        dataset_id: Dataset ID
        test_case_id: Test case ID
        customer_id: Customer ID from request context
        service: Dataset service instance
        
    Raises:
        NotFoundError: If dataset or test case not found
        UnauthorizedError: If customer context missing
        ValidationError: If IDs are invalid
    """
    try:
        # Validate IDs format
        validated_dataset_id = validate_dataset_id(dataset_id)
        validated_test_case_id = validate_test_case_id(test_case_id)
        
        await service.delete_test_case(validated_dataset_id, customer_id, validated_test_case_id)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))
