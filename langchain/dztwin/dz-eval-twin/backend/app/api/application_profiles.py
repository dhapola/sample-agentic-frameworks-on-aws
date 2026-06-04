"""Application profile management API endpoints (admin only)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status, Request
from pydantic import BaseModel, Field, AnyUrl

from app.database.connection import database_manager
from app.database.repository import DataRepository
from app.middleware.error_handler import NotFoundError, ValidationError, UnauthorizedError
from app.models.application_profile import ApplicationProfile, ApplicationType
from app.services.application_profile_service import ApplicationProfileService
from app.utils.validation import validate_customer_id, validate_application_profile_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["application-profiles"])


# Request/Response models
class CreateApplicationProfileRequest(BaseModel):
    """Request model for creating an application profile."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Profile name")
    type: ApplicationType = Field(..., description="Application type")
    endpoint: str = Field(..., description="Application endpoint URL")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    retries: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    authentication: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Authentication configuration"
    )
    custom_headers: Optional[Dict[str, str]] = Field(
        default=None,
        alias="customHeaders",
        description="Custom HTTP headers"
    )
    
    class Config:
        populate_by_name = True  # Accept both snake_case and camelCase
        json_schema_extra = {
            "example": {
                "name": "Production Chatbot",
                "type": "chatbot",
                "endpoint": "https://api.example.com/v1/chat",
                "timeout": 30,
                "retries": 3,
                "authentication": {
                    "type": "bearer",
                    "token": "sk-..."
                },
                "customHeaders": {
                    "X-Custom-Header": "value"
                }
            }
        }


class UpdateApplicationProfileRequest(BaseModel):
    """Request model for updating an application profile."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Profile name")
    endpoint: Optional[str] = Field(None, description="Application endpoint URL")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Request timeout in seconds")
    retries: Optional[int] = Field(None, ge=0, le=10, description="Number of retry attempts")
    authentication: Optional[Dict[str, Any]] = Field(
        None,
        description="Authentication configuration"
    )
    custom_headers: Optional[Dict[str, str]] = Field(
        None,
        alias="customHeaders",
        description="Custom HTTP headers"
    )
    
    class Config:
        populate_by_name = True  # Accept both snake_case and camelCase
        json_schema_extra = {
            "example": {
                "name": "Production Chatbot Updated",
                "timeout": 60
            }
        }


class ApplicationProfileResponse(BaseModel):
    """Response model for application profile data."""
    
    id: str
    customer_id: str = Field(..., alias="customerId")
    name: str
    type: str
    connection_config: Dict[str, Any] = Field(..., alias="connectionConfig")
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")
    
    class Config:
        populate_by_name = True
        by_alias = True  # Serialize using aliases (camelCase)
    
    @classmethod
    def from_application_profile(cls, profile: ApplicationProfile) -> "ApplicationProfileResponse":
        """Convert ApplicationProfile model to response."""
        return cls(
            id=profile.id,
            customer_id=profile.customer_id,
            name=profile.name,
            type=profile.type,
            connection_config=profile.connection_config.model_dump(),
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat()
        )


# Dependency to get application profile service
def get_application_profile_service() -> ApplicationProfileService:
    """Get application profile service instance."""
    repository = DataRepository(database_manager.database)
    return ApplicationProfileService(repository)


@router.post(
    "/customers/{customer_id}/application-profiles",
    response_model=ApplicationProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create application profile",
    description="Create a new application profile for a customer (admin only)"
)
async def create_application_profile(
    customer_id: str,
    request: CreateApplicationProfileRequest,
    service: ApplicationProfileService = Depends(get_application_profile_service)
) -> ApplicationProfileResponse:
    """
    Create a new application profile for a customer.
    
    Args:
        customer_id: Customer ID
        request: Application profile creation request
        service: Application profile service instance
        
    Returns:
        Created application profile
        
    Raises:
        ValidationError: If validation fails
        NotFoundError: If customer not found
    """
    try:
        # Validate customer_id format
        validated_customer_id = validate_customer_id(customer_id)
        
        profile = await service.create_application_profile(
            customer_id=validated_customer_id,
            name=request.name,
            app_type=request.type,
            endpoint=request.endpoint,
            timeout=request.timeout,
            retries=request.retries,
            authentication=request.authentication,
            custom_headers=request.custom_headers
        )
        return ApplicationProfileResponse.from_application_profile(profile)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))


@router.get(
    "/customers/{customer_id}/application-profiles",
    response_model=List[ApplicationProfileResponse],
    summary="List customer's application profiles",
    description="Get all application profiles for a specific customer (admin only)"
)
async def list_customer_application_profiles(
    customer_id: str,
    service: ApplicationProfileService = Depends(get_application_profile_service)
) -> List[ApplicationProfileResponse]:
    """
    Get all application profiles for a customer.
    
    Args:
        customer_id: Customer ID
        service: Application profile service instance
        
    Returns:
        List of application profiles for the customer
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Validate customer_id format
        validated_customer_id = validate_customer_id(customer_id)
        
        profiles = await service.get_profiles_by_customer(validated_customer_id)
        return [ApplicationProfileResponse.from_application_profile(p) for p in profiles]
    except ValueError as e:
        raise ValidationError(str(e))


