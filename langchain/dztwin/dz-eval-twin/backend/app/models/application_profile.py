"""Application profile model for customer-specific gen AI application configurations."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .connection_config import ConnectionConfig


# Valid application types
ApplicationType = Literal["chatbot", "rag", "agent", "workflow", "custom"]


class ApplicationProfile(BaseModel):
    """
    Customer-specific gen AI application configuration.
    
    Represents a specific configuration of a generative AI application
    for a customer, including connection details and application type.
    """
    
    id: str = Field(..., description="Unique application profile identifier")
    customer_id: str = Field(..., description="Customer ID for tenant isolation")
    name: str = Field(..., min_length=1, max_length=200, description="Profile name")
    type: ApplicationType = Field(..., description="Application type")
    connection_config: ConnectionConfig = Field(..., description="Connection configuration")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate profile name is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Profile name cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator('customer_id')
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer_id is not empty."""
        if not v or not v.strip():
            raise ValueError("Customer ID cannot be empty")
        return v.strip()
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "app_profile_123",
                "customer_id": "cust_123456",
                "name": "Production Chatbot",
                "type": "chatbot",
                "connection_config": {
                    "endpoint": "https://api.example.com/v1/chat",
                    "authentication": {
                        "type": "bearer",
                        "token": "sk-..."
                    },
                    "timeout": 30,
                    "retries": 3
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
