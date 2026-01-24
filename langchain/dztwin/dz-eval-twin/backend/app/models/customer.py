"""Customer model for multi-tenant isolation."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class Customer(BaseModel):
    """
    Tenant organization model.
    
    Represents a customer organization using the platform with complete data isolation.
    All datasets, application profiles, and evaluation runs are scoped to a customer.
    """
    
    id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Customer organization name")
    contact_email: EmailStr = Field(..., description="Primary contact email address")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    configuration: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Customer-specific configuration settings"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate customer name is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Customer name cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator('contact_phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format if provided."""
        if v is not None:
            # Remove common formatting characters
            cleaned = v.strip()
            if cleaned and not any(c.isdigit() for c in cleaned):
                raise ValueError("Phone number must contain at least one digit")
            return cleaned
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "cust_123456",
                "name": "Acme Corporation",
                "contact_email": "admin@acme.com",
                "contact_phone": "+1-555-0100",
                "configuration": {
                    "max_concurrent_runs": 5,
                    "default_timeout": 30
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