@router.get(
    "/application-profiles",
    response_model=List[ApplicationProfileResponse],
    summary="List application profiles (tenant-scoped)",
    description="Get all application profiles for the current customer context"
)
async def list_application_profiles(
    request: Request,
    service: ApplicationProfileService = Depends(get_application_profile_service)
) -> List[ApplicationProfileResponse]:
    """
    Get all application profiles for the current customer.
    
    Args:
        request: FastAPI request object
        service: Application profile service instance
        
    Returns:
        List of application profiles for the customer
        
    Raises:
        UnauthorizedError: If customer context missing
        ValidationError: If validation fails
    """
    # Get customer_id from request state (set by CustomerContextMiddleware)
    customer_id = getattr(request.state, "customer_id", None)
    if not customer_id:
        raise UnauthorizedError("Customer context required. Please provide X-Customer-ID header.")
    
    try:
        profiles = await service.get_profiles_by_customer(customer_id)
        return [ApplicationProfileResponse.from_application_profile(p) for p in profiles]
    except ValueError as e:
        raise ValidationError(str(e))


@router.get(
    "/application-profiles/{profile_id}",
    response_model=ApplicationProfileResponse,
    summary="Get application profile details",
    description="Get details of a specific application profile (admin only)"
)
async def get_application_profile(
    profile_id: str,
    service: ApplicationProfileService = Depends(get_application_profile_service)
) -> ApplicationProfileResponse:
    """
    Get application profile by ID.
    
    Args:
        profile_id: Application profile ID
        service: Application profile service instance
        
    Returns:
        Application profile details
        
    Raises:
        NotFoundError: If profile not found
        ValidationError: If validation fails
    """
    try:
        # Validate profile_id format
        validated_profile_id = validate_application_profile_id(profile_id)
        
        profile = await service.get_application_profile(validated_profile_id)
        if profile is None:
            raise NotFoundError(f"Application profile not found: {validated_profile_id}")
        return ApplicationProfileResponse.from_application_profile(profile)
    except ValueError as e:
        raise ValidationError(str(e))


@router.put(
    "/application-profiles/{profile_id}",
    response_model=ApplicationProfileResponse,
    summary="Update application profile",
    description="Update application profile configuration (admin only)"
)
async def update_application_profile(
    profile_id: str,
    request: UpdateApplicationProfileRequest,
    service: ApplicationProfileService = Depends(get_application_profile_service)
) -> ApplicationProfileResponse:
    """
    Update application profile.
    
    Args:
        profile_id: Application profile ID
        request: Application profile update request
        service: Application profile service instance
        
    Returns:
        Updated application profile
        
    Raises:
        NotFoundError: If profile not found
        ValidationError: If validation fails
    """
    try:
        # Validate profile_id format
        validated_profile_id = validate_application_profile_id(profile_id)
        
        # Check if at least one field is provided
        if all(v is None for v in [
            request.name,
            request.endpoint,
            request.timeout,
            request.retries,
            request.authentication,
            request.custom_headers
        ]):
            raise ValidationError("At least one field must be provided for update")
        
        profile = await service.update_application_profile(
            profile_id=validated_profile_id,
            name=request.name,
            endpoint=request.endpoint,
            timeout=request.timeout,
            retries=request.retries,
            authentication=request.authentication,
            custom_headers=request.custom_headers
        )
        return ApplicationProfileResponse.from_application_profile(profile)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))


@router.delete(
    "/application-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete application profile",
    description="Delete an application profile (admin only)"
)
async def delete_application_profile(
    profile_id: str,
    service: ApplicationProfileService = Depends(get_application_profile_service)
) -> None:
    """
    Delete application profile.
    
    Args:
        profile_id: Application profile ID
        service: Application profile service instance
        
    Raises:
        NotFoundError: If profile not found
        ValidationError: If validation fails
    """
    try:
        # Validate profile_id format
        validated_profile_id = validate_application_profile_id(profile_id)
        
        await service.delete_application_profile(validated_profile_id)
    except ValueError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise NotFoundError(str(e))
        raise ValidationError(str(e))
