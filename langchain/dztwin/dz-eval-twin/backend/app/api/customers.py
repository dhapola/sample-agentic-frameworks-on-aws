"""Customer management API endpoints (admin only)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.middleware.error_handler import NotFoundError, ValidationError
from app.models.customer import Customer
from app.services.customer_service import CustomerService
from app.utils.validation import validate_customer_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customers", tags=["customers"])


# Request/Response models
class CreateCustomerRequest(BaseModel):
    """Request model for creating a customer."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Customer organization name")
    contact_email: EmailStr = Field(..., description="Primary contact email address")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    configuration: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Customer-specific configuration settings"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation",
                "contact_email": "admin@acme.com",
                "contact_phone": "+1-555-0100",
                "configuration": {
                    "max_concurrent_runs": 5,
                    "default_timeout": 30
                }
            }
        }


class UpdateCustomerRequest(BaseModel):
    """Request model for updating a customer."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Customer organization name")
    contact_email: Optional[EmailStr] = Field(None, description="Primary contact email address")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="Customer-specific configuration settings"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation Updated",
                "contact_email": "newadmin@acme.com"
            }
        }


class CustomerResponse(BaseModel):
    """Response model for customer data."""
    
    id: str
    name: str
    contact_email: str
    contact_phone: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str
    
    @classmethod
    def from_customer(cls, customer: Customer) -> "CustomerResponse":
        """Convert Customer model to response."""
        return cls(
            id=customer.id,
            name=customer.name,
            contact_email=customer.contact_email,
            contact_phone=customer.contact_phone,
            configuration=customer.configuration,
            created_at=customer.created_at.isoformat(),
            updated_at=customer.updated_at.isoformat()
        )


# Dependency to get customer service
def get_customer_service() -> CustomerService:
    """Get customer service instance."""
    repository = DataRepository(database_manager.database)
    return CustomerService(repository)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
    description="Create a new customer organization (admin only)"
)
async def create_customer(
    request: CreateCustomerRequest,
    service: CustomerService = Depends(get_customer_service)
) -> CustomerResponse:
    """
    Create a new customer organization.
    
    Args:
        request: Customer creation request
        service: Customer service instance
        
    Returns:
        Created customer
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        customer = await service.create_customer(
            name=request.name,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            configuration=request.configuration
        )
        return CustomerResponse.from_customer(customer)
    except ValueError as e:
        raise ValidationError(str(e))


@router.get(
    "",
    response_model=List[CustomerResponse],
    summary="List all customers",
    description="Get a list of all customer organizations (admin only)"
)
async def list_customers(
    service: CustomerService = Depends(get_customer_service)
) -> List[CustomerResponse]:
    """
    Get all customers.
    
    Args:
        service: Customer service instance
        
    Returns:
        List of all customers
    """
    customers = await service.get_all_customers()
    return [CustomerResponse.from_customer(c) for c in customers]


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer details",
    description="Get details of a specific customer (admin only)"
)
async def get_customer(
    customer_id: str,
    service: CustomerService = Depends(get_customer_service)
) -> CustomerResponse:
    """
    Get customer by ID.
    
    Args:
        customer_id: Customer ID
        service: Customer service instance
        
    Returns:
        Customer details
        
    Raises:
        NotFoundError: If customer not found
        ValidationError: If customer ID is invalid
    """
    try:
        # Validate customer_id format
        validated_id = validate_customer_id(customer_id)
        
        customer = await service.get_customer(validated_id)
        if customer is None:
            raise NotFoundError(f"Customer not found: {validated_id}")
        return CustomerResponse.from_customer(customer)
    except ValueError as e:
        raise ValidationError(str(e))


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
    description="Update customer information (admin only)"
)
async def update_customer(
    customer_id: str,
    request: UpdateCustomerRequest,
    service: CustomerService = Depends(get_customer_service)
) -> CustomerResponse:
    """
    Update customer information.
    
    Args:
        customer_id: Customer ID
        request: Customer update request
        service: Customer service instance
        
    Returns:
        Updated customer
        
    Raises:
        NotFoundError: If customer not found
        ValidationError: If validation fails
    """
    try:
        # Validate customer_id format
        validated_id = validate_customer_id(customer_id)
        
        # Check if at least one field is provided
        if all(v is None for v in [request.name, request.contact_email, request.contact_phone, request.configuration]):
            raise ValidationError("At least one field must be provided for update")
        
        customer = await service.update_customer(
            customer_id=validated_id,
            name=request.name,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            configuration=request.configuration
        )
        return CustomerResponse.from_customer(customer)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer",
    description="Delete a customer organization (admin only)"
)
async def delete_customer(
    customer_id: str,
    service: CustomerService = Depends(get_customer_service)
) -> None:
    """
    Delete customer.
    
    Args:
        customer_id: Customer ID
        service: Customer service instance
        
    Raises:
        NotFoundError: If customer not found
        ValidationError: If customer ID is invalid
    """
    try:
        # Validate customer_id format
        validated_id = validate_customer_id(customer_id)
        
        await service.delete_customer(validated_id)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))
